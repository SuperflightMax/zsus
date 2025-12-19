import copy

import pytest

from src.core.engine import CoreEngine, InMemoryStorageBackend


@pytest.fixture()
def storage_id() -> str:
    return "test_storage"


@pytest.fixture()
def backend() -> InMemoryStorageBackend:
    return InMemoryStorageBackend()


@pytest.fixture()
def engine(backend: InMemoryStorageBackend) -> CoreEngine:
    return CoreEngine(backend=backend)


def snapshot(backend: InMemoryStorageBackend, storage_id: str):
    return copy.deepcopy(backend.get_storage_snapshot(storage_id))


def test_intake_single_item_new(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 3, "location": None}]},
        }
    )

    assert response == {"status": "ok", "data": {}}
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: 3}}


def test_intake_multiple_items(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {
                "items": [
                    {"item_id": "radio", "qty": 3, "location": None},
                    {"item_id": "battery", "qty": 5, "location": "box"},
                ]
            },
        }
    )

    assert response["status"] == "ok"
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: 3},
        "battery": {"box": 5},
    }


def test_intake_same_item_twice(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    command = {
        "command": "intake",
        "storage_id": storage_id,
        "payload": {"items": [{"item_id": "radio", "qty": 2, "location": None}]},
    }
    first = engine.handle_command(command)
    second = engine.handle_command(command)

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: 4}}


def test_intake_invalid_qty(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 0, "location": None}]},
        }
    )

    assert response["status"] == "error"
    assert backend.get_storage_snapshot(storage_id) == before


def test_move_between_locations(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 5, "location": None}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 2, "from": None, "to": "box_1"},
        }
    )

    assert response["status"] == "ok"
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: 3, "box_1": 2},
    }


def test_move_not_enough_qty(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 2, "location": None}]},
        }
    )
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 3, "from": None, "to": "box_1"},
        }
    )

    assert response["status"] == "error"
    assert backend.get_storage_snapshot(storage_id) == before


def test_move_nonexistent_item(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None, "to": "box_1"},
        }
    )

    assert response["status"] == "error"
    assert backend.get_storage_snapshot(storage_id) == before


def test_consume_from_location(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 5, "location": "shelf"}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 2, "from": "shelf"},
        }
    )

    assert response["status"] == "ok"
    assert backend.get_storage_snapshot(storage_id) == {"radio": {"shelf": 3}}


def test_consume_all_qty_removes_location(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None},
        }
    )

    assert response["status"] == "ok"
    assert backend.get_storage_snapshot(storage_id) == {}


def test_consume_not_enough_qty(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None}]},
        }
    )
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 2, "from": None},
        }
    )

    assert response["status"] == "error"
    assert backend.get_storage_snapshot(storage_id) == before


def test_find_single_location(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 4, "location": None}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "find",
            "storage_id": storage_id,
            "payload": {"item_id": "radio"},
        }
    )

    assert response == {
        "status": "ok",
        "data": {"item_id": "radio", "total_qty": 4, "locations": {"null": 4}},
    }


def test_find_multiple_locations(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 4, "location": None}]},
        }
    )
    engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None, "to": "shelf"},
        }
    )

    response = engine.handle_command(
        {
            "command": "find",
            "storage_id": storage_id,
            "payload": {"item_id": "radio"},
        }
    )

    assert response["status"] == "ok"
    assert response["data"] == {
        "item_id": "radio",
        "total_qty": 4,
        "locations": {"null": 3, "shelf": 1},
    }


def test_find_nonexistent_item(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "find",
            "storage_id": storage_id,
            "payload": {"item_id": "radio"},
        }
    )

    assert response["status"] == "error"


def test_list_empty_storage(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "list",
            "storage_id": storage_id,
            "payload": {},
        }
    )

    assert response == {"status": "ok", "data": {}}


def test_list_with_multiple_items(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {
                "items": [
                    {"item_id": "radio", "qty": 2, "location": None},
                    {"item_id": "battery", "qty": 5, "location": "box"},
                ]
            },
        }
    )
    engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None, "to": "box"},
        }
    )

    response = engine.handle_command(
        {
            "command": "list",
            "storage_id": storage_id,
            "payload": {},
        }
    )

    assert response["status"] == "ok"
    assert response["data"] == {
        "radio": {"null": 1, "box": 1},
        "battery": {"box": 5},
    }


def test_multiple_storages_are_isolated(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    other_storage = "other_storage"
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 2, "location": None}]},
        }
    )

    response_other = engine.handle_command(
        {
            "command": "list",
            "storage_id": other_storage,
            "payload": {},
        }
    )

    assert response_other == {"status": "ok", "data": {}}
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: 2}}


def test_unknown_command_returns_error(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "unknown",
            "storage_id": storage_id,
            "payload": {},
        }
    )

    assert response["status"] == "error"
    assert backend.get_storage_snapshot(storage_id) == before

