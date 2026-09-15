import os
from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel


class SummConfig(BaseModel):
    model_name = os.getenv("MODEL_NAME", "v11.jit.pt")
    ratio: float = 0.0
    word_to_digit: bool = True
    minlen: int = 5
    maxlen: int = 200
    beam: int = 4
    no_repeat_ngram_size: int = 3
    temperature: float = 0.5
    semantic_threshold = 0.83
    generate_reason: bool = False
    remove_lower_case: bool = True
    api_key: str = os.getenv(
        "API_KEY",
        "",
    )

    def check_all_model_files(self, models_dir: Union[Path, str]) -> bool:
        models_dir = Path(models_dir)
        if not (models_dir / f"{self.model_name}.pt").exists():
            return False
        if not (models_dir / "gpt2_bpe" / "encoder.json").exists():
            return False
        if not (models_dir / "gpt2_bpe" / "vocab.bpe").exists():
            return False

        if not (models_dir / "task_tracking" / "pytorch_model.bin"):
            return False

        return True
