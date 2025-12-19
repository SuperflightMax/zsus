"""Core engine stub with command validation."""

from __future__ import annotations

from typing import Any, Dict


def handle_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and forward structured commands.

    The core accepts only structured JSON commands. At this stage the function
    performs minimal validation to confirm that the input is a dictionary and
    contains the required ``command`` field, then returns a stub response.
    """

    if not isinstance(command, dict):
        raise ValueError("Command must be a dictionary.")

    if "command" not in command:
        raise ValueError("Missing required field: command")

    return {
        "status": "ok",
        "data": {},
    }
