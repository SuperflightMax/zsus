"""Storage registry stub for future storage management."""

from __future__ import annotations

from typing import Any, Dict


class StorageRegistry:
    """Placeholder registry implementation."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

