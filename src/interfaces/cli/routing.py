"""Input routing helpers for CLI."""

from __future__ import annotations


def starts_json(text: str) -> bool:
    """Return True if the input should be treated as JSON."""
    return text.strip().startswith("{")


def classify_input(text: str) -> str:
    if text.startswith("+"):
        return "admin"
    if starts_json(text):
        return "json"
    return "user"


def truncate_data(value: str, max_chars: int) -> str:
    if max_chars == 0:
        return value
    if max_chars < 0:
        return ""
    return value if len(value) <= max_chars else value[:max_chars] + "..."
