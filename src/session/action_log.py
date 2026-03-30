"""Unified action audit log helpers for executed core commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.result import OperationResult


def normalize_optional_str(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def normalize_source(value: Optional[str], *, default: str) -> str:
    normalized = normalize_optional_str(value)
    return normalized or default


def append_action_log(
    command_payload: Dict[str, Any],
    response: OperationResult,
    *,
    client_id: Optional[str] = None,
    operator_id: Optional[str] = None,
    source: Optional[str] = None,
    source_default: str = "http",
) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "actions.log"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "storage_id": command_payload.get("storage_id"),
        "client_id": normalize_optional_str(client_id),
        "operator_id": normalize_optional_str(operator_id),
        "source": normalize_source(source, default=source_default),
        "command": command_payload.get("command"),
        "payload": command_payload.get("payload"),
        "core_ok": response.ok,
    }
    if not response.ok:
        entry["core_error"] = response.user_text

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
