"""LLM client interfaces and errors."""

from __future__ import annotations

from typing import Protocol


class LLMUnavailableError(RuntimeError):
    """Raised when LLM is unavailable or misconfigured."""


class LLMClient(Protocol):
    """Minimal LLM client contract used by adapters."""

    def generate(self, system_prompt: str, user_payload: str) -> str:
        """Generate a response from the LLM."""

        raise NotImplementedError
