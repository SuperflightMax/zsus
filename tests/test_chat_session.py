import json

from src.core.result import OperationResult
from src.llm.llm_operator import LLMResult, SnapshotResult
from src.session.chat_session import ChatSession


class DummyLLMOperator:
    def __init__(self, llm_result: LLMResult) -> None:
        self._llm_result = llm_result

    def run(self, *, user_text: str, active_storage_id: str, dialogue_context: str):
        snapshot = SnapshotResult(ok=True, snapshot_text="snapshot", snapshot_json={}, system_log=[])
        return self._llm_result, snapshot, "test-model"


class SequenceLLMOperator:
    def __init__(self, llm_results):
        self._llm_results = list(llm_results)
        self.dialogue_contexts = []

    def run(self, *, user_text: str, active_storage_id: str, dialogue_context: str):
        self.dialogue_contexts.append(dialogue_context)
        snapshot = SnapshotResult(ok=True, snapshot_text="snapshot", snapshot_json={}, system_log=[])
        if self._llm_results:
            llm_result = self._llm_results.pop(0)
        else:
            llm_result = LLMResult(
                ok=True,
                assistant_text="ok",
                commands=[],
                need_more_info=False,
                questions=[],
                raw_response=None,
                parsed=None,
                system_log=[],
            )
        return llm_result, snapshot, "test-model"


def test_chat_session_keeps_context_on_need_more_info():
    llm_result = LLMResult(
        ok=True,
        assistant_text="Need more details.",
        commands=[],
        need_more_info=True,
        questions=["Question 1"],
        raw_response=None,
        parsed=None,
        system_log=[],
    )
    session = ChatSession(active_storage_id="storage", llm_operator=DummyLLMOperator(llm_result))

    result = session.handle_text("Hello")

    assert result.ok is True
    assert "Питання" in (result.user_text or "")
    assert session.dialogue_context == ["USER: Hello", "ASSISTANT: Need more details."]


def test_chat_session_keeps_context_tail_on_success():
    llm_result = LLMResult(
        ok=True,
        assistant_text="All set.",
        commands=[],
        need_more_info=False,
        questions=[],
        raw_response=None,
        parsed=None,
        system_log=[],
    )
    session = ChatSession(active_storage_id="storage", llm_operator=DummyLLMOperator(llm_result))

    result = session.handle_text("Process")

    assert result.ok is True
    assert session.dialogue_context == ["USER: Process", "ASSISTANT: All set."]


def test_chat_session_clears_context_on_failure():
    llm_result = LLMResult(
        ok=False,
        assistant_text="Failed.",
        commands=[],
        need_more_info=False,
        questions=[],
        raw_response=None,
        parsed=None,
        system_log=[],
    )
    session = ChatSession(active_storage_id="storage", llm_operator=DummyLLMOperator(llm_result))

    result = session.handle_text("Oops")

    assert result.ok is False
    assert session.dialogue_context == []


def test_chat_session_logs_audit_context_for_successful_command(monkeypatch, tmp_path):
    llm_result = LLMResult(
        ok=True,
        assistant_text="Done.",
        commands=[
            {
                "command": "intake",
                "payload": {"items": [{"item_id": "mask", "qty": 1}]},
                "storage_id": "ACTIVE_STORAGE",
            }
        ],
        need_more_info=False,
        questions=[],
        raw_response=None,
        parsed=None,
        system_log=[],
    )
    session = ChatSession(active_storage_id="st", llm_operator=DummyLLMOperator(llm_result))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.session.chat_session.handle_command",
        lambda command_payload: OperationResult.success(user_text="ok", system_log=[]),
    )

    result = session.handle_text(
        "Прийми маску",
        operator_id=" Falcon ",
        client_id=" client-123 ",
        source=" http ",
    )

    assert result.ok is True
    log_entry = json.loads((tmp_path / "logs" / "actions.log").read_text(encoding="utf-8").strip())
    assert log_entry["storage_id"] == "st"
    assert log_entry["command"] == "intake"
    assert log_entry["client_id"] == "client-123"
    assert log_entry["operator_id"] == "Falcon"
    assert log_entry["source"] == "http"
    assert log_entry["core_ok"] is True
    assert "core_error" not in log_entry


def test_chat_session_logs_audit_context_for_failed_command(monkeypatch, tmp_path):
    llm_result = LLMResult(
        ok=True,
        assistant_text="Trying.",
        commands=[
            {
                "command": "move",
                "payload": {"item_id": "mask", "qty": 2, "from": "A", "to": "B"},
                "storage_id": "ACTIVE_STORAGE",
            }
        ],
        need_more_info=False,
        questions=[],
        raw_response=None,
        parsed=None,
        system_log=[],
    )
    session = ChatSession(active_storage_id="st", llm_operator=DummyLLMOperator(llm_result))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.session.chat_session.handle_command",
        lambda command_payload: OperationResult.failure(user_text="not enough stock", system_log=[]),
    )

    result = session.handle_text(
        "Перемісти маску",
        operator_id="Raven",
        client_id="client-999",
        source="http",
    )

    assert result.ok is False
    log_entry = json.loads((tmp_path / "logs" / "actions.log").read_text(encoding="utf-8").strip())
    assert log_entry["command"] == "move"
    assert log_entry["client_id"] == "client-999"
    assert log_entry["operator_id"] == "Raven"
    assert log_entry["source"] == "http"
    assert log_entry["core_ok"] is False
    assert log_entry["core_error"] == "not enough stock"


def test_chat_session_success_path_keeps_last_three_pairs():
    llm_result = LLMResult(
        ok=True,
        assistant_text="Done.",
        commands=[],
        need_more_info=False,
        questions=[],
        raw_response=None,
        parsed=None,
        system_log=[],
    )
    llm_operator = SequenceLLMOperator([llm_result, llm_result, llm_result, llm_result])
    session = ChatSession(active_storage_id="storage", llm_operator=llm_operator)

    session.handle_text("one")
    session.handle_text("two")
    session.handle_text("three")
    result = session.handle_text("four")

    assert result.ok is True
    assert llm_operator.dialogue_contexts[-1] == (
        "USER: one\n"
        "ASSISTANT: Done.\n"
        "USER: two\n"
        "ASSISTANT: Done.\n"
        "USER: three\n"
        "ASSISTANT: Done.\n"
        "USER: four"
    )
    assert session.dialogue_context == [
        "USER: two",
        "ASSISTANT: Done.",
        "USER: three",
        "ASSISTANT: Done.",
        "USER: four",
        "ASSISTANT: Done.",
    ]
