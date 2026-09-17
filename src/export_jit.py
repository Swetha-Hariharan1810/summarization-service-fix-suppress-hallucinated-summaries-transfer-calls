import argparse
import io
import shutil
from pathlib import Path
from typing import List

import torch

from summ_service.config import SummConfig
from summ_service.summ_model import SummModel


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        required=True,
        help="Model directory",
    )
    parser.add_argument(
        "--output-model-name",
        type=str,
        required=True,
        help="Model path for the output jit model",
    )
    return parser


def encode_questions(questions: List[str], summ_model: SummModel):
    qbpes = [summ_model.bpe.encode(q + "\t") for q in questions]
    qbpes = [" ".join([str(b) for b in qbpe]) for qbpe in qbpes]
    q_encoded = [
        summ_model.summarizer.task.source_dictionary.encode_line(
            qbpe, append_eos=False
        ).to(torch.long)
        for qbpe in qbpes
    ]
    return q_encoded


def encode_filler(config: SummConfig, summ_model: SummModel):
    filler_bpe = summ_model.bpe.encode(config.question_filler)
    filler_bpe_str = " ".join([str(b) for b in filler_bpe])
    filler_encoded = summ_model.summarizer.task.source_dictionary.encode_line(
        filler_bpe_str, append_eos=False
    )
    return filler_encoded.to(torch.long)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    config = SummConfig()
    summ_model = SummModel.from_pretrained(args.model_dir, config)
    model_dir = Path(args.model_dir)
    model_path = model_dir / config.model_version
    qbpes = encode_questions(config.questions, summ_model)
    filler = encode_filler(config, summ_model)
    # fairseq model doesn't use filler anymore
    summ_model.summarizer.set_questions(qbpes)
    summarizaer_scripted = torch.jit.script(summ_model.summarizer)
    buffer = io.BytesIO()
    num_written = buffer.write(
        b"birch is awesome!birch is awesome!birch is awesome!birch is"
        b" awesome!birch is awesome!"
    )
    print(f"Beginning: {num_written=}")
    torch.jit.save(summarizaer_scripted, buffer)
    num_written = buffer.write(
        b"birch is awesome!birch is awesome!birch is awesome!birch is"
    )
    print(f"End: {num_written=}")
    with open(
        model_path / args.output_model_name, "wb"
    ) as out:  ## Open temporary file as bytes
        out.write(buffer.getbuffer())  ## Read bytes into file

    # remove eager version models
    (model_path / f"{config.model_name}.pt").unlink()
    for f in model_path.glob("*.zip"):
        f.unlink()
    shutil.rmtree(model_path / "task_verification_model")
    shutil.move(model_path, model_dir / "jit-model")
