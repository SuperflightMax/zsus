import copy
import sqlite3
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
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 3.0, "unit": "од"}}}

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
    assert list_response.data == {"radio": {"null": {"qty": 3.0, "unit": "од"}}}


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
    assert engine.backend.get_storage_snapshot(storage_id) == {"radio": {"shelf": {"qty": 1.0, "unit": "од"}}}


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

    assert snapshot(backend, "one") == {"radio": {None: {"qty": 2.0, "unit": "од"}}}
    assert snapshot(backend, "two") == {"radio": {"box": {"qty": 5.0, "unit": "од"}}}


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


def test_unit_column_migrates_existing_db(tmp_path: Path):
    storage_id = "legacy_storage"
    storages_root = tmp_path / "storages"
    db_path = storages_root / storage_id / "storage.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE items (
            item_name  TEXT NOT NULL,
            location   TEXT,
            qty        INTEGER NOT NULL,
            PRIMARY KEY (item_name, location)
        )
        """
    )
    conn.execute("INSERT INTO items (item_name, location, qty) VALUES (?, ?, ?)", ("radio", None, 2))
    conn.commit()
    conn.close()

    backend = SqliteStorageBackend(storages_root)
    snapshot_data = backend.get_storage_snapshot(storage_id)

    assert snapshot_data == {"radio": {None: {"qty": 2.0, "unit": "од"}}}
