"""LLM responder for user-facing messages."""

from __future__ import annotations

import json
from typing import Any, Dict

from .openai_client import OpenAIClient
from .prompt_loader import PromptLoader


class Responder:
    """LLM-based responder that returns Ukrainian user text."""

    def __init__(self, config: Dict[str, Any], client: OpenAIClient | None = None, loader: PromptLoader | None = None):
        self._config = config
        self._client = client or OpenAIClient(config)
        self._loader = loader or PromptLoader()

    def respond(self, context: Dict[str, Any]) -> Dict[str, Any]:
        llm_config = self._config.get("llm", {})
        if not llm_config.get("enabled", False):
            return {
                "ok": False,
                "raw": None,
                "text": None,
                "error": "LLM disabled",
            }

        system_prompt = self._loader.load("respond.system.md")
        user_prompt = self._loader.load("respond.user.md").format(
            input_text=context.get("input_text"),
            validation_status=context.get("validation", {}).get("status"),
            validation_reason=context.get("validation", {}).get("reason"),
            execution_status=context.get("execution", {}).get("status"),
            execution_data=json.dumps(context.get("execution", {}).get("data"), ensure_ascii=False),
            inventory_summary=json.dumps(context.get("inventory_summary"), ensure_ascii=False),
            template_reply=context.get("template_reply"),
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
                "text": None,
                "error": response.error or "LLM response missing",
            }

        return {
            "ok": True,
            "raw": response.content,
            "text": response.content.strip(),
            "error": None,
        }
