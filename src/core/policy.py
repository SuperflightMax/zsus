"""Policy and defaults application layer for commands."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .defaults import DEFAULT_LOCATION, DEFAULT_QTY
from .result import OperationResult


def apply_policy(command: Dict[str, Any]) -> OperationResult:
    """Normalize command, apply defaults, and perform light validation."""

    if not isinstance(command, dict):
        return OperationResult.failure(
            user_text="Команда має бути словником.",
            system_log=["Invalid command type."],
        )

    name = command.get("command")
    if not isinstance(name, str):
        return OperationResult.failure(
            user_text="Команда відсутня або некоректна.",
            system_log=["Missing or invalid 'command' field."],
        )

    normalized = dict(command)
    payload = normalized.get("payload") or {}
    if not isinstance(payload, dict):
        return OperationResult.failure(
            user_text="Payload має бути об'єктом.",
            system_log=["Payload is not a dict."],
        )

    normalized["payload"] = payload

    if name in {"intake", "move", "consume", "list", "find"}:
        storage_id = normalized.get("storage_id")
        if not isinstance(storage_id, str) or not storage_id:
            return OperationResult.failure(
                user_text="Не вказаний склад (storage_id).",
                system_log=["storage_id is required for this command."],
            )

    if name == "intake":
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            return OperationResult.failure(
                user_text="Потрібен непорожній список items.",
                system_log=["items must be non-empty list for intake."],
            )
        normalized_items = []
        for entry in items:
            if not isinstance(entry, dict):
                return OperationResult.failure(
                    user_text="Кожний елемент items має бути об'єктом.",
                    system_log=["Invalid item entry in intake."],
                )
            item_id = entry.get("item_id")
            if not isinstance(item_id, str) or not item_id:
                return OperationResult.failure(
                    user_text="Кожний item_id обов'язковий.",
                    system_log=["item_id missing in intake item."],
                )
            normalized_items.append(
                {
                    "item_id": item_id,
                    "qty": _ensure_int(entry.get("qty"), DEFAULT_QTY),
                    "location": entry.get("location", DEFAULT_LOCATION),
                }
            )
        normalized["payload"]["items"] = normalized_items

    if name in {"move", "consume"}:
        item_id = payload.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            return OperationResult.failure(
                user_text="item_id обов'язковий.",
                system_log=["item_id missing for move/consume."],
            )
        payload["item_id"] = item_id
        payload["qty"] = _ensure_int(payload.get("qty"), DEFAULT_QTY)
        payload["from"] = payload.get("from", DEFAULT_LOCATION)
        if name == "move":
            payload["to"] = payload.get("to", DEFAULT_LOCATION)

    if name == "find":
        item_id = payload.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            return OperationResult.failure(
                user_text="item_id обов'язковий для пошуку.",
                system_log=["item_id missing for find."],
            )

    return OperationResult.success(data=normalized, system_log=["Policy applied."])


def _ensure_int(value: Optional[Any], default: int) -> int:
    return value if isinstance(value, int) else default

