"""Rule-based interpreter that maps free-form text to core commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_UNKNOWN_SUMMARY = "Не зрозумів запит. Спробуйте переформулювати."


@dataclass
class Interpretation:
    intent: str
    confidence: float
    human_summary_ua: str
    command: Optional[Dict[str, Any]]


class Interpreter:
    """Lightweight intent interpreter (no external LLM calls)."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        llm_config = config.get("llm", {})
        self._enabled = bool(llm_config.get("enabled", False))

    def interpret(self, text: str) -> Dict[str, Any]:
        """Interpret user text into a structured command payload.

        The interpreter intentionally stays simple and conservative:
        - No external calls
        - Only light heuristics and keywords
        - Defaults to a safe "unknown" with low confidence
        """

        if not self._enabled:
            return self._asdict(
                Interpretation(
                    intent="unknown",
                    confidence=0.0,
                    human_summary_ua="LLM вимкнено. Нічого не виконано.",
                    command=None,
                )
            )

        cleaned = (text or "").strip()
        if not cleaned:
            return self._unknown()

        lower = cleaned.lower()

        # list
        if self._contains_any(lower, ["список", "все на складе", "все на складі", "list", "весь склад"]):
            return self._asdict(
                Interpretation(
                    intent="list",
                    confidence=0.9,
                    human_summary_ua="Показати весь склад.",
                    command={"command": "list", "payload": {}},
                )
            )

        # find
        if self._contains_any(lower, ["де", "где", "найди", "знайди", "find", "ищи", "покажи где", "where"]):
            item = self._extract_item(cleaned, intent="find")
            if item:
                return self._asdict(
                    Interpretation(
                        intent="find",
                        confidence=0.88,
                        human_summary_ua=f"Пошук: {item}.",
                        command={"command": "find", "payload": {"item_id": item}},
                    )
                )

        # move (minimal support)
        if self._contains_any(lower, ["перенеси", "перемести", "переміст", "переклади", "переведи"]):
            parsed_move = self._parse_move(cleaned)
            if parsed_move:
                item, qty, from_loc, to_loc = parsed_move
                return self._asdict(
                    Interpretation(
                        intent="move",
                        confidence=0.8,
                        human_summary_ua=f"Перемістити: {item} ×{qty} з {from_loc or 'склад'} до {to_loc or 'склад'}.",
                        command={
                            "command": "move",
                            "payload": {
                                "item_id": item,
                                "qty": qty,
                                "from": from_loc,
                                "to": to_loc,
                            },
                        },
                    )
                )

        # consume
        if self._contains_any(lower, ["спиши", "списати", "списать", "выдай", "віддай", "відпиши", "расходуй", "списуй"]):
            item = self._extract_item(cleaned, intent="consume")
            qty = self._extract_qty(cleaned) or 1
            if item:
                return self._asdict(
                    Interpretation(
                        intent="consume",
                        confidence=0.87,
                        human_summary_ua=f"Списав: {item} ×{qty}.",
                        command={
                            "command": "consume",
                            "payload": {
                                "item_id": item,
                                "qty": qty,
                                "from": None,
                            },
                        },
                    )
                )

        # intake
        if self._contains_any(lower, ["додай", "добавь", "добавь", "добавити", "добавь", "добавь", "прийми", "прими", "поклади", "положи", "добав", "принять", "принеси"]):
            item = self._extract_item(cleaned, intent="intake")
            qty = self._extract_qty(cleaned) or 1
            if item:
                return self._asdict(
                    Interpretation(
                        intent="intake",
                        confidence=0.9,
                        human_summary_ua=f"Додав: {item} ×{qty}.",
                        command={
                            "command": "intake",
                            "payload": {
                                "items": [
                                    {
                                        "item_id": item,
                                        "qty": qty,
                                        "location": None,
                                    }
                                ]
                            },
                        },
                    )
                )

        return self._unknown()

    # helpers

    @staticmethod
    def _contains_any(text: str, keywords: Iterable[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _extract_qty(text: str) -> Optional[int]:
        match = re.search(r"(\d+)", text)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _extract_item(self, text: str, intent: str) -> Optional[str]:
        tokens = re.findall(r"[\w'’\-]+", text, flags=re.UNICODE)
        if not tokens:
            return None

        skip_keywords = {
            "intake": ["додай", "добавь", "добавити", "прийми", "прими", "поклади", "положи", "принеси"],
            "consume": ["спиши", "списати", "списать", "выдай", "віддай", "расходуй", "списуй", "відпиши"],
            "find": ["де", "где", "найди", "знайди", "find", "ищи", "покажи", "where"],
            "move": ["перенеси", "перемести", "переклади", "переведи"],
        }.get(intent, [])

        filtered: List[str] = []
        for token in tokens:
            lower = token.lower()
            if lower.isdigit():
                continue
            if lower in skip_keywords:
                continue
            filtered.append(token)

        if not filtered:
            return None

        return " ".join(filtered).strip()

    def _parse_move(self, text: str) -> Optional[tuple[str, int, Optional[str], Optional[str]]]:
        qty = self._extract_qty(text) or 1
        from_loc = None
        to_loc = None

        # naive pattern: "з <loc> в <loc>" / "из <loc> в <loc>"
        match = re.search(r"[ззiи]з?\s+([^\s]+)\s+[вву]\s+([^\s]+)", text, flags=re.IGNORECASE)
        if match:
            from_loc = match.group(1)
            to_loc = match.group(2)

        item = self._extract_item(text, intent="move")
        if not item:
            return None

        return item, qty, from_loc, to_loc

    @staticmethod
    def _asdict(result: Interpretation) -> Dict[str, Any]:
        return {
            "intent": result.intent,
            "confidence": float(result.confidence),
            "human_summary_ua": result.human_summary_ua,
            "command": result.command,
        }

    @staticmethod
    def _unknown() -> Dict[str, Any]:
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "human_summary_ua": DEFAULT_UNKNOWN_SUMMARY,
            "command": None,
        }
