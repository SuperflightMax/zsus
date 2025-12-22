"""LLM-backed interpreter that converts free-form text to core commands."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI


DEFAULT_UNKNOWN_SUMMARY = "Не зрозумів запит. Спробуйте переформулювати."


@dataclass
class Interpretation:
    intent: str
    confidence: float
    human_summary_ua: str
    command: Optional[Dict[str, Any]]
    error: Optional[str] = None


class _OpenAIClient:
    """Thin wrapper over OpenAI chat completions used by the interpreter."""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content or ""


class Interpreter:
    """LLM-backed intent interpreter using OpenAI GPT-4.1."""

    def __init__(self, config: Dict[str, Any], client: Optional[_OpenAIClient] = None):
        self._config = config
        llm_config = config.get("llm", {})
        self._enabled = bool(llm_config.get("enabled", False))
        self._model = os.getenv("OPENAI_MODEL") or llm_config.get("model") or "gpt-4.1"
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") or llm_config.get("base_url")
        self._client = client if client is not None else (self._build_client(api_key, base_url) if self._enabled else None)

    def interpret(self, text: str) -> Dict[str, Any]:
        if not self._enabled:
            return self._asdict(
                Interpretation(
                    intent="unknown",
                    confidence=0.0,
                    human_summary_ua="LLM вимкнено. Нічого не виконано.",
                    command=None,
                )
            )

        if not text or not text.strip():
            return self._unknown()

        if self._client is None:
            return self._asdict(
                Interpretation(
                    intent="unknown",
                    confidence=0.0,
                    human_summary_ua="LLM недоступний: немає ключа або клієнта.",
                    command=None,
                    error="LLM client not configured",
                )
            )

        try:
            raw_text = self._call_model(text.strip())
            parsed = self._parse_llm_response(raw_text)
        except Exception as exc:  # broad on purpose to avoid leaking stack traces
            return self._asdict(
                Interpretation(
                    intent="unknown",
                    confidence=0.0,
                    human_summary_ua=DEFAULT_UNKNOWN_SUMMARY,
                    command=None,
                    error=str(exc),
                )
            )

        enriched = self._apply_defaults(parsed)
        return self._asdict(enriched)

    # internals

    def _build_client(self, api_key: Optional[str], base_url: Optional[str]) -> Optional[_OpenAIClient]:
        if not api_key:
            return None
        return _OpenAIClient(model=self._model, api_key=api_key, base_url=base_url)

    def _call_model(self, prompt: str) -> str:
        system_prompt = (
            "Ти LLM-інтерпретатор. Перетвори вхідний текст на JSON з полями: intent (intake|move|consume|find|list|unknown), "
            "confidence (0..1), human_summary_ua (українською), command (або null). intent/command мають відповідати core: "
            "intake items[{item_id, qty, location|null}], move {item_id, qty, from, to}, consume {item_id, qty, from|null}, "
            "find {item_id}, list {}. Якщо запит незрозумілий — intent=unknown, command=null, confidence=0. "
            "Якщо qty не вказана для intake/consume — став qty=1. item_id і human_summary_ua українською. Відповідай ТІЛЬКИ JSON."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self._client.complete(messages)

    def _parse_llm_response(self, text: str) -> Interpretation:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError("LLM response is not valid JSON")

        intent = payload.get("intent") or "unknown"
        confidence = float(payload.get("confidence") or 0.0)
        human_summary = payload.get("human_summary_ua") or DEFAULT_UNKNOWN_SUMMARY
        command = payload.get("command")

        return Interpretation(intent=intent, confidence=confidence, human_summary_ua=human_summary, command=command)

    def _apply_defaults(self, interpretation: Interpretation) -> Interpretation:
        intent = interpretation.intent
        command = interpretation.command

        if intent in {"intake", "consume"} and command:
            if intent == "intake":
                items = command.get("payload", {}).get("items") if isinstance(command, dict) else None
                if items and isinstance(items, list):
                    for item in items:
                        if "qty" not in item or not item.get("qty"):
                            item["qty"] = 1
                        if "location" not in item:
                            item["location"] = None
            if intent == "consume":
                payload = command.get("payload") if isinstance(command, dict) else None
                if isinstance(payload, dict):
                    if "qty" not in payload or not payload.get("qty"):
                        payload["qty"] = 1
                    if "from" not in payload:
                        payload["from"] = None

        return interpretation

    @staticmethod
    def _asdict(result: Interpretation) -> Dict[str, Any]:
        data = {
            "intent": result.intent,
            "confidence": float(result.confidence),
            "human_summary_ua": result.human_summary_ua,
            "command": result.command,
        }
        if result.error:
            data["error"] = result.error
        return data

    @staticmethod
    def _unknown() -> Dict[str, Any]:
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "human_summary_ua": DEFAULT_UNKNOWN_SUMMARY,
            "command": None,
        }
