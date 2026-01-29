"""SQLite-based storage backend implementing the StorageBackend protocol."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional, Tuple


EPSILON = 1e-9


class SqliteStorageBackend:
    """SQLite backend with per-storage databases located under the storages root.

    Each storage uses its own database file placed in the storage directory:
        <root>/<storage_id>/<db_filename>

    The schema is fixed and applied per database:
        CREATE TABLE IF NOT EXISTS items (
          item_name  TEXT NOT NULL,
          location   TEXT,
          qty        REAL NOT NULL,
          unit       TEXT NOT NULL DEFAULT 'од',
          PRIMARY KEY (item_name, location)
        );
    """

    def __init__(self, storages_root: Path, db_filename: str = "storage.db"):
        self._storages_root = Path(storages_root)
        self._db_filename = db_filename
        self._storages_root.mkdir(parents=True, exist_ok=True)
        self._connections: Dict[str, sqlite3.Connection] = {}
        self._locks: Dict[str, threading.RLock] = {}

    # public API

    def ensure_storage(self, storage_id: str) -> None:
        with self._lock_for(storage_id):
            storage_dir = self._storages_root / storage_id
            storage_dir.mkdir(parents=True, exist_ok=True)
            # Touch the database by opening a connection and ensuring schema.
            self._get_conn(storage_id)

    def clear_storage(self, storage_id: str) -> None:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            conn.execute("DELETE FROM items")
            conn.commit()

    def delete_storage(self, storage_id: str) -> None:
        with self._lock_for(storage_id):
            # Close cached connection if present.
            conn = self._connections.pop(storage_id, None)
            if conn is not None:
                conn.close()

            db_path = self._db_path(storage_id)
            if db_path.exists():
                db_path.unlink()

    def get_storage_snapshot(self, storage_id: str) -> Dict[str, Dict[Optional[str], Dict[str, object]]]:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            snapshot: Dict[str, Dict[Optional[str], Dict[str, object]]] = {}
            cursor = conn.execute("SELECT item_name, location, qty, unit FROM items")
            for row in cursor.fetchall():
                item_name = row["item_name"]
                location = row["location"]
                qty = row["qty"]
                unit = row["unit"]
                snapshot.setdefault(item_name, {})[location] = {"qty": qty, "unit": unit}
            return snapshot

    def update_item_location(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
        delta: float,
        unit: Optional[str] = None,
    ) -> float:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            entry = self.location_entry(storage_id, item_id, location)
            current_qty = entry[0] if entry else 0.0
            current_unit = entry[1] if entry else None
            new_qty = current_qty + float(delta)
            unit_to_store = unit or current_unit

            if entry is not None:
                if unit_to_store:
                    conn.execute(
                        """
                        UPDATE items
                        SET qty = ?, unit = ?
                        WHERE item_name = ? AND location IS ?
                        """,
                        (new_qty, unit_to_store, item_id, location),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE items
                        SET qty = ?
                        WHERE item_name = ? AND location IS ?
                        """,
                        (new_qty, item_id, location),
                    )
            else:
                unit_to_store = unit_to_store or "од"
                conn.execute(
                    "INSERT INTO items (item_name, location, qty, unit) VALUES (?, ?, ?, ?)",
                    (item_id, location, new_qty, unit_to_store),
                )

            conn.commit()
            return new_qty

    def remove_location_if_empty(
        self,
        storage_id: str,
        item_id: str,
        location: Optional[str],
    ) -> None:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            cursor = conn.execute(
                "SELECT qty FROM items WHERE item_name = ? AND location IS ?",
                (item_id, location),
            )
            row = cursor.fetchone()
            if row and abs(float(row["qty"])) <= EPSILON:
                conn.execute(
                    "DELETE FROM items WHERE item_name = ? AND location IS ?",
                    (item_id, location),
                )
                conn.commit()

    def item_exists(self, storage_id: str, item_id: str) -> bool:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            cursor = conn.execute(
                "SELECT 1 FROM items WHERE item_name = ? LIMIT 1",
                (item_id,),
            )
            return cursor.fetchone() is not None

    def location_exists(self, storage_id: str, item_id: str, location: Optional[str]) -> bool:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            cursor = conn.execute(
                "SELECT 1 FROM items WHERE item_name = ? AND location IS ? LIMIT 1",
                (item_id, location),
            )
            return cursor.fetchone() is not None

    def location_quantity(self, storage_id: str, item_id: str, location: Optional[str]) -> float:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            cursor = conn.execute(
                "SELECT qty FROM items WHERE item_name = ? AND location IS ?",
                (item_id, location),
            )
            row = cursor.fetchone()
            return float(row["qty"]) if row else 0.0

    def location_entry(self, storage_id: str, item_id: str, location: Optional[str]) -> Optional[Tuple[float, str]]:
        with self._lock_for(storage_id):
            conn = self._get_conn(storage_id)
            cursor = conn.execute(
                "SELECT qty, unit FROM items WHERE item_name = ? AND location IS ?",
                (item_id, location),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return float(row["qty"]), str(row["unit"])

    # internal helpers

    def _db_path(self, storage_id: str) -> Path:
        return self._storages_root / storage_id / self._db_filename

    def _get_conn(self, storage_id: str) -> sqlite3.Connection:
        if storage_id in self._connections:
            return self._connections[storage_id]

        db_path = self._db_path(storage_id)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        self._connections[storage_id] = conn
        return conn

    @contextmanager
    def _lock_for(self, storage_id: str):
        lock = self._locks.setdefault(storage_id, threading.RLock())
        with lock:
            yield

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                item_name  TEXT NOT NULL,
                location   TEXT,
                qty        REAL NOT NULL,
                unit       TEXT NOT NULL DEFAULT 'од',
                PRIMARY KEY (item_name, location)
            )
            """
        )
        SqliteStorageBackend._ensure_unit_column(conn)
        conn.commit()

    @staticmethod
    def _ensure_unit_column(conn: sqlite3.Connection) -> None:
        cursor = conn.execute("PRAGMA table_info(items)")
        columns = {row[1] for row in cursor.fetchall()}
        if "unit" not in columns:
            conn.execute("ALTER TABLE items ADD COLUMN unit TEXT NOT NULL DEFAULT 'од'")
