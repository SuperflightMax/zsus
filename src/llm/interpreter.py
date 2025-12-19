"""LLM interpreter stub."""

from __future__ import annotations

from typing import Any, Dict


class Interpreter:
    """Stub interpreter that respects LLM enablement flag."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config

    def interpret(self, text: str) -> Dict[str, Any]:
        llm_config = self._config.get("llm", {})
        if not llm_config.get("enabled", False):
            return {
                "status": "disabled",
                "message": "LLM disabled",
            }

        return {
            "status": "ok",
            "message": "LLM placeholder",
            "input": text,
        }
