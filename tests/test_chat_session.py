from src.llm.llm_operator import LLMResult, SnapshotResult
from src.session.chat_session import ChatSession


class DummyLLMOperator:
    def __init__(self, llm_result: LLMResult) -> None:
        self._llm_result = llm_result

    def run(self, *, user_text: str, active_storage_id: str, dialogue_context: str):
        snapshot = SnapshotResult(ok=True, snapshot_text="snapshot", snapshot_json={}, system_log=[])
        return self._llm_result, snapshot, "test-model"


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


def test_chat_session_clears_context_on_success():
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
    assert session.dialogue_context == []


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
