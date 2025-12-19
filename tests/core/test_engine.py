import pytest

from src.core.engine import CoreEngine, InMemoryStorageBackend


def make_engine():
    return CoreEngine(InMemoryStorageBackend())


def test_intake_and_list():
    engine = make_engine()
    response = engine.handle_command(
        {
            "command": "intake",
            "storage_id": "s1",
            "payload": {
                "items": [
                    {"item_id": "fuel_barrel", "qty": 10, "location": None},
                    {"item_id": "fuel_barrel", "qty": 5, "location": "tank_1"},
                ]
            },
        }
    )
    assert response["status"] == "ok"

    listed = engine.handle_command({"command": "list", "storage_id": "s1", "payload": {}})
    assert listed == {
        "status": "ok",
        "data": {
            "fuel_barrel": {
                "null": 10,
                "tank_1": 5,
            }
        },
    }


def test_move_between_locations():
    engine = make_engine()
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "s1",
            "payload": {
                "items": [{"item_id": "fuel_barrel", "qty": 10, "location": None}]
            },
        }
    )

    move_response = engine.handle_command(
        {
            "command": "move",
            "storage_id": "s1",
            "payload": {
                "item_id": "fuel_barrel",
                "qty": 5,
                "from": None,
                "to": "tank_1",
            },
        }
    )
    assert move_response["status"] == "ok"

    listed = engine.handle_command({"command": "list", "storage_id": "s1", "payload": {}})
    assert listed["data"]["fuel_barrel"] == {"null": 5, "tank_1": 5}


def test_move_insufficient_qty_error():
    engine = make_engine()
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "s1",
            "payload": {
                "items": [{"item_id": "fuel_barrel", "qty": 2, "location": None}]
            },
        }
    )

    response = engine.handle_command(
        {
            "command": "move",
            "storage_id": "s1",
            "payload": {
                "item_id": "fuel_barrel",
                "qty": 3,
                "from": None,
                "to": "tank_1",
            },
        }
    )

    assert response["status"] == "error"
    assert "Not enough" in response["error"]


def test_consume_removes_empty_location():
    engine = make_engine()
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "s1",
            "payload": {
                "items": [
                    {"item_id": "fuel_barrel", "qty": 5, "location": None},
                    {"item_id": "fuel_barrel", "qty": 2, "location": "tank_1"},
                ]
            },
        }
    )

    consume = engine.handle_command(
        {
            "command": "consume",
            "storage_id": "s1",
            "payload": {
                "item_id": "fuel_barrel",
                "qty": 2,
                "from": "tank_1",
            },
        }
    )
    assert consume["status"] == "ok"

    listed = engine.handle_command({"command": "list", "storage_id": "s1", "payload": {}})
    assert listed["data"]["fuel_barrel"] == {"null": 5}


def test_consume_missing_item_or_location_errors():
    engine = make_engine()
    missing_item = engine.handle_command(
        {
            "command": "consume",
            "storage_id": "s1",
            "payload": {"item_id": "fuel_barrel", "qty": 1, "from": None},
        }
    )
    assert missing_item["status"] == "error"

    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "s1",
            "payload": {
                "items": [{"item_id": "fuel_barrel", "qty": 1, "location": None}]
            },
        }
    )
    missing_location = engine.handle_command(
        {
            "command": "consume",
            "storage_id": "s1",
            "payload": {"item_id": "fuel_barrel", "qty": 1, "from": "tank_1"},
        }
    )
    assert missing_location["status"] == "error"


def test_find_returns_totals():
    engine = make_engine()
    engine.handle_command(
        {
            "command": "intake",
            "storage_id": "s1",
            "payload": {
                "items": [
                    {"item_id": "radio", "qty": 4, "location": None},
                    {"item_id": "radio", "qty": 6, "location": "tank_1"},
                ]
            },
        }
    )

    found = engine.handle_command({"command": "find", "storage_id": "s1", "payload": {"item_id": "radio"}})
    assert found["status"] == "ok"
    assert found["data"] == {
        "item_id": "radio",
        "total_qty": 10,
        "locations": {"null": 4, "tank_1": 6},
    }

    missing = engine.handle_command({"command": "find", "storage_id": "s1", "payload": {"item_id": "helmet"}})
    assert missing["status"] == "error"


def test_unknown_command_returns_error():
    engine = make_engine()
    response = engine.handle_command({"command": "unknown", "storage_id": "s1", "payload": {}})
    assert response["status"] == "error"
