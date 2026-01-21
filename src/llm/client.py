"""LLM client interfaces and errors."""

from __future__ import annotations

from typing import Optional, Protocol


class LLMUnavailableError(RuntimeError):
    """Raised when LLM is unavailable or misconfigured."""


class LLMClient(Protocol):
    """Minimal LLM client contract used by adapters."""

    @property
    def model(self) -> Optional[str]:
        """LLM model identifier, if available."""

        raise NotImplementedError

    def generate(
        self,
        system_prompt: str,
        user_payload: str,
        response_format: Optional[dict] = None,
    ) -> str:
        """Generate a response from the LLM."""

        raise NotImplementedError
