from __future__ import annotations

import json
from typing import Any

import pytest

from src.llm.interpreter import Interpreter


def _mock_llm(monkeypatch, payload: dict[str, Any]) -> None:
    def _fake_call_llm(self, text: str) -> str:  # noqa: ANN001
        return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(Interpreter, "_call_llm", _fake_call_llm, raising=True)


def test_intake_confident_no_confirmation(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")
    _mock_llm(
        monkeypatch,
        {
            "intent": "intake",
            "confidence": 0.92,
            "needs_confirmation": False,
            "human_summary": "Додати аптечки.",
            "command": {
                "command": "intake",
                "payload": {"items": [{"item_id": "аптечка", "qty": 5, "location": None}]},
            },
            "questions": [],
        },
    )

    interpreter = Interpreter(config={"core": {"confidence_threshold": 0.7}})
    result = interpreter.interpret("додай 5 аптечок")

    assert result["intent"] == "intake"
    assert result["needs_confirmation"] is False
    assert result["command"] == {
        "command": "intake",
        "payload": {"items": [{"item_id": "аптечка", "qty": 5, "location": None}]},
    }


def test_consume_always_needs_confirmation(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")
    _mock_llm(
        monkeypatch,
        {
            "intent": "consume",
            "confidence": 0.95,
            "needs_confirmation": False,
            "human_summary": "Списати аптечки.",
            "command": {"command": "consume", "payload": {"item_id": "аптечка", "qty": 2, "from": None}},
            "questions": [],
        },
    )

    interpreter = Interpreter(config={})
    result = interpreter.interpret("спиши аптечки")

    assert result["intent"] == "consume"
    assert result["needs_confirmation"] is True


def test_low_confidence_triggers_confirmation(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")
    _mock_llm(
        monkeypatch,
        {
            "intent": "find",
            "confidence": 0.5,
            "needs_confirmation": False,
            "human_summary": "Знайти аптечки.",
            "command": {"command": "find", "payload": {"item_id": "аптечка"}},
            "questions": [],
        },
    )

    interpreter = Interpreter(config={"core": {"confidence_threshold": 0.8}})
    result = interpreter.interpret("покажи де аптечки")

    assert result["intent"] == "find"
    assert result["needs_confirmation"] is True


def test_invalid_json_falls_back_to_unknown(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")

    def _bad_llm(self, text: str) -> str:  # noqa: ANN001
        return "not-a-json"

    monkeypatch.setattr(Interpreter, "_call_llm", _bad_llm, raising=True)

    interpreter = Interpreter(config={})
    result = interpreter.interpret("шось не то")

    assert result["intent"] == "unknown"
    assert result["command"] is None
    assert result["needs_confirmation"] is True
    assert result["questions"]
    assert result["debug"]["raw_llm_response"] == "not-a-json"


def test_disabled_llm_returns_unknown(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    interpreter = Interpreter(config={})
    result = interpreter.interpret("будь-який запит")

    assert result["intent"] == "unknown"
    assert result["command"] is None
    assert result["needs_confirmation"] is True


def test_error_in_llm_call_exposed_in_debug(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")

    def _raise_llm(self, text: str) -> str:  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(Interpreter, "_call_llm", _raise_llm, raising=True)

    interpreter = Interpreter(config={})
    result = interpreter.interpret("будь-який запит")

    assert result["intent"] == "unknown"
    assert result["debug"]["error"] == "boom"
