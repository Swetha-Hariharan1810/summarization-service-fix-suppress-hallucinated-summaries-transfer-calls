# summarization process using summ_service package and SummModel
import argparse
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple

import torch

from preprocess import word_to_digit
from preprocess.process_transcripts import (
    aggregate_by_channel,
    clean_transcript,
    clean_transfer,
    get_symbol_to_word,
    has_caller_channel,
)
from postprocess.service import mdt_post_process
from summ_service.config import SummConfig
from summ_service.summ_model import SummModel

w2d_obj = word_to_digit.get_word_to_digit()
logger = logging.getLogger(__name__)

# Transfer / routing phrases used to detect calls that were handed off to
# another queue before the caller stated a reason.
_TRANSFER_PATTERNS = [
    r"let me get you to",
    r"let me get you over",
    r"connect you with",
    r"get you to the right",
    r"transfer(?:ring)? you",
    r"not trained (?:with|on)",
    r"i'?m not trained",
    r"you'?re on the .{0,25}line",
    r"wrong (?:line|department|queue|number)",
    r"one moment while i get",
    r"interpreter",
    r"i need to get you there",
    r"right group of people",
    r"the right (?:team|group|department|spot|people)",
    r"i'?ll (?:get|put) you (?:through|over)",
    r"put you through to",
]
_TRANSFER_RE = re.compile("|".join(_TRANSFER_PATTERNS), re.IGNORECASE)

MIN_WORDS = 26
TRANSFER_MIN_WORDS = 150
TRANSFER_MAX_WORDS = 1000
SUMMARY_TO_CALLER_RATIO = 3

def _has_transfer_language(text: str) -> bool:
    """True if the transcript contains any transfer/routing phrase."""
    return bool(_TRANSFER_RE.search(text or ""))


def _has_transfer_language_any(*variants: str) -> bool:
    """True if any transcript variant carries transfer language.

    Neither the preprocessed nor the raw transcript is sufficient alone:

    * aggregate_by_channel runs clean_transcript with phrases_removal
      enabled, which strips "one moment". The "one moment while i get"
      pattern therefore can never match the preprocessed text.
    * That same preprocessing folds the typographic apostrophe and drops
      punctuation, which is what lets "i'?m", "i'?ll" and "you'?re" match
      "im", "ill" and "youre". Those patterns fail on raw transcripts
      written with a typographic apostrophe.

    Checking both keeps whichever representation preserved the phrase.
    """
    return any(_has_transfer_language(v) for v in variants)


def get_summary(text: str, summ_model: SummModel) -> Tuple[str, str]:
    
    raw_text = text
    # 1. Preprocess input text
    text = aggregate_by_channel(text)
    text = " ".join([tt for tt in text.split("\n") if tt])

    if summ_model.config.word_to_digit:
        text = get_symbol_to_word(text)
        try:
            text = w2d_obj.text_to_int_dialog(text)
        except ValueError:
            logger.exception("Got exception on word_to_digit")

    text = clean_transcript(
        [text], phrases_removal=False, words_removal=False, after_number=True
    )[0]
    logging.debug(f"Preprocess input:\n{text}")

    # Guard: do not summarize empty/too-short transcripts.
    # These are typically calls that were transferred or dropped before the
    # caller stated a reason. 

    if not text or len(text.split()) < MIN_WORDS:
        logger.info(
            "Transcript too short for summarization (%d words); returning empty summary.",
            len(text.split()),
        )
        return "Empty Call", "Empty Call"

    transcript_len = len(text.split())

    check_short_transfer = (
        transcript_len <= TRANSFER_MIN_WORDS
        and _has_transfer_language_any(text, raw_text)
        and has_caller_channel(raw_text)
    )
    if check_short_transfer:
        logger.info(
            "Transfer transcript too short for summarization (%d words); returning short transfer summary.",
            len(text.split()),
        )
        return "Short Transfer Call", "Short Transfer Call"


    # Detected before generation, applied after it.
    input_len = None
    check_transfer = (
        TRANSFER_MIN_WORDS < transcript_len <= TRANSFER_MAX_WORDS
        and _has_transfer_language_any(text, raw_text)
        and has_caller_channel(raw_text)
    )
    if check_transfer:
        caller_only = clean_transfer(raw_text)
        input_len = len(caller_only.split())

    # 2. Generate summary
    tokens, truncate = summ_model.encode(text)
    summary_tokens = summ_model.forward(tokens)
    summary = summ_model.decode(summary_tokens)
    summary = mdt_post_process(summary)

    # Guard: transfer/routing call where the summary is not a compression of
    # the transcript. anything that does not is not summarizing.
    summary_len = len(summary.split())
    if check_transfer and summary_len >= SUMMARY_TO_CALLER_RATIO * input_len:
        return "Transfer Call", "Transfer Call"

    # 3. Post-process summary, generate reasons if needed
    # if truncate and summ_model.sliding_windows:
    # processed_summary = summ_model.process_summary(summary)
    reason = ""
    # if summ_config.generate_reason:
    #     reason = summ_model.generate_reason(processed_summary)
    return summary, reason


def get_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--model-dir", "-m", type=str, required=True)
    parser.add_argument("--model-version", "-v", type=str, required=True)
    parser.add_argument("--model-name", "-n", type=str, required=True)
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        required=True,
        help="directory to store outputs",
    )
    parser.add_argument(
        "input_files",
        type=str,
        nargs="+",
        help="input text files to run summarization",
    )
    parser.add_argument("--device", "-d", type=str, required=False, default="cpu")
    parser.add_argument(
        "--cpu-workers", default=1, type=int, help="number of cpu workers"
    )
    return parser


if __name__ == "__main__":
    import pandas as pd

    formatter = "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
    logging.basicConfig(format=formatter, level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    # setup intra_op multi-processing in pytorch.

    torch.set_num_threads(args.cpu_workers)
    logger.info(
        "Setting summary model to use parallelization(intra-op) with"
        f" {args.cpu_workers} cores"
    )
    summ_config = SummConfig()
    summ_config.device = args.device
    summ_config.model_version = args.model_version
    summ_config.model_name = args.model_name
    summ_model = SummModel.from_pretrained(args.model_dir, summ_config)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(exist_ok=True, parents=True)

    run_id = datetime.now().isoformat()

    time_records = []
    for text_file in args.input_files:
        text = open(text_file).read()
        start_time = time.perf_counter()
        summary_processed, reason = get_summary(text, summ_model)
        end_time = time.perf_counter()
        processed_time = end_time - start_time
        transcript_length = len(text.split())
        summary_length = len(summary_processed.split())
        logger.info(
            f"{text_file}:{transcript_length=} {summary_length=} {processed_time}"
        )
        time_records.append(
            {
                "processing_time": processed_time,
                "filename": Path(text_file).stem,
                "transcript_len": transcript_length,
                "summary_len": summary_length,
            }
        )
        with open(output_dir / f"{Path(text_file).stem}.txt", "w") as f:
            f.write(summary_processed)
    df = pd.DataFrame(time_records)

    df.to_csv(output_dir / f"{run_id}-timerecords.csv", index=False)