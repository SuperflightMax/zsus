from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from src.interfaces.cli.main import _handle_text_input


class _DummyInterpreter:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def interpret(self, text: str) -> Dict[str, Any]:  # noqa: ANN001
        return self._payload


def test_handle_text_executes_without_confirmation(monkeypatch, capsys):
    called = {}

    def _fake_handle_command(command: Dict[str, Any]):  # noqa: ANN001
        called["command"] = command
        return {"status": "ok", "data": {}}

    monkeypatch.setattr("src.interfaces.cli.main.handle_command", _fake_handle_command)

    interpreter = _DummyInterpreter(
        {
            "intent": "intake",
            "confidence": 0.9,
            "needs_confirmation": False,
            "human_summary": "Додати швабру.",
            "command": {"command": "intake", "payload": {"items": [{"item_id": "швабра", "qty": 1, "location": None}]}},
            "questions": [],
        }
    )

    _handle_text_input(
        "додай швабру",
        active_storage_id="s1",
        interpreter=interpreter,
        table_max_width=24,
    )

    assert called["command"]["storage_id"] == "s1"
    assert called["command"]["command"] == "intake"
    assert called["command"]["payload"]["items"][0]["item_id"] == "швабра"

    printed = capsys.readouterr().out
    assert '"intent": "intake"' in printed


def test_handle_text_skips_on_confirmation_decline(monkeypatch, capsys):
    def _fake_input(prompt: str) -> str:  # noqa: ANN001
        return "n"

    monkeypatch.setattr("builtins.input", _fake_input)
    monkeypatch.setattr("src.interfaces.cli.main.handle_command", lambda *_args, **_kwargs: pytest.fail("should not run"))

    interpreter = _DummyInterpreter(
        {
            "intent": "consume",
            "confidence": 0.9,
            "needs_confirmation": True,
            "human_summary": "Списати аптечки.",
            "command": {"command": "consume", "payload": {"item_id": "аптечка", "qty": 1, "from": None}},
            "questions": ["Підтвердьте списання."],
        }
    )

    _handle_text_input(
        "спиши аптечки",
        active_storage_id="s1",
        interpreter=interpreter,
        table_max_width=24,
    )

    printed = capsys.readouterr().out
    assert "Skipped." in printed


def test_handle_text_requires_active_storage(monkeypatch, capsys):
    monkeypatch.setattr("src.interfaces.cli.main.handle_command", lambda *_args, **_kwargs: pytest.fail("should not run"))

    interpreter = _DummyInterpreter(
        {
            "intent": "intake",
            "confidence": 0.9,
            "needs_confirmation": False,
            "human_summary": "Додати швабру.",
            "command": {"command": "intake", "payload": {"items": [{"item_id": "швабра", "qty": 1, "location": None}]}},
            "questions": [],
        }
    )

    _handle_text_input(
        "додай швабру",
        active_storage_id=None,
        interpreter=interpreter,
        table_max_width=24,
    )

    printed = capsys.readouterr().out
    assert "No active storage" in printed
