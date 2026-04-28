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

    assert response.ok is True
    assert response.data == {}
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 3.0, "unit": "од"}}}


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

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: {"qty": 3.0, "unit": "од"}},
        "battery": {"box": {"qty": 5.0, "unit": "од"}},
    }


def test_intake_same_item_twice(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    command = {
        "command": "intake",
        "storage_id": storage_id,
        "payload": {"items": [{"item_id": "radio", "qty": 2, "location": None}]},
    }
    first = engine.handle_command(command)
    second = engine.handle_command(command)

    assert first.ok is True
    assert second.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 4.0, "unit": "од"}}}


def test_intake_invalid_qty(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 0, "location": None}]},
        }
    )

    assert response.ok is False
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

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: {"qty": 3.0, "unit": "од"}, "box_1": {"qty": 2.0, "unit": "од"}},
    }


def test_location_alias_sklad(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    intake_response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 5, "location": " склад "}]},
        }
    )

    assert intake_response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 5.0, "unit": "од"}}}

    move_response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 2, "from": "склад", "to": "кухня"},
        }
    )

    assert move_response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: {"qty": 3.0, "unit": "од"}, "кухня": {"qty": 2.0, "unit": "од"}},
    }

    consume_response = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": "Склад"},
        }
    )

    assert consume_response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: {"qty": 2.0, "unit": "од"}, "кухня": {"qty": 2.0, "unit": "од"}},
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

    assert response.ok is False
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

    assert response.ok is False
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

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {"shelf": {"qty": 3.0, "unit": "од"}}}


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

    assert response.ok is True
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

    assert response.ok is False
    assert backend.get_storage_snapshot(storage_id) == before


def test_fractional_qty_and_unit(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    intake_response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "fuel", "qty": 1.5, "unit": "л", "location": None}]},
        }
    )

    assert intake_response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"fuel": {None: {"qty": 1.5, "unit": "л"}}}

    move_response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "fuel", "qty": 0.5, "from": None, "to": "can"},
        }
    )

    assert move_response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "fuel": {None: {"qty": 1.0, "unit": "л"}, "can": {"qty": 0.5, "unit": "л"}},
    }

    consume_response = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "fuel", "qty": 0.25, "from": "can"},
        }
    )

    assert consume_response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "fuel": {None: {"qty": 1.0, "unit": "л"}, "can": {"qty": 0.25, "unit": "л"}},
    }


def test_unit_kept_without_override(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "sand", "qty": 2, "unit": "кг", "location": "bag"}]},
        }
    )
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "sand", "qty": 1, "location": "bag"}]},
        }
    )

    assert backend.get_storage_snapshot(storage_id) == {"sand": {"bag": {"qty": 3.0, "unit": "кг"}}}


def test_intake_with_holder(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {
                "items": [
                    {
                        "item_id": "radio",
                        "qty": 1,
                        "location": "shelf",
                        "holder": "Сокіл +380000000000",
                    }
                ]
            },
        }
    )

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {"shelf": {"qty": 1.0, "unit": "од", "holder": "Сокіл +380000000000"}}
    }


def test_intake_without_holder_does_not_clear_existing_holder(
    engine: CoreEngine,
    backend: InMemoryStorageBackend,
    storage_id: str,
):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None, "holder": "Сокіл"}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None}]},
        }
    )

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: {"qty": 2.0, "unit": "од", "holder": "Сокіл"}}
    }


def test_move_can_set_holder_on_same_location(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None, "to": None, "holder": "Сокіл"},
        }
    )

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {
        "radio": {None: {"qty": 1.0, "unit": "од", "holder": "Сокіл"}}
    }


def test_move_can_clear_holder(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None, "holder": "Сокіл"}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "qty": 1, "from": None, "to": None, "holder": None},
        }
    )

    assert response.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 1.0, "unit": "од"}}}


def test_find_includes_holders_when_present(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio", "qty": 1, "location": None, "holder": "Сокіл"}]},
        }
    )

    response = engine.handle_command(
        {
            "command": "find",
            "storage_id": storage_id,
            "payload": {"item_id": "radio"},
        }
    )

    assert response.ok is True
    assert response.data == {
        "item_id": "radio",
        "total_qty": 1.0,
        "locations": {"null": 1.0},
        "holders": {"null": "Сокіл"},
    }


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

    assert response.ok is True
    assert response.data == {"item_id": "radio", "total_qty": 4.0, "locations": {"null": 4.0}}


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

    assert response.ok is True
    assert response.data == {
        "item_id": "radio",
        "total_qty": 4.0,
        "locations": {"null": 3.0, "shelf": 1.0},
    }


def test_find_nonexistent_item(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "find",
            "storage_id": storage_id,
            "payload": {"item_id": "radio"},
        }
    )

    assert response.ok is False


def test_list_empty_storage(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response = engine.handle_command(
        {
            "command": "list",
            "storage_id": storage_id,
            "payload": {},
        }
    )

    assert response.ok is True
    assert response.data == {}


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

    assert response.ok is True
    assert response.data == {
        "radio": {"null": {"qty": 1.0, "unit": "од"}, "box": {"qty": 1.0, "unit": "од"}},
        "battery": {"box": {"qty": 5.0, "unit": "од"}},
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

    assert response_other.ok is True
    assert response_other.data == {}
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 2.0, "unit": "од"}}}


def test_unknown_command_returns_error(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    before = snapshot(backend, storage_id)

    response = engine.handle_command(
        {
            "command": "unknown",
            "storage_id": storage_id,
            "payload": {},
        }
    )

    assert response.ok is False


def test_defaults_applied_by_policy(engine: CoreEngine, backend: InMemoryStorageBackend, storage_id: str):
    response_intake = engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio"}]},
        }
    )

    assert response_intake.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {None: {"qty": 1.0, "unit": "од"}}}

    response_consume = engine.handle_command(
        {
            "command": "consume",
            "storage_id": storage_id,
            "payload": {"item_id": "radio"},
        }
    )

    assert response_consume.ok is True
    assert backend.get_storage_snapshot(storage_id) == {}

    engine.handle_command(
        {
            "command": "intake",
            "storage_id": storage_id,
            "payload": {"items": [{"item_id": "radio"}]},
        }
    )

    response_move = engine.handle_command(
        {
            "command": "move",
            "storage_id": storage_id,
            "payload": {"item_id": "radio", "from": None, "to": "box"},
        }
    )

    assert response_move.ok is True
    assert backend.get_storage_snapshot(storage_id) == {"radio": {"box": {"qty": 1.0, "unit": "од"}}}
