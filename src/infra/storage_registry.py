"""Storage registry utilities for managing storage roots."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List


class StorageRegistry:
    """Lightweight registry that manages storage directories."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config or {}
        storages_config = self._config.get("storages", {})
        root_path = storages_config.get("root_path", "./storages")
        self._root_path = Path(root_path)
        self._root_path.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def root_path(self) -> Path:
        return self._root_path

    def list_storages(self) -> List[str]:
        """Return a sorted list of existing storages."""
        if not self._root_path.exists():
            return []

        return sorted(
            entry.name
            for entry in self._root_path.iterdir()
            if entry.is_dir()
        )

    def storage_exists(self, storage_id: str) -> bool:
        return (self._root_path / storage_id).is_dir()

    def create_storage(self, storage_id: str) -> bool:
        """Create a storage directory. Returns True if created, False if it already exists."""
        storage_path = self._root_path / storage_id
        if storage_path.exists():
            return False

        storage_path.mkdir(parents=True, exist_ok=False)
        return True

    def delete_storage(self, storage_id: str) -> bool:
        """Delete a storage directory. Returns True if deleted, False if missing."""
        storage_path = self._root_path / storage_id
        if not storage_path.exists():
            return False

        shutil.rmtree(storage_path)
        return True
