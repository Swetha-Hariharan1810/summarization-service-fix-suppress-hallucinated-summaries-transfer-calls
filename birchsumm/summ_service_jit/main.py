import argparse
import datetime
import logging
from pathlib import Path

from .config import SummConfig
from .preprocess import word_to_digit
from .preprocess.process_transcripts import (
    aggregate_by_channel,
    clean_transcript,
    get_symbol_to_word,
)
from .summ_model import SummModel

logger = logging.getLogger("summ_service_jit.main")

w2d_obj = word_to_digit.get_word_to_digit()


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
        "--input-dir",
        type=str,
        required=True,
        help="Directory that contains input files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to dump outputs",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        required=True,
        help="Directory to dump logs",
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        required=False,
        default=False,
        const=True,
        help="Whether to print out debug logs",
    )
    return parser


def get_summary(text: str, summ_model: SummModel) -> str:
    # 1. Preprocess input text
    text = aggregate_by_channel(text)
    text = " ".join([tt for tt in text.split("\n") if tt])
    text = get_symbol_to_word(text)
    if summ_model.config.word_to_digit:
        try:
            text = w2d_obj.text_to_int_dialog(text)
        except ValueError:
            logger.exception("Got exception on word_to_digit")
    # text = remove_punc(text)
    text = clean_transcript([text], after_number=True)[0]
    logging.debug(f"Preprocess input:\n{text}")
    # 2. Generate summary
    sents = summ_model.encode(text)
    hyps = summ_model.generate(sents)
    summary = summ_model.decode(hyps)

    return summary


def setup_logging(log_dir: Path, log_level=logging.INFO):
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(log_level)
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    fh = logging.FileHandler(log_dir / f"{logfile}.log", mode="a")
    fh.setFormatter(formatter)
    fh.setLevel(log_level)
    logging.root.handlers = [ch, fh]
    logging.root.setLevel(log_level)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    config = SummConfig()
    summ_model = SummModel.from_pretrained(args.model_dir, config)
    all_files = set()
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(Path(args.log_dir), log_level)

    if not input_path.exists():
        logger.error(f"{input_path} doesn't exist")
        import sys

        sys.exit(1)

    output_path.mkdir(exist_ok=True, parents=True)
    while True:
        input_files = input_path.glob("*.txt")
        new_files = set(input_files) - all_files
        if new_files:
            for f in new_files:
                logger.info(f"Processing input file {f}")
                text = f.read_text()
                summary = get_summary(text, summ_model)
                (output_path / f"{f.stem}.summ.txt").write_text(summary + "\n")
                logger.info(f"Finish processing input file {f}")
            all_files.update(new_files)
