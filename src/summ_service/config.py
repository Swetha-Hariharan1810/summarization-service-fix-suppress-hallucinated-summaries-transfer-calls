from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel

import config

settings = config.get_settings()


class SummConfig(BaseModel):
    model_version: str = settings.SUMM_MODEL_VERSION
    model_url: str = settings.SUMM_MODEL_DOWNLOAD_PATH
    model_name: str = settings.SUMM_MODEL_NAME
    general_model: str = settings.GENERAL_SUMMARY

    questions: List[str] = ["Summarize this conversation with details?"]
    summary_exclude: List[str] = [
        "The customer needs to complete a customer service satisfaction survey"
    ]
    word_to_digit: bool = False
    minlen: int = 5
    maxlen: int = 500
    beam: int = 4
    no_repeat_ngram_size: int = 3
    temperature: float = 1.0
    semantic_threshold = 0.83
    sliding_windows: bool = False
    generate_reason: bool = False
    remove_lower_case: bool = True
    ratio: List[float] = [0.05, 0.1]
    device: str = "cpu"

    reasons: Dict[str, List[str]] = {
        "Caller checking on case status": [
            "Caller checking on case status.",
            "Caller asking the status of the case.",
        ],
    }
    question_filler: str = "the agent"

    def check_all_model_files(self, model_dir: Union[Path, str]) -> bool:
        model_dir = Path(model_dir)
        if not (model_dir / f"{self.model_name}.pt").exists():
            return False
        if not (model_dir / "gpt2_bpe" / "encoder.json").exists():
            return False
        if not (model_dir / "gpt2_bpe" / "vocab.bpe").exists():
            return False

        if not (model_dir / "task_verification_model" / "pytorch_model.bin"):
            return False

        return True
