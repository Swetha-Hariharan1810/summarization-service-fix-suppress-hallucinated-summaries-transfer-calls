import logging
from pathlib import Path

import pandas as pd
import pytest

import summ_main
from summ_service.config import SummConfig
from summ_service.summ_model import SummModel

logger = logging.getLogger(__name__)


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


def test_summ_service(test_df, summ_model):
    for text, summary in zip(test_df["Transcripts"], test_df["V9"]):
        # we only verify the summary is not empty
        hyp, _ = summ_main.get_summary(text, summ_model)
        assert hyp != ""
        # assert hyp == summary


# Test main.py with local model path
# def test_summ_old(test_df):
#     import main
#     for text, summary in zip(test_df["Transcripts"], test_df["V9"]):
#         hyp, _, _ = main.get_summary(1234, None, text)
#         assert hyp == summary
