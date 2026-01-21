from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.app.message_handler import (
    DEFAULT_STORAGE_MISSING,
    DEFAULT_USER_FALLBACK,
    handle_user_message,
)
from src.core.result import OperationResult


class FakeInterpreter:
    def __init__(self, parsed: Dict[str, Any], ok: bool = True):
        self._parsed = parsed
        self._ok = ok

    def interpret(self, input_text: str, interaction_context: Dict[str, Any], snapshot_summary: Dict[str, Any]):
        return {"ok": self._ok, "raw": "{}", "parsed": self._parsed, "error": None if self._ok else "error"}


class FakeResponder:
    def __init__(self, text: str, ok: bool = True):
        self._text = text
        self._ok = ok

    def respond(self, context: Dict[str, Any]):
        return {"ok": self._ok, "raw": self._text, "text": self._text, "error": None if self._ok else "fail"}


class RecordingCore:
    def __init__(self, result: OperationResult):
        self.calls: List[Dict[str, Any]] = []
        self._result = result

    def __call__(self, command: Dict[str, Any]) -> OperationResult:
        self.calls.append(command)
        return self._result


@pytest.fixture()
def base_config():
    return {"core": {"confidence_threshold": 0.7}, "llm": {"enabled": True}}


def test_missing_active_storage_blocks_core(base_config):
    core = RecordingCore(OperationResult.success())
    result = handle_user_message(
        "що є на складі",
        active_storage_id=None,
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter({"confidence": 0.9, "draft_command": {"intent": "list_inventory"}}),
        responder=FakeResponder("ok"),
    )

    assert result.ok is False
    assert result.user_text == DEFAULT_STORAGE_MISSING
    assert core.calls == []


def test_low_confidence_blocks_core(base_config):
    core = RecordingCore(OperationResult.success())
    result = handle_user_message(
        "додай аптечку",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter({"confidence": 0.2, "draft_command": {"intent": "intake"}}),
        responder=FakeResponder("ok"),
    )

    assert result.ok is False
    assert result.user_text == DEFAULT_USER_FALLBACK
    assert core.calls
    assert core.calls[0]["command"] == "list"


def test_intake_without_location_allows_null_location(base_config):
    core = RecordingCore(OperationResult.success())
    result = handle_user_message(
        "додай 5 аптечок",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter(
            {
                "confidence": 0.9,
                "draft_command": {"intent": "intake", "item_id": "аптечка", "qty": 5},
            }
        ),
        responder=FakeResponder("Готово."),
    )

    assert result.ok is True
    executable = result.data["executable_command"]
    assert executable["command"] == "intake"
    assert executable["payload"]["items"][0]["location"] is None


def test_list_inventory_executes_and_returns_user_text(base_config):
    core = RecordingCore(OperationResult.success(data={"аптечка": {"null": 2}}))
    result = handle_user_message(
        "що є на складі",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter({"confidence": 0.95, "draft_command": {"intent": "list_inventory"}}),
        responder=FakeResponder("Є: аптечка — 2."),
    )

    assert result.ok is True
    assert result.user_text == "Є: аптечка — 2."


def test_user_text_pipeline_uses_active_storage_only(base_config):
    core = RecordingCore(OperationResult.success())
    handle_user_message(
        "додай 1 аптечку",
        active_storage_id="active_1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter(
            {"confidence": 0.9, "draft_command": {"intent": "intake", "item_id": "аптечка", "qty": 1}}
        ),
        responder=FakeResponder("Готово."),
    )

    assert core.calls[-1]["storage_id"] == "active_1"
