import json
from uuid import uuid4

from src.core.engine import CoreEngine, InMemoryStorageBackend
from src.llm.adapter import InteractionContext, LLMAdapter2Pass
from src.llm.client import LLMClient, LLMUnavailableError


class StaticLLMClient(LLMClient):
    def __init__(self, responses):
        self._responses = list(responses)
        self._model = "test-model"

    @property
    def model(self):
        return self._model

    def generate(self, system_prompt: str, user_payload: str, response_format=None) -> str:
        if not self._responses:
            raise AssertionError("No more responses configured")
        return self._responses.pop(0)


class UnavailableLLMClient(LLMClient):
    @property
    def model(self):
        return "test-model"

    def generate(self, system_prompt: str, user_payload: str, response_format=None) -> str:
        raise LLMUnavailableError("LLM down")


def _interaction(text: str) -> InteractionContext:
    return InteractionContext(
        interaction_id=str(uuid4()),
        language_policy={"input": "any", "output": "uk"},
        turns=[{"role": "user", "content": text}],
    )


def _adapter(client, engine, threshold=0.7):
    return LLMAdapter2Pass(llm_client=client, confidence_threshold=threshold, engine=engine)


def test_pass1_invalid_json_rejected_and_core_unchanged():
    backend = InMemoryStorageBackend()
    engine = CoreEngine(backend=backend)
    before = backend.get_storage_snapshot("test")

    client = StaticLLMClient([
        "not-json",
        "Не вдалося зрозуміти запит.",
    ])
    adapter = _adapter(client, engine)
    result = adapter.run(
        interaction_context=_interaction("add batteries"),
        allowed_intents=["add"],
        mvp_mode=True,
        storage_id="test",
    )

    after = backend.get_storage_snapshot("test")
    assert before == after
    assert result.ok is False
    assert isinstance(result.user_text, str) and result.user_text
    assert any("reason: unknown_intent" in line for line in result.system_log)


def test_low_confidence_rejected_and_core_unchanged():
    backend = InMemoryStorageBackend()
    engine = CoreEngine(backend=backend)
    before = backend.get_storage_snapshot("test")

    pass1 = json.dumps(
        {"draft_command": {"intent": "add", "item": "кабель"}, "confidence": 0.1},
        ensure_ascii=False,
    )
    client = StaticLLMClient([
        pass1,
        "Запит незрозумілий.",
    ])
    adapter = _adapter(client, engine, threshold=0.7)
    result = adapter.run(
        interaction_context=_interaction("додай кабель"),
        allowed_intents=["add"],
        mvp_mode=True,
        storage_id="test",
    )

    after = backend.get_storage_snapshot("test")
    assert before == after
    assert result.ok is False
    assert isinstance(result.user_text, str) and result.user_text
    assert any("reason: low_confidence" in line for line in result.system_log)


def test_move_missing_to_location_rejected():
    backend = InMemoryStorageBackend()
    engine = CoreEngine(backend=backend)

    pass1 = json.dumps({"intent": "move", "item": "рація", "confidence": 0.9}, ensure_ascii=False)
    client = StaticLLMClient([
        pass1,
        "Не вистачає даних для переміщення.",
    ])
    adapter = _adapter(client, engine)
    result = adapter.run(
        interaction_context=_interaction("перемісти рацію"),
        allowed_intents=["move"],
        mvp_mode=True,
        storage_id="test",
    )

    assert result.ok is False
    assert isinstance(result.user_text, str) and result.user_text
    assert any("reason: missing_required_fields" in line for line in result.system_log)


def test_llm_unavailable_rejected():
    backend = InMemoryStorageBackend()
    engine = CoreEngine(backend=backend)
    before = backend.get_storage_snapshot("test")

    adapter = _adapter(UnavailableLLMClient(), engine)
    result = adapter.run(
        interaction_context=_interaction("додай щось"),
        allowed_intents=["add"],
        mvp_mode=True,
        storage_id="test",
    )

    after = backend.get_storage_snapshot("test")
    assert before == after
    assert result.ok is False
    assert isinstance(result.user_text, str) and result.user_text
    assert any("reason: llm_unavailable" in line for line in result.system_log)
