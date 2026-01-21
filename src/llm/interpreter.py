"""LLM interpreter for DraftCommand generation."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .openai_client import OpenAIClient
from .prompt_loader import PromptLoader


class Interpreter:
    """LLM-based interpreter that returns DraftCommand JSON."""

    def __init__(self, config: Dict[str, Any], client: OpenAIClient | None = None, loader: PromptLoader | None = None):
        self._config = config
        self._client = client or OpenAIClient(config)
        self._loader = loader or PromptLoader()

    def interpret(self, input_text: str, interaction_context: Dict[str, Any], snapshot_summary: Dict[str, Any]) -> Dict[str, Any]:
        llm_config = self._config.get("llm", {})
        if not llm_config.get("enabled", False):
            return {
                "ok": False,
                "raw": None,
                "parsed": None,
                "error": "LLM disabled",
            }

        system_prompt = self._loader.load("interpret.system.md")
        user_prompt = self._loader.load("interpret.user.md").format(
            interaction_context=json.dumps(interaction_context, ensure_ascii=False),
            snapshot_summary=json.dumps(snapshot_summary, ensure_ascii=False),
            input_text=input_text,
        )

        response = self._client.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        if not response.ok or not response.content:
            return {
                "ok": False,
                "raw": response.content,
                "parsed": None,
                "error": response.error or "LLM response missing",
            }

        parsed = _parse_json(response.content)
        if parsed is None:
            return {
                "ok": False,
                "raw": response.content,
                "parsed": None,
                "error": "Invalid JSON from LLM",
            }

        return {
            "ok": True,
            "raw": response.content,
            "parsed": parsed,
            "error": None,
        }


def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None
