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
