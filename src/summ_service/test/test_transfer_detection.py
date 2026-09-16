"""Transfer-language detection must survive preprocessing.

get_summary matches _TRANSFER_PATTERNS to decide whether a short call is a
transfer. Preprocessing helps some patterns and destroys others, so the
match is run against both the preprocessed and the raw transcript. These
tests pin that down in both directions.
"""
import pytest

from preprocess.process_transcripts import aggregate_by_channel, clean_transcript
from summ_main import _has_transfer_language, _has_transfer_language_any

# A transcript using the typographic apostrophe, as real ASR output often does.
RSQUO = "’"


def preprocess(raw):
    """Reproduce the preprocessing get_summary applies before matching."""
    text = aggregate_by_channel(raw)
    text = " ".join(tt for tt in text.split("\n") if tt)
    return clean_transcript(
        [text], phrases_removal=False, words_removal=False, after_number=True
    )[0]


def test_one_moment_survives_only_in_raw_text():
    """phrases_removal strips 'one moment', killing the pattern downstream."""
    raw = "Agent: Okay, one moment while I get that sorted out.\nCaller: Sure."
    assert not _has_transfer_language(preprocess(raw))
    assert _has_transfer_language(raw)
    assert _has_transfer_language_any(preprocess(raw), raw)


@pytest.mark.parametrize(
    "raw",
    [
        f"Agent: I{RSQUO}m not trained for that question.\nCaller: Oh.",
        f"Agent: I{RSQUO}ll put you through now.\nCaller: Thanks.",
        f"Agent: You{RSQUO}re on the sales line here.\nCaller: Ah.",
    ],
)
def test_apostrophe_patterns_survive_only_in_preprocessed_text(raw):
    """Preprocessing folds the apostrophe; the raw form will not match."""
    assert _has_transfer_language(preprocess(raw))
    assert not _has_transfer_language(raw)
    assert _has_transfer_language_any(preprocess(raw), raw)


def test_plain_transfer_language_matches_either_way():
    raw = "Agent: I am transferring you now.\nCaller: Ok."
    assert _has_transfer_language(preprocess(raw))
    assert _has_transfer_language(raw)


def test_non_transfer_call_is_not_flagged():
    raw = "Agent: Your order shipped yesterday.\nCaller: Great, thanks."
    assert not _has_transfer_language_any(preprocess(raw), raw)
