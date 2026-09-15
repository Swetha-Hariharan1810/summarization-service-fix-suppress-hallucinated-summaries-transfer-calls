import logging
import math
from pathlib import Path
from typing import List, Tuple, Union

import _birchsumm  # nopep8
import torch  # nopep8

from .config import SummConfig
from .preprocess.gpt2_bpe_utils import get_encoder

logger = logging.getLogger(__name__)


torch._C._jit_set_profiling_executor(False)
torch._C._jit_set_profiling_mode(False)
torch._C._set_graph_executor_optimize(False)


class SummModel:
    def __init__(
        self,
        bpe,
        summarizer,
        config=SummConfig(),
    ):
        self.bpe = bpe
        self.summarizer = summarizer
        self.config = config
        self.max_position = summarizer.get_max_position()

    def encode(self, text_ip: str) -> List[str]:
        transcript_bpe = self.bpe.encode(text_ip)
        if len(transcript_bpe) > self.max_position - 30:
            if len(transcript_bpe) < self.max_position - 30 + 100:
                transcript_bpes = [transcript_bpe[: self.max_position - 30]]
            else:
                # apply sliding window on long transcripts with 2k token overlapping.
                num_sliding_windows = len(transcript_bpe) // 2000
                transcript_bpes = [
                    transcript_bpe[j * 2000 : j * 2000 + self.max_position - 60]
                    for j in range(num_sliding_windows)
                ]
        else:
            transcript_bpes = [transcript_bpe]

        transcript_bpes = [
            " ".join([str(b) for b in transcript_bpe])
            for transcript_bpe in transcript_bpes
        ]
        transcript_bpes = [
            transcript_bpe + " </s>" for transcript_bpe in transcript_bpes
        ]
        return transcript_bpes

    def generate(self, sents: List[str]) -> List[str]:
        params_tensor = params_to_tensor(
            beam=self.config.beam,
            temperature=self.config.temperature,
            min_ratio=self.config.ratio,
            max_len_b=self.config.maxlen,
            no_repeat_ngram_size=self.config.no_repeat_ngram_size,
        )
        hypos = self.summarizer.generate(sents, params_tensor, self.config.api_key)
        return hypos

    def decode(self, hyps: List[str]) -> str:
        concat_summary = []
        for hyp in hyps:
            best_summary = self.bpe.decode([int(b) for b in hyp.split(" ")]).strip()
            if best_summary[-1] != ".":
                best_summary += "."
            concat_summary.append(best_summary)
        # concat_summary_str = " ".join(concat_summary)
        concat_summary_str = concat_summary[0] if concat_summary else ""
        return concat_summary_str

    @classmethod
    def from_pretrained(
        cls, model_dir: Union[Path, str], config: SummConfig = SummConfig()
    ):
        model_dir = Path(model_dir)

        logger.info("Start loading models from disk ...")

        summarizer = _birchsumm.Model(
            str(model_dir / config.model_name), str(model_dir / "dict.src.txt")
        )
        bpe = get_encoder(
            model_dir / "gpt2_bpe" / "encoder.json",
            model_dir / "gpt2_bpe" / "vocab.bpe",
        )
        logger.info("Finish loading models ...")
        model = cls(bpe, summarizer, config)
        return model


def params_to_tensor(
    beam: int,
    temperature: float,
    min_ratio: float,
    max_len_b: int,
    no_repeat_ngram_size: int,
):
    return torch.tensor(
        [beam, temperature, min_ratio, max_len_b, no_repeat_ngram_size],
        dtype=torch.float64,
    )
