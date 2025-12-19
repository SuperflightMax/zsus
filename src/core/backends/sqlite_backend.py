"""SQLite-based storage backend implementing the StorageBackend protocol."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Optional


class SqliteStorageBackend:
    """SQLite backend with per-storage databases located under the storages root.

    Each storage uses its own database file placed in the storage directory:
        <root>/<storage_id>/<db_filename>

    The schema is fixed and applied per database:
        CREATE TABLE IF NOT EXISTS items (
          item_name  TEXT NOT NULL,
          location   TEXT,
          qty        INTEGER NOT NULL,
          PRIMARY KEY (item_name, location)
        );
    """

    def __init__(self, storages_root: Path, db_filename: str = "storage.db"):
        self._storages_root = Path(storages_root)
        self._db_filename = db_filename
        self._storages_root.mkdir(parents=True, exist_ok=True)
        self._connections: Dict[str, sqlite3.Connection] = {}

    # public API

    def ensure_storage(self, storage_id: str) -> None:
        storage_dir = self._storages_root / storage_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        # Touch the database by opening a connection and ensuring schema.
        self._get_conn(storage_id)

    def clear_storage(self, storage_id: str) -> None:
        conn = self._get_conn(storage_id)
        conn.execute("DELETE FROM items")
        conn.commit()

    def delete_storage(self, storage_id: str) -> None:
        # Close cached connection if present.
        conn = self._connections.pop(storage_id, None)
        if conn is not None:
            conn.close()

        db_path = self._db_path(storage_id)
        if db_path.exists():
            db_path.unlink()

    def get_storage_snapshot(self, storage_id: str) -> Dict[str, Dict[Optional[str], int]]:
        conn = self._get_conn(storage_id)
        snapshot: Dict[str, Dict[Optional[str], int]] = {}
        cursor = conn.execute("SELECT item_name, location, qty FROM items")
        for row in cursor.fetchall():
            item_name = row["item_name"]
            location = row["location"]
            qty = row["qty"]
            snapshot.setdefault(item_name, {})[location] = qty
        return snapshot

    def update_item_location(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
        delta: int,
    ) -> int:
        conn = self._get_conn(storage_id)
        current_qty = self.location_quantity(storage_id, item_id, location)
        new_qty = current_qty + delta

        if current_qty:
            conn.execute(
                """
                UPDATE items
                SET qty = ?
                WHERE item_name = ? AND location IS ?
                """,
                (new_qty, item_id, location),
            )
        else:
            conn.execute(
                "INSERT INTO items (item_name, location, qty) VALUES (?, ?, ?)",
                (item_id, location, new_qty),
            )

        conn.commit()
        return new_qty

    def remove_location_if_empty(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
    ) -> None:
        conn = self._get_conn(storage_id)
        cursor = conn.execute(
            "SELECT qty FROM items WHERE item_name = ? AND location IS ?",
            (item_id, location),
        )
        row = cursor.fetchone()
        if row and row["qty"] == 0:
            conn.execute(
                "DELETE FROM items WHERE item_name = ? AND location IS ?",
                (item_id, location),
            )
            conn.commit()

    def item_exists(self, storage_id: str, item_id: str) -> bool:
        conn = self._get_conn(storage_id)
        cursor = conn.execute(
            "SELECT 1 FROM items WHERE item_name = ? LIMIT 1",
            (item_id,),
        )
        return cursor.fetchone() is not None

    def location_exists(self, storage_id: str, item_id: str, location: Optional[str]) -> bool:
        conn = self._get_conn(storage_id)
        cursor = conn.execute(
            "SELECT 1 FROM items WHERE item_name = ? AND location IS ? LIMIT 1",
            (item_id, location),
        )
        return cursor.fetchone() is not None

    def location_quantity(self, storage_id: str, item_id: str, location: Optional[str]) -> int:
        conn = self._get_conn(storage_id)
        cursor = conn.execute(
            "SELECT qty FROM items WHERE item_name = ? AND location IS ?",
            (item_id, location),
        )
        row = cursor.fetchone()
        return int(row["qty"]) if row else 0

    # internal helpers

    def _db_path(self, storage_id: str) -> Path:
        return self._storages_root / storage_id / self._db_filename

    def _get_conn(self, storage_id: str) -> sqlite3.Connection:
        if storage_id in self._connections:
            return self._connections[storage_id]

        db_path = self._db_path(storage_id)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        self._connections[storage_id] = conn
        return conn

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                item_name  TEXT NOT NULL,
                location   TEXT,
                qty        INTEGER NOT NULL,
                PRIMARY KEY (item_name, location)
            )
            """
        )
        conn.commit()
