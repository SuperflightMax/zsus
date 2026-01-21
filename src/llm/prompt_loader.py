"""Prompt loader for LLM system/user templates."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


class PromptLoader:
    """Load prompt templates from the prompts directory."""

    def __init__(self, base_dir: Path | None = None):
        self._base_dir = base_dir or Path(__file__).resolve().parents[2] / "prompts"

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def load(self, name: str) -> str:
        path = self._base_dir / name
        return path.read_text(encoding="utf-8")

    def load_all(self, names: Dict[str, str]) -> Dict[str, str]:
        return {key: self.load(filename) for key, filename in names.items()}
