"""Backend factory that selects storage backend based on configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from ..core.engine import InMemoryStorageBackend, StorageBackend
from ..core.backends import SqliteStorageBackend


def create_backend(config: Dict[str, Any]) -> Tuple[str, StorageBackend]:
    """Create a storage backend based on configuration.

    Supported backends:
    - memory (default)
    - sqlite (per-storage DB files inside storages root)
    """

    storage_config = config.get("storage", {}) if isinstance(config, dict) else {}
    backend_name = (storage_config.get("backend") or "memory").lower()

    if backend_name == "sqlite":
        storages_root = _storages_root(config)
        db_filename = storage_config.get("sqlite_filename") or "storage.db"
        backend = SqliteStorageBackend(storages_root, db_filename=db_filename)
    else:
        backend_name = "memory"
        backend = InMemoryStorageBackend()

    return backend_name, backend


def _storages_root(config: Dict[str, Any]) -> Path:
    storages_config = config.get("storages", {}) if isinstance(config, dict) else {}
    return Path(storages_config.get("root_path", "./storages"))
