import pytest

from src.interfaces.cli import main as cli_main


def test_service_user_output_separation(capsys, monkeypatch):
    # arrange: use a tiny interpreter stub to avoid engine calls
    class FakeInterpreter:
        def interpret(self, text: str):
            return {
                "intent": "unknown",
                "confidence": 0.1,
                "human_summary_ua": "Не зрозумів запит. Спробуйте переформулювати.",
                "command": None,
            }

    # capture output of handler directly
    cli_main._print_service_and_user({"intent": "unknown", "confidence": 0.1, "command": None}, "Не зрозумів")
    captured = capsys.readouterr().out

    assert "SERVICE" in captured
    assert "USER" in captured
    assert "Не зрозумів" in captured


def test_plain_text_without_storage(monkeypatch, capsys):
    # interpreter suggests a command but no active storage should block execution
    class FakeInterpreter:
        def interpret(self, text: str):
            return {
                "intent": "intake",
                "confidence": 1.0,
                "human_summary_ua": "Додав: молоток ×1.",
                "command": {"command": "intake", "payload": {"items": [{"item_id": "молоток", "qty": 1, "location": None}]}},
            }

    def fake_handle_command(cmd):
        raise AssertionError("handle_command should not be called without storage")

    monkeypatch.setattr(cli_main, "handle_command", fake_handle_command)

    cli_main._handle_plain_text_input(
        text="додай молоток",
        interpreter=FakeInterpreter(),
        active_storage_id=None,
        confidence_threshold=0.7,
    )

    captured = capsys.readouterr().out
    assert "Помилка активації сервісу." in captured
    assert "No active storage" in captured  # service section
