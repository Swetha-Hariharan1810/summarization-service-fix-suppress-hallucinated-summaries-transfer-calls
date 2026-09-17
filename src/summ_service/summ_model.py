import contextlib
import functools
import inspect
import logging
import math
import multiprocessing
import shutil
import time
from pathlib import Path
from typing import List, Tuple, Union

import torch
from fairseq.data.encoders.gpt2_bpe import get_encoder
from fairseq.models.transformer import TransformerModel
from sentence_transformers import SentenceTransformer

from . import az_util, s3_util
from .config import SummConfig

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _trusted_checkpoint_load():
    """Let fairseq load our own checkpoint under torch >= 2.6.

    torch 2.6 changed the default of ``torch.load``'s ``weights_only`` argument
    from False to True. fairseq's ``load_checkpoint_to_cpu`` calls
    ``torch.load`` without passing it, and our checkpoints are not plain
    tensors: ``_upgrade_state_dict`` reads an ``argparse.Namespace`` out of
    ``state["args"]`` and an omegaconf container out of ``state["cfg"]``.
    Neither is something the weights-only unpickler will construct, so the load
    raises UnpicklingError before the model is ever built.

    The checkpoint is our own build artifact, fetched over TLS from the Azure
    blob container or S3 bucket named in SummConfig - the same trust boundary
    the service has always had. Restoring the pre-2.6 behaviour for this one
    call is therefore not a change in exposure, and scoping it to the call
    keeps the weights-only default everywhere else, including the
    ``SentenceTransformer`` load below.

    Model loading happens once, at startup, before any worker threads exist, so
    swapping the module attribute is safe here. Do not reuse this around
    anything that runs concurrently.
    """
    original = torch.load
    try:
        takes_weights_only = "weights_only" in inspect.signature(original).parameters
    except (TypeError, ValueError):
        # Not introspectable. Our pin is well past 2.6, so assume it takes it.
        takes_weights_only = True
    if not takes_weights_only:
        # torch < 1.13 has no such argument; nothing to do.
        yield
        return

    @functools.wraps(original)
    def _load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original(*args, **kwargs)

    torch.load = _load
    try:
        yield
    finally:
        torch.load = original


class SummModel(torch.nn.Module):
    def __init__(self, bpe, summarizer, sentence_understanding, config=SummConfig()):
        super().__init__()
        self.bpe = bpe
        self.summarizer = summarizer
        self.config = config
        if config.sliding_windows or (config.general_model and config.summary_exclude):
            self.sentence_understanding = sentence_understanding
            self.summary_exclude_embed = [
                sentence_understanding.encode(exl) for exl in config.summary_exclude
            ]
        if config.generate_reason:
            self.reasons_embedding = {
                k: [sentence_understanding.encode(vv) for vv in config.reasons[k]]
                for k in config.reasons
            }

    @torch.no_grad()
    def encode(self, text_ip: str) -> Tuple[List[torch.Tensor], bool]:
        tokens_all = []
        truncate = False
        for q in self.config.questions:
            if q:
                text = q + "\t" + text_ip
            else:
                text = text_ip
            # step 2 bpe, truncation, binary
            transcript_bpe = self.bpe.encode(text)
            # TODO: when using torchscript model, max_positions is not accessible
            if len(transcript_bpe) > self.summarizer.max_positions[0] - 2:
                if (
                    len(transcript_bpe) < self.summarizer.max_positions[0] - 2 + 100
                    or not self.config.sliding_windows
                ):
                    transcript_bpes = [
                        transcript_bpe[: self.summarizer.max_positions[0] - 2]
                    ]
                else:
                    # apply sliding window on long transcripts with 2k token overlapping.
                    truncate = True
                    window_size = int(self.summarizer.max_positions[0] / 3 * 2)
                    num_sliding_windows = len(transcript_bpe) // window_size
                    transcript_bpes = [
                        transcript_bpe[
                            j * window_size : j * window_size
                            + self.summarizer.max_positions[0]
                            - 30
                        ]
                        for j in range(num_sliding_windows)
                    ]
                    if q:
                        quenstion_encode = self.bpe.encode(q + "\t")
                    else:
                        quenstion_encode = ""
                    for j in range(1, len(transcript_bpes)):
                        transcript_bpes[j] = quenstion_encode + transcript_bpes[j]
            else:
                transcript_bpes = [transcript_bpe]

            transcript_bpes = [
                " ".join([str(b) for b in transcript_bpe])
                for transcript_bpe in transcript_bpes
            ]
            transcript_bpes = [
                transcript_bpe + " </s>" for transcript_bpe in transcript_bpes
            ]
            tokens = [
                self.summarizer.task.source_dictionary.encode_line(
                    transcript_bpe, append_eos=False
                )
                for transcript_bpe in transcript_bpes
            ]

            tokens_all.extend(tokens)
        return tokens_all, truncate

    @torch.no_grad()
    def forward(self, tokens: List[torch.Tensor]) -> List[torch.Tensor]:
        # 1. compute minlen based on ratio
        minlen = max(
            self.config.minlen,
            math.ceil(self.config.ratio[0] * max([len(t) for t in tokens])),
        )
        maxlen = max(
            self.config.maxlen,
            math.ceil(self.config.ratio[1] * max([len(t) for t in tokens])),
        )

        hypos = self.summarizer.generate(
            tokens,
            temperature=self.config.temperature,
            beam=self.config.beam,
            max_len_b=maxlen,
            min_len=minlen,
            no_repeat_ngram_size=self.config.no_repeat_ngram_size,
        )
        return [hypo[0]["tokens"] for hypo in hypos]

    def decode(self, tokens: List[torch.Tensor]) -> str:
        concat_summary = []
        for hyp in tokens:
            candidate = self.summarizer.decode(hyp)
            best_summary = self.bpe.decode(
                [int(b) for b in candidate.split(" ")]
            ).strip()
            if best_summary[-1] != ".":
                best_summary += "."
            concat_summary.append(best_summary)

        concat_summary_str = " ".join(concat_summary)
        return concat_summary_str

    def process_summary(self, text_str: str) -> str:
        assert self.config.general_model or self.config.sliding_windows
        early_stop = False
        text = [t.strip() + "." for t in text_str.split(".") if t.strip()]
        new_text = []
        for t in text:
            if t[0].isdigit() and len(new_text) > 0:
                new_text[-1] += t
            else:
                new_text.append(t)
        text = new_text
        if self.config.remove_lower_case:
            text = [t for t in text if t[0].upper() == t[0]]
        if self.config.semantic_threshold < 1:
            text_embed = self.sentence_understanding.encode(text)
            final = []
            for idx, t in enumerate(text):
                if early_stop:
                    continue
                if (
                    text_embed[idx].dot(self.summary_exclude_embed)
                    > self.config.semantic_threshold
                ):
                    continue
                flag = False
                for j in final:
                    if (
                        text_embed[idx].dot(text_embed[j])
                        > self.config.semantic_threshold
                    ):
                        flag = True
                        break
                if not flag:
                    final.append(idx)
            final = set(final)
            text = [t for i, t in enumerate(text) if i in final]
        return " ".join(text)

    def generate_reason(self, summary_processed: str) -> str:
        assert self.config.generate_reason
        best_reason = ""
        best_reason_score = 0
        best_summary_embed_reasons = self.sentence_understanding.encode(
            summary_processed
        )
        for reason in self.reasons_embedding:
            reason_embed = self.reasons_embedding[reason]
            reason_score = max(
                [best_summary_embed_reasons.dot(v) for v in reason_embed]
            )
            if reason_score > best_reason_score:
                best_reason_score = reason_score
                best_reason = reason
        return best_reason

    @classmethod
    def from_pretrained(
        cls, models_dir: Union[Path, str], config: SummConfig = SummConfig()
    ):
        model_dir = Path(models_dir) / config.model_version
        download_wait_cnt = 0
        download_job_cnt = 1
        # TODO: directly load model into memory from s3, need to change how model is loaded in fariseq and sentence_transformer
        while not config.check_all_model_files(model_dir):
            if not model_dir.is_dir():
                logger.info(f"Downloading model from {config.model_url}")
                model_dir.mkdir(parents=True, exist_ok=True)
                open(model_dir / f"download_job_cnt_{download_job_cnt}", "a").close()
                models_zip_file = model_dir / "model.zip"
                if config.model_url.startswith("https://"):
                    az_util.download_file(config.model_url, str(models_zip_file))
                elif config.model_url.startswith("s3://"):
                    s3_util.download_file(config.model_url, str(models_zip_file))
                else:
                    raise ValueError("Model url must start with https:// or s3://")

                shutil.unpack_archive(models_zip_file, model_dir)
                # unpack bpe and similarity model
                if (model_dir / "gpt2_bpe.zip").exists():
                    shutil.unpack_archive(model_dir / "gpt2_bpe.zip", model_dir)
                    (model_dir / "gpt2_bpe.zip").unlink()
                if (model_dir / "task_verification_model.zip").exists():
                    shutil.unpack_archive(
                        model_dir / "task_verification_model.zip", model_dir
                    )
                    (model_dir / "task_verification_model.zip").unlink()
                models_zip_file.unlink()
                break
            logger.info(
                f"Waiting for model file to be downloaded ... {download_wait_cnt*10}"
            )
            time.sleep(10)
            download_wait_cnt += 1
            if download_wait_cnt >= 30 * download_job_cnt:
                if (model_dir / f"download_job_cnt_{download_job_cnt}").exists():
                    logger.info(
                        "Restart downloading after waiting for"
                        f" {10*download_wait_cnt} seconds"
                    )
                    shutil.rmtree(model_dir)
                else:
                    download_job_cnt += 1

        logger.info("Start loading models ...")
        with _trusted_checkpoint_load():
            summarizer = TransformerModel.from_pretrained(
                model_dir, checkpoint_file=f"{config.model_name}.pt"
            )
        summarizer.eval()
        # summarizer = torch.compile(summarizer, mode="reduce-overhead")
        if config.general_model:
            sentence_understanding = SentenceTransformer(
                str(model_dir / "task_verification_model")
            )
        else:
            sentence_understanding = None

        if config.device == "cuda":
            summarizer = summarizer.eval().to("cuda")
            torch.set_num_threads(1)

        bpe = get_encoder(
            model_dir / "gpt2_bpe" / "encoder.json",
            model_dir / "gpt2_bpe" / "vocab.bpe",
        )
        model = cls(bpe, summarizer, sentence_understanding, config)
        logger.info("Finish loading models ...")
        return model
