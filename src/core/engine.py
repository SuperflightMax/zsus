"""Core engine stub with command validation."""

from __future__ import annotations

from typing import Any, Dict

REQUIRED_FIELDS = ("command", "payload")


def handle_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Validate structured command and return placeholder response."""

    if not isinstance(command, dict):
        raise ValueError("Command must be a dictionary.")

    for field in REQUIRED_FIELDS:
        if field not in command:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(command["command"], str) or not command["command"]:
        raise ValueError("Field 'command' must be a non-empty string.")

    if not isinstance(command["payload"], dict):
        raise ValueError("Field 'payload' must be a dictionary.")

    return {
        "status": "ok",
        "data": {
            "message": "Command validated",
            "command": command["command"],
        },
    }
