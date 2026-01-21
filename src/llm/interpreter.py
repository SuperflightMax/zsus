"""LLM interpreter stub."""

from __future__ import annotations

from typing import Any, Dict


class Interpreter:
    """Stub interpreter with always-on LLM placeholder behavior."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config

    def interpret(self, text: str) -> Dict[str, Any]:
        return {
            "status": "ok",
            "message": "LLM placeholder",
            "input": text,
        }
