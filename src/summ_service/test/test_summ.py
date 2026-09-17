import logging
from pathlib import Path

import pandas as pd
import pytest

import summ_main
from summ_service.config import SummConfig
from summ_service.summ_model import SummModel

logger = logging.getLogger(__name__)

# Sentinels returned by summ_main.get_summary instead of a generated summary.
EMPTY_CALL = "Empty Call"
SHORT_TRANSFER_CALL = "Short Transfer Call"
TRANSFER_CALL = "Transfer Call"

# Every transcript in the regression corpus is 341-1140 words once
# preprocessed, so neither pre-generation guard can legitimately fire:
#   * MIN_WORDS (26)           -> EMPTY_CALL
#   * TRANSFER_MIN_WORDS (150) -> SHORT_TRANSFER_CALL
# Either one appearing means suppression has started swallowing ordinary
# calls, which is the regression this corpus exists to catch.
UNREACHABLE_SENTINELS = (EMPTY_CALL, SHORT_TRANSFER_CALL)

# Only two transcripts carry transfer/routing language, so only those two can
# reach the post-generation transfer guard. The rest must produce real text.
MAX_EXPECTED_TRANSFER_CALLS = 2


@pytest.fixture(scope="module")
def test_df():
    return pd.read_csv(
        Path(__file__).parent / "test_data" / "SummarizationTestsnoDiverseResults5.csv"
    )


@pytest.fixture(scope="module")
def summ_model(tmp_path_factory):
    summ_config = SummConfig()
    models_dir = tmp_path_factory.mktemp("models")
    summ_model = SummModel.from_pretrained(models_dir, summ_config)
    return summ_model


@pytest.fixture(scope="module")
def summaries(test_df, summ_model):
    """Summarize the corpus once; the assertions below all read this."""
    return [
        summ_main.get_summary(text, summ_model)[0] for text in test_df["Transcripts"]
    ]


def test_corpus_is_long_enough_to_exercise_the_model(test_df):
    """Guard the assumption the suppression assertions below rely on."""
    for idx, text in enumerate(test_df["Transcripts"]):
        word_count = len(str(text).split())
        assert word_count > summ_main.TRANSFER_MIN_WORDS, (
            f"transcript {idx} is {word_count} words, short enough to trip a "
            "pre-generation guard; the suppression assertions no longer hold"
        )


def test_no_summary_is_empty(summaries):
    for idx, hyp in enumerate(summaries):
        assert hyp != "", f"transcript {idx} produced an empty summary"


def test_ordinary_calls_are_not_suppressed(summaries):
    for idx, hyp in enumerate(summaries):
        assert hyp not in UNREACHABLE_SENTINELS, (
            f"transcript {idx} was suppressed as {hyp!r}, but it is far above "
            "both the MIN_WORDS and TRANSFER_MIN_WORDS thresholds"
        )


def test_transfer_suppression_stays_bounded(summaries):
    suppressed = [idx for idx, hyp in enumerate(summaries) if hyp == TRANSFER_CALL]
    assert len(suppressed) <= MAX_EXPECTED_TRANSFER_CALLS, (
        f"{len(suppressed)} transcripts suppressed as {TRANSFER_CALL!r} "
        f"(indices {suppressed}); at most {MAX_EXPECTED_TRANSFER_CALLS} carry "
        "transfer language, so the guard is over-firing"
    )


# Exact-match against the stored V9 column is deliberately not asserted: model
# output drifts between checkpoints, so it would fail on every model bump.


# Test main.py with local model path
# def test_summ_old(test_df):
#     import main
#     for text, summary in zip(test_df["Transcripts"], test_df["V9"]):
#         hyp, _, _ = main.get_summary(1234, None, text)
#         assert hyp == summary
