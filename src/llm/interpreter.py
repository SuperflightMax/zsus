"""LLM Interpreter that maps Ukrainian text to structured core commands."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .system_prompt import SYSTEM_PROMPT

ALLOWED_INTENTS = {"intake", "move", "consume", "find", "list", "unknown"}


@dataclass
class InterpreterResult:
    intent: str
    confidence: float
    needs_confirmation: bool
    human_summary: str
    command: Optional[Dict[str, Any]]
    questions: List[str]
    debug: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "needs_confirmation": self.needs_confirmation,
            "human_summary": self.human_summary,
            "command": self.command,
            "questions": self.questions,
            "debug": self.debug or {},
        }


class Interpreter:
    """LLM-based interpreter that outputs the core JSON contract."""

    def __init__(self, config: Dict[str, Any], client: Optional[OpenAI] = None):
        self._config = config or {}
        self._client = client

    def interpret(self, text: str) -> Dict[str, Any]:
        debug: Dict[str, Any] = {}
        if not self._is_enabled():
            result = InterpreterResult(
                intent="unknown",
                confidence=0.0,
                needs_confirmation=True,
                human_summary="LLM недоступний, інтерпретація не виконана.",
                command=None,
                questions=["Спробуйте пізніше або увімкніть LLM."],
                debug={"error": "LLM disabled"},
            )
            return result.to_dict()

        try:
            raw_json = self._call_llm(text)
            debug["raw_llm_response"] = raw_json
            parsed = self._safe_load_json(raw_json)
        except Exception as exc:  # noqa: BLE001
            # Defensive fallback to unknown intent on any error.
            debug["error"] = str(exc)
            parsed = None

        if not isinstance(parsed, dict):
            return self._fallback_unknown("Не вдалося інтерпретувати запит.", debug).to_dict()

        normalized = self._normalize_response(parsed)
        threshold = self._confidence_threshold()
        validated_command = self._validate_command(normalized.intent, normalized.command)
        needs_confirmation = self._calculate_confirmation(
            normalized.intent,
            normalized.confidence,
            validated_command,
            normalized.needs_confirmation,
            threshold,
        )

        normalized.command = validated_command
        normalized.needs_confirmation = needs_confirmation
        normalized.debug = debug
        return normalized.to_dict()

    def _is_enabled(self) -> bool:
        env_flag = os.getenv("LLM_ENABLED")
        if env_flag is not None:
            return env_flag.lower() in {"1", "true", "yes", "on"}

        llm_config = self._config.get("llm", {}) if isinstance(self._config, dict) else {}
        return bool(llm_config.get("enabled"))

    def _confidence_threshold(self) -> float:
        core_config = self._config.get("core", {}) if isinstance(self._config, dict) else {}
        try:
            return float(core_config.get("confidence_threshold", 0.7))
        except (TypeError, ValueError):
            return 0.7

    def _call_llm(self, text: str) -> str:
        client = self._client or self._create_client()
        model = os.getenv("OPENAI_MODEL") or self._config.get("llm", {}).get("model", "gpt-4.1")

        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )

        message = response.choices[0].message
        if hasattr(message, "content") and message.content:
            return message.content
        raise ValueError("Empty LLM response")

    def _create_client(self) -> OpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM is enabled")
        base_url = os.getenv("OPENAI_BASE_URL") or None
        client = OpenAI(api_key=api_key, base_url=base_url)
        self._client = client
        return client

    def _safe_load_json(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _normalize_response(self, data: Dict[str, Any]) -> InterpreterResult:
        intent = str(data.get("intent") or "unknown").lower()
        if intent not in ALLOWED_INTENTS:
            intent = "unknown"

        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        needs_confirmation = bool(data.get("needs_confirmation", False))
        human_summary = str(data.get("human_summary") or "")
        questions = [str(q) for q in data.get("questions") or [] if q]
        command = data.get("command") if intent != "unknown" else None

        if not human_summary:
            human_summary = self._default_summary(intent)

        if intent == "unknown" and not questions:
            questions = ["Не зовсім зрозумів запит. Уточніть, будь ласка."]

        return InterpreterResult(
            intent=intent,
            confidence=confidence,
            needs_confirmation=needs_confirmation,
            human_summary=human_summary,
            command=command if isinstance(command, dict) else None,
            questions=questions,
        )

    def _validate_command(self, intent: str, command: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not command or not isinstance(command, dict):
            return None

        if command.get("command") != intent and intent != "unknown":
            return None

        payload = command.get("payload")
        if not isinstance(payload, dict):
            return None

        if intent == "intake":
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                return None
            normalized_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = item.get("item_id")
                qty = item.get("qty")
                location = item.get("location") if item.get("location") is not None else None
                if not item_id or not self._is_positive_number(qty):
                    continue
                normalized_items.append({"item_id": str(item_id), "qty": qty, "location": location})

            if not normalized_items:
                return None
            return {"command": "intake", "payload": {"items": normalized_items}}

        if intent == "move":
            item_id = payload.get("item_id")
            qty = payload.get("qty")
            if not item_id or not self._is_positive_number(qty):
                return None
            return {
                "command": "move",
                "payload": {
                    "item_id": str(item_id),
                    "qty": qty,
                    "from": payload.get("from"),
                    "to": payload.get("to"),
                },
            }

        if intent == "consume":
            item_id = payload.get("item_id")
            qty = payload.get("qty")
            if not item_id or not self._is_positive_number(qty):
                return None
            return {
                "command": "consume",
                "payload": {"item_id": str(item_id), "qty": qty, "from": payload.get("from")},
            }

        if intent == "find":
            item_id = payload.get("item_id")
            if not item_id:
                return None
            return {"command": "find", "payload": {"item_id": str(item_id)}}

        if intent == "list":
            return {"command": "list", "payload": {}}

        return None

    def _calculate_confirmation(
        self,
        intent: str,
        confidence: float,
        command: Optional[Dict[str, Any]],
        model_flag: bool,
        threshold: float,
    ) -> bool:
        if intent == "unknown":
            return True
        if intent == "consume":
            return True
        if command is None:
            return True
        if confidence < threshold:
            return True
        if model_flag:
            return True
        return False

    def _default_summary(self, intent: str) -> str:
        summaries = {
            "intake": "Додати вказані предмети на склад.",
            "move": "Перемістити предмети між локаціями.",
            "consume": "Списати або видати предмети.",
            "find": "Знайти предмет на складі.",
            "list": "Показати всі залишки складу.",
            "unknown": "Невідомий намір.",
        }
        return summaries.get(intent, "Невідомий намір.")

    def _is_positive_number(self, value: Any) -> bool:
        try:
            return float(value) > 0
        except (TypeError, ValueError):
            return False

    def _fallback_unknown(self, summary: str, debug: Optional[Dict[str, Any]] = None) -> InterpreterResult:
        return InterpreterResult(
            intent="unknown",
            confidence=0.0,
            needs_confirmation=True,
            human_summary=summary,
            command=None,
            questions=["Спробуйте уточнити запит."],
            debug=debug,
        )
