"""Shared operation result object for core and interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class OperationResult:
    """Unified result returned by commands and interfaces."""

    ok: bool
    user_text: Optional[str] = None
    data: Any = None
    system_log: List[str] = field(default_factory=list)

    @classmethod
    def success(
        cls,
        *,
        user_text: Optional[str] = None,
        data: Any = None,
        system_log: Optional[List[str]] = None,
    ) -> "OperationResult":
        return cls(ok=True, user_text=user_text, data=data, system_log=system_log or [])

    @classmethod
    def failure(
        cls,
        *,
        user_text: str,
        data: Any = None,
        system_log: Optional[List[str]] = None,
    ) -> "OperationResult":
        return cls(ok=False, user_text=user_text, data=data, system_log=system_log or [])

    def with_prepended_logs(self, logs: List[str]) -> "OperationResult":
        """Return a copy with additional system logs prepended."""

        return OperationResult(
            ok=self.ok,
            user_text=self.user_text,
            data=self.data,
            system_log=list(logs) + list(self.system_log),
        )

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "user_text": self.user_text,
            "data": self.data,
            "system_log": list(self.system_log),
        }

