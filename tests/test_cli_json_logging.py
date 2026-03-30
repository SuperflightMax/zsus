import json

from src.core.result import OperationResult
from src.interfaces.cli.main import _process_json_block


def _read_single_log_entry(tmp_path):
    log_path = tmp_path / "logs" / "actions.log"
    raw = log_path.read_text(encoding="utf-8").strip()
    return json.loads(raw)


def test_json_cli_logs_operator_id_and_source_from_meta(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.interfaces.cli.main.handle_command",
        lambda payload: OperationResult.success(user_text="ok", system_log=[]),
    )

    _process_json_block(
        json.dumps(
            {
                "meta": {"operator_id": " Falcon ", "source": " agent_whatsapp "},
                "command": "move",
                "payload": {"item": "ammo_545", "from": "A1", "to": "B2", "qty": 10},
            },
            ensure_ascii=False,
        ),
        "st",
    )

    log_entry = _read_single_log_entry(tmp_path)
    assert log_entry["storage_id"] == "st"
    assert log_entry["operator_id"] == "Falcon"
    assert log_entry["source"] == "agent_whatsapp"
    assert log_entry["command"] == "move"
    assert log_entry["core_ok"] is True


def test_json_cli_logs_without_operator_id_when_meta_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.interfaces.cli.main.handle_command",
        lambda payload: OperationResult.success(user_text="ok", system_log=[]),
    )

    _process_json_block(
        json.dumps(
            {
                "command": "intake",
                "payload": {"items": [{"item": "ammo_545", "qty": 10}]},
            },
            ensure_ascii=False,
        ),
        "st",
    )

    log_entry = _read_single_log_entry(tmp_path)
    assert log_entry["operator_id"] is None
    assert log_entry["source"] == "cli"
    assert log_entry["core_ok"] is True


def test_json_cli_failure_logs_operator_source_and_core_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.interfaces.cli.main.handle_command",
        lambda payload: OperationResult.failure(user_text="not enough stock", system_log=[]),
    )

    _process_json_block(
        json.dumps(
            {
                "meta": {"operator_id": "Falcon", "source": "agent_whatsapp"},
                "command": "move",
                "payload": {"item": "ammo_545", "from": "A1", "to": "B2", "qty": 999},
            },
            ensure_ascii=False,
        ),
        "st",
    )

    log_entry = _read_single_log_entry(tmp_path)
    assert log_entry["operator_id"] == "Falcon"
    assert log_entry["source"] == "agent_whatsapp"
    assert log_entry["core_ok"] is False
    assert log_entry["core_error"] == "not enough stock"
