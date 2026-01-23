"""Core engine with in-memory backend and basic commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from .result import OperationResult
from .policy import apply_policy


class StorageBackend(Protocol):
    """Abstract backend interface for storage state."""

    def ensure_storage(self, storage_id: str) -> None:
        ...

    def clear_storage(self, storage_id: str) -> None:
        ...

    def delete_storage(self, storage_id: str) -> None:
        ...

    def get_storage_snapshot(self, storage_id: str) -> Dict[str, Dict[Optional[str], int]]:
        ...

    def update_item_location(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
        delta: int,
    ) -> int:
        ...

    def remove_location_if_empty(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
    ) -> None:
        ...

    def item_exists(self, storage_id: str, item_id: str) -> bool:
        ...

    def location_exists(self, storage_id: str, item_id: str, location: Optional[str]) -> bool:
        ...

    def location_quantity(self, storage_id: str, item_id: str, location: Optional[str]) -> int:
        ...


@dataclass
class InMemoryStorageBackend:
    """Simple in-memory backend for development and testing."""

    storages: Dict[str, Dict[str, Dict[Optional[str], int]]] = field(default_factory=dict)

    def ensure_storage(self, storage_id: str) -> None:
        self.storages.setdefault(storage_id, {})

    def clear_storage(self, storage_id: str) -> None:
        self.storages[storage_id] = {}

    def delete_storage(self, storage_id: str) -> None:
        self.storages.pop(storage_id, None)

    def get_storage_snapshot(self, storage_id: str) -> Dict[str, Dict[Optional[str], int]]:
        return {item: dict(locations) for item, locations in self.storages.get(storage_id, {}).items()}

    def update_item_location(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
        delta: int,
    ) -> int:
        self.ensure_storage(storage_id)
        item_locations = self.storages[storage_id].setdefault(item_id, {})
        new_qty = item_locations.get(location, 0) + delta
        item_locations[location] = new_qty
        return new_qty

    def remove_location_if_empty(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
    ) -> None:
        item_locations = self.storages.get(storage_id, {}).get(item_id)
        if not item_locations:
            return
        if item_locations.get(location) == 0:
            item_locations.pop(location, None)
        if not item_locations:
            self.storages.get(storage_id, {}).pop(item_id, None)

    def item_exists(self, storage_id: str, item_id: str) -> bool:
        return item_id in self.storages.get(storage_id, {})

    def location_exists(self, storage_id: str, item_id: str, location: Optional[str]) -> bool:
        return location in self.storages.get(storage_id, {}).get(item_id, {})

    def location_quantity(self, storage_id: str, item_id: str, location: Optional[str]) -> int:
        return self.storages.get(storage_id, {}).get(item_id, {}).get(location, 0)


class CoreEngine:
    """Command dispatcher working against a storage backend."""

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    def handle_command(self, command: Dict[str, Any]) -> OperationResult:
        policy_result = apply_policy(command)
        if not policy_result.ok:
            return policy_result

        normalized = policy_result.data or {}
        name = normalized.get("command")
        payload = normalized.get("payload") or {}
        storage_id = normalized.get("storage_id")

        handlers = {
            "create_storage": self._create_storage,
            "delete_storage": self._delete_storage,
            "intake": self._intake,
            "move": self._move,
            "consume": self._consume,
            "list": self._list_items,
            "find": self._find_item,
        }

        handler = handlers.get(name)
        if handler is None:
            return self._error("Невідома команда.")

        try:
            return handler(storage_id=storage_id, payload=payload)
        except ValueError as exc:
            return self._error(str(exc))

    # command handlers

    def _create_storage(self, storage_id: Optional[str], payload: Dict[str, Any]) -> OperationResult:
        target_id = payload.get("storage_id") or storage_id
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("storage_id є обов'язковим.")
        self.backend.ensure_storage(target_id)
        return OperationResult.success(data={"storage_id": target_id})

    def _delete_storage(self, storage_id: Optional[str], payload: Dict[str, Any]) -> OperationResult:
        target_id = payload.get("storage_id") or storage_id
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("storage_id є обов'язковим.")
        self.backend.delete_storage(target_id)
        return OperationResult.success(data={"storage_id": target_id})

    def _intake(self, storage_id: str, payload: Dict[str, Any]) -> OperationResult:
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("Список items має бути непорожнім.")
        self.backend.ensure_storage(storage_id)
        for entry in items:
            item_id = entry.get("item_id")
            qty = entry.get("qty")
            location = entry.get("location")
            self._validate_item_id(item_id)
            self._validate_qty(qty)
            self.backend.update_item_location(storage_id, item_id, location, qty)
        return OperationResult.success(data={})

    def _move(self, storage_id: str, payload: Dict[str, Any]) -> OperationResult:
        item_id = payload.get("item_id")
        qty = payload.get("qty")
        from_location = payload.get("from")
        to_location = payload.get("to")

        self._validate_item_id(item_id)
        self._validate_qty(qty)
        self._ensure_item_location_exists(storage_id, item_id, from_location)
        available = self.backend.location_quantity(storage_id, item_id, from_location)
        if available < qty:
            raise ValueError("Недостатньо предметів у вихідній локації.")

        self.backend.update_item_location(storage_id, item_id, from_location, -qty)
        self.backend.remove_location_if_empty(storage_id, item_id, from_location)
        self.backend.update_item_location(storage_id, item_id, to_location, qty)
        return OperationResult.success(data={})

    def _consume(self, storage_id: str, payload: Dict[str, Any]) -> OperationResult:
        item_id = payload.get("item_id")
        qty = payload.get("qty")
        from_location = payload.get("from")

        self._validate_item_id(item_id)
        self._validate_qty(qty)
        self._ensure_item_location_exists(storage_id, item_id, from_location)
        available = self.backend.location_quantity(storage_id, item_id, from_location)
        if available < qty:
            raise ValueError("Недостатньо предметів у локації.")

        self.backend.update_item_location(storage_id, item_id, from_location, -qty)
        self.backend.remove_location_if_empty(storage_id, item_id, from_location)
        return OperationResult.success(data={})

    def _list_items(self, storage_id: str, payload: Dict[str, Any]) -> OperationResult:
        snapshot = self.backend.get_storage_snapshot(storage_id)
        return OperationResult.success(data=self._serialize_snapshot(snapshot))

    def _find_item(self, storage_id: str, payload: Dict[str, Any]) -> OperationResult:
        item_id = payload.get("item_id")
        self._validate_item_id(item_id)
        snapshot = self.backend.get_storage_snapshot(storage_id)
        locations = snapshot.get(item_id)
        if not locations:
            raise ValueError("Предмет не знайдено.")

        total_qty = sum(locations.values())
        return OperationResult.success(
            data={
                "item_id": item_id,
                "total_qty": total_qty,
                "locations": {self._location_key(k): v for k, v in locations.items()},
            }
        )

    # helpers

    def _ensure_item_location_exists(self, storage_id: str, item_id: str, location: Optional[str]) -> None:
        if not self.backend.item_exists(storage_id, item_id):
            raise ValueError("Предмет не знайдено.")
        if not self.backend.location_exists(storage_id, item_id, location):
            raise ValueError("Локацію не знайдено.")

    @staticmethod
    def _location_key(location: Optional[str]) -> str:
        return "null" if location is None else str(location)

    @staticmethod
    def _serialize_snapshot(snapshot: Dict[str, Dict[Optional[str], int]]) -> Dict[str, Dict[str, int]]:
        return {item: {CoreEngine._location_key(loc): qty for loc, qty in locations.items()} for item, locations in snapshot.items()}

    @staticmethod
    def _validate_item_id(item_id: Any) -> None:
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("item_id є обов'язковим")

    @staticmethod
    def _validate_qty(qty: Any) -> None:
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty має бути > 0")

    @staticmethod
    def _error(message: str) -> OperationResult:
        return OperationResult.failure(user_text=message, data=None, system_log=[message])


_default_engine = CoreEngine(backend=InMemoryStorageBackend())


def set_default_backend(backend: StorageBackend) -> None:
    """Replace the module-level engine backend (used by CLI and interfaces)."""

    global _default_engine
    _default_engine = CoreEngine(backend=backend)


def handle_command(command: Dict[str, Any]) -> OperationResult:
    """Module-level entry point used by interfaces."""

    return _default_engine.handle_command(command)
