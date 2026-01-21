from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.app.formatting import render_inventory_table
from src.app.message_handler import DEFAULT_STORAGE_MISSING, DEFAULT_USER_FALLBACK, handle_user_message
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


class RoutingCore:
    def __init__(self, handler):
        self.calls: List[Dict[str, Any]] = []
        self._handler = handler

    def __call__(self, command: Dict[str, Any]) -> OperationResult:
        self.calls.append(command)
        return self._handler(command)


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


def test_intake_defaults_qty_to_one(base_config):
    core = RecordingCore(OperationResult.success())
    result = handle_user_message(
        "додай аптечку",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter(
            {
                "confidence": 0.9,
                "draft_command": {"intent": "intake", "item_id": "аптечка"},
            }
        ),
        responder=FakeResponder("Готово."),
    )

    assert result.ok is True
    executable = result.data["executable_command"]
    assert executable["payload"]["items"][0]["qty"] == 1


def test_list_inventory_executes_and_returns_user_text(base_config):
    core = RecordingCore(OperationResult.success(data={"аптечка": {"null": 2}}))
    expected_table = "\n".join(
        render_inventory_table(
            {"аптечка": {"null": 2}},
            max_width=24,
            unplaced_label="склад",
            empty_message="Склад порожній.",
        )
    )
    result = handle_user_message(
        "що є на складі",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter({"confidence": 0.95, "draft_command": {"intent": "list_inventory"}}),
        responder=FakeResponder(expected_table),
    )

    assert result.ok is True
    assert result.user_text == expected_table


def test_find_reply_includes_locations(base_config):
    def handler(command: Dict[str, Any]) -> OperationResult:
        if command["command"] == "list":
            return OperationResult.success(data={})
        if command["command"] == "find":
            return OperationResult.success(
                data={"item_id": "стакан", "total_qty": 2, "locations": {"столі": 1, "null": 1}}
            )
        return OperationResult.success(data={})

    core = RoutingCore(handler)
    expected_reply = "Стакан: 1 на столі, 1 на складі."
    result = handle_user_message(
        "де стакан",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter({"confidence": 0.9, "draft_command": {"intent": "find", "item_id": "стакан"}}),
        responder=FakeResponder(expected_reply),
    )

    assert result.ok is True
    assert result.user_text == expected_reply


def test_move_all_expands_across_locations(base_config):
    def handler(command: Dict[str, Any]) -> OperationResult:
        if command["command"] == "list":
            return OperationResult.success(data={})
        if command["command"] == "find":
            return OperationResult.success(
                data={"item_id": "бинт", "total_qty": 3, "locations": {"null": 2, "ящик": 1}}
            )
        return OperationResult.success(data={})

    core = RoutingCore(handler)
    result = handle_user_message(
        "поклади всі бинти в аптечку",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter(
            {"confidence": 0.9, "draft_command": {"intent": "move", "item_id": "бинт", "qty": "all", "to": "аптечка"}}
        ),
        responder=FakeResponder("ok"),
    )

    assert result.ok is True
    move_calls = [call for call in core.calls if call["command"] == "move"]
    assert len(move_calls) == 2
    assert move_calls[0]["payload"]["to"] == "аптечка"
    assert move_calls[1]["payload"]["to"] == "аптечка"


def test_consume_without_from_expands_by_policy(base_config):
    def handler(command: Dict[str, Any]) -> OperationResult:
        if command["command"] == "list":
            return OperationResult.success(data={})
        if command["command"] == "find":
            return OperationResult.success(
                data={"item_id": "бинт", "total_qty": 4, "locations": {"null": 2, "коробка": 2}}
            )
        return OperationResult.success(data={})

    core = RoutingCore(handler)
    result = handle_user_message(
        "убери 3 бинта",
        active_storage_id="s1",
        config=base_config,
        core_handler=core,
        interpreter=FakeInterpreter({"confidence": 0.9, "draft_command": {"intent": "consume", "item_id": "бинт", "qty": 3}}),
        responder=FakeResponder("ok"),
    )

    assert result.ok is True
    consume_calls = [call for call in core.calls if call["command"] == "consume"]
    assert len(consume_calls) == 2
    assert consume_calls[0]["payload"]["from"] is None
    assert consume_calls[0]["payload"]["qty"] == 2
    assert consume_calls[1]["payload"]["from"] == "коробка"
    assert consume_calls[1]["payload"]["qty"] == 1


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
