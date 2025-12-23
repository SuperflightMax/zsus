import copy
from pathlib import Path

from src.core.backends import SqliteStorageBackend
from src.core.engine import CoreEngine


def snapshot(backend: SqliteStorageBackend, storage_id: str):
    return copy.deepcopy(backend.get_storage_snapshot(storage_id))


def test_intake_and_persist_across_sessions(tmp_path: Path):
    storage_id = "sqlite_storage"
    storages_root = tmp_path / "storages"

    backend = SqliteStorageBackend(storages_root)
    engine = CoreEngine(backend=backend)

    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 3, "location": None}]},
        }
    )

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: 3}}

    # Recreate backend to ensure data persists on disk.
    backend_reopened = SqliteStorageBackend(storages_root)
    engine_reopened = CoreEngine(backend=backend_reopened)

    list_response = engine_reopened.handle_command(
        {
            "command": "list",
            "storage_id": storage_id,
            "payload": {},
        }
    )

    assert list_response.ok is True
    assert list_response.data == {"radio": {"null": 3}}


def test_move_and_consume_cleanup(tmp_path: Path):
    storage_id = "sqlite_storage"
    storages_root = tmp_path / "storages"
    engine = CoreEngine(SqliteStorageBackend(storages_root))

    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 3, "location": None}]},
        }
    )

    engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None, "to": "shelf"},
        }
    )

    consume_response = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 2, "from": None},
        }
    )

    assert consume_response.ok is True
    assert engine.backend.get_storage_snapshot(storage_id) == {"radio": {"shelf": 1}}


def test_multiple_storages_isolated(tmp_path: Path):
    storages_root = tmp_path / "storages"
    backend = SqliteStorageBackend(storages_root)
    engine = CoreEngine(backend=backend)

    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "one",
            "payload": {"items": [{"item_id": "radio", "qty": 2, "location": None}]},
        }
    )

    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "two",
            "payload": {"items": [{"item_id": "radio", "qty": 5, "location": "box"}]},
        }
    )

    assert snapshot(backend, "one") == {"radio": {None: 2}}
    assert snapshot(backend, "two") == {"radio": {"box": 5}}


def test_database_file_created_and_deleted(tmp_path: Path):
    storages_root = tmp_path / "storages"
    backend = SqliteStorageBackend(storages_root)
    storage_id = "alpha"

    # ensure storage creates DB file
    backend.ensure_storage(storage_id)
    db_path = storages_root / storage_id / "storage.db"
    assert db_path.exists()

    backend.delete_storage(storage_id)
    assert not db_path.exists()


def test_find_nonexistent_item_returns_error(tmp_path: Path):
    storages_root = tmp_path / "storages"
    engine = CoreEngine(SqliteStorageBackend(storages_root))
    storage_id = "sqlite_storage"

    before = engine.backend.get_storage_snapshot(storage_id)

    response = engine.handle_command(
        {
            "command": "find",
            "storage_id": storage_id,
            "payload": {"item_id": "missing"},
        }
    )

    assert response.ok is False
    assert engine.backend.get_storage_snapshot(storage_id) == before
