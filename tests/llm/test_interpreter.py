import json
from typing import Any, Dict

import pytest

from src.llm.interpreter import Interpreter, _OpenAIClient


def make_config(enabled: bool = True) -> dict:
    return {"llm": {"enabled": enabled, "model": "gpt-4.1"}}


class DummyClient(_OpenAIClient):
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload

    def complete(self, messages: list[dict[str, str]]) -> str:
        return json.dumps(self.payload)


@pytest.mark.parametrize(
    "text,expected_intent,expected_item,expected_qty",
    [
        ("додай молоток", "intake", "молоток", 1),
        ("додай 3 рації", "intake", "рації", 3),
        ("спиши аптечку", "consume", "аптечку", 1),
    ],
)
def test_intake_and_consume_intents(text, expected_intent, expected_item, expected_qty):
    payload = {
        "intent": expected_intent,
        "confidence": 0.9,
        "human_summary_ua": "ok",
        "command": {
            "command": expected_intent,
            "payload": (
                {"items": [{"item_id": expected_item, "qty": expected_qty, "location": None}]}
                if expected_intent == "intake"
                else {"item_id": expected_item, "qty": expected_qty, "from": None}
            ),
        },
    }
    interpreter = Interpreter(make_config(), client=DummyClient(payload))

    result = interpreter.interpret(text)

    assert result["intent"] == expected_intent
    assert result["command"] is not None
    if expected_intent == "intake":
        item = result["command"]["payload"]["items"][0]
        assert item["item_id"] == expected_item
        assert item["qty"] == expected_qty
    elif expected_intent == "consume":
        payload = result["command"]["payload"]
        assert payload["item_id"] == expected_item
        assert payload["qty"] == expected_qty


def test_find_intent_extracts_item():
    payload = {
        "intent": "find",
        "confidence": 0.8,
        "human_summary_ua": "Пошук: бинт.",
        "command": {"command": "find", "payload": {"item_id": "бинт"}},
    }
    interpreter = Interpreter(make_config(), client=DummyClient(payload))

    result = interpreter.interpret("де бинт")

    assert result["intent"] == "find"
    assert result["command"]["payload"]["item_id"] == "бинт"
    assert "Пошук" in result["human_summary_ua"]


def test_gibberish_falls_back_to_unknown():
    interpreter = Interpreter(make_config(), client=DummyClient({"intent": "unknown", "confidence": 0.0, "command": None}))

    result = interpreter.interpret("asdf qwerty")

    assert result["intent"] == "unknown"
    assert result["command"] is None
    assert "Не зрозумів" in result["human_summary_ua"]


def test_disabled_llm_reports_unknown():
    interpreter = Interpreter(make_config(enabled=False))

    result = interpreter.interpret("додай молоток")

    assert result["intent"] == "unknown"
    assert result["command"] is None
    assert "вимкнено" in result["human_summary_ua"]
