"""SQLite storage for long-term device log retention."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("tuya_logs.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS device_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id       TEXT    NOT NULL,
    event_id        TEXT    NOT NULL,
    event_time      INTEGER NOT NULL,
    event_from      TEXT    NOT NULL DEFAULT '',
    code            TEXT    NOT NULL DEFAULT '',
    value           TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT '',
    raw_json        TEXT    NOT NULL,
    collected_at    INTEGER NOT NULL,
    UNIQUE(device_id, event_id, event_time)
);

CREATE INDEX IF NOT EXISTS idx_device_logs_device_time
    ON device_logs(device_id, event_time);

CREATE INDEX IF NOT EXISTS idx_device_logs_event_time
    ON device_logs(event_time);

CREATE TABLE IF NOT EXISTS collection_bookmarks (
    device_id       TEXT PRIMARY KEY,
    last_event_time INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      INTEGER NOT NULL,
    finished_at     INTEGER,
    devices_count   INTEGER NOT NULL DEFAULT 0,
    logs_collected  INTEGER NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'running'
);
"""


@dataclass
class LogRecord:
    """A single device log entry for storage."""

    device_id: str
    event_id: int
    event_time: int
    event_from: str
    code: str
    value: str
    status: str
    raw_json: str

    @classmethod
    def from_api(cls, device_id: str, entry: dict) -> LogRecord:
        """Create a LogRecord from a raw Tuya API log entry."""
        return cls(
            device_id=device_id,
            event_id=entry.get("event_id", 0),
            event_time=entry.get("event_time", 0),
            event_from=str(entry.get("event_from", "")),
            code=entry.get("code", ""),
            value=str(entry.get("value", "")),
            status=str(entry.get("status", "")),
            raw_json=json.dumps(entry),
        )


class LogStorage:
    """Manages a SQLite database for Tuya device log persistence."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the database and ensure schema exists."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> LogStorage:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not opened")
        return self._conn

    # -- Log insertion -------------------------------------------------------

    def insert_logs(self, records: list[LogRecord]) -> int:
        """Bulk insert log records, skipping duplicates. Returns new row count."""
        if not records:
            return 0
        now_ms = int(time.time() * 1000)
        cursor = self.conn.executemany(
            """
            INSERT OR IGNORE INTO device_logs
                (device_id, event_id, event_time, event_from,
                 code, value, status, raw_json, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.device_id,
                    r.event_id,
                    r.event_time,
                    r.event_from,
                    r.code,
                    r.value,
                    r.status,
                    r.raw_json,
                    now_ms,
                )
                for r in records
            ],
        )
        self.conn.commit()
        return cursor.rowcount

    # -- Bookmarks -----------------------------------------------------------

    def get_device_bookmark(self, device_id: str) -> int | None:
        """Return the last collected event_time for a device, or None."""
        row = self.conn.execute(
            "SELECT last_event_time FROM collection_bookmarks WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        return row[0] if row else None

    def set_device_bookmark(self, device_id: str, last_event_time: int) -> None:
        """Upsert the bookmark for a device."""
        now_ms = int(time.time() * 1000)
        self.conn.execute(
            """
            INSERT INTO collection_bookmarks (device_id, last_event_time, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                last_event_time = excluded.last_event_time,
                updated_at = excluded.updated_at
            """,
            (device_id, last_event_time, now_ms),
        )
        self.conn.commit()

    def get_all_bookmarks(self) -> list[tuple[str, int]]:
        """Return all (device_id, last_event_time) bookmark pairs."""
        rows = self.conn.execute(
            "SELECT device_id, last_event_time FROM collection_bookmarks "
            "ORDER BY device_id"
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    # -- Run tracking --------------------------------------------------------

    def record_run_start(self) -> int:
        """Insert a new collection run and return its ID."""
        now_ms = int(time.time() * 1000)
        cursor = self.conn.execute(
            "INSERT INTO collection_runs (started_at) VALUES (?)",
            (now_ms,),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def record_run_end(
        self,
        run_id: int,
        *,
        devices: int,
        logs: int,
        status: str = "completed",
    ) -> None:
        """Update a run record with final counts and status."""
        now_ms = int(time.time() * 1000)
        self.conn.execute(
            """
            UPDATE collection_runs
            SET finished_at = ?, devices_count = ?, logs_collected = ?, status = ?
            WHERE id = ?
            """,
            (now_ms, devices, logs, status, run_id),
        )
        self.conn.commit()

    # -- Query helpers -------------------------------------------------------

    def query_logs(
        self,
        *,
        device_id: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query device_logs with optional filters.

        Returns ``(rows_as_dicts, total_count)``.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if device_id:
            clauses.append("device_id = ?")
            params.append(device_id)
        if start_time is not None:
            clauses.append("event_time >= ?")
            params.append(start_time)
        if end_time is not None:
            clauses.append("event_time <= ?")
            params.append(end_time)
        if code:
            clauses.append("code = ?")
            params.append(code)

        where = " AND ".join(clauses) if clauses else "1=1"

        total: int = self.conn.execute(
            f"SELECT COUNT(*) FROM device_logs WHERE {where}",
            params,
        ).fetchone()[0]

        cols = (
            "device_id, event_id, event_time, event_from, "
            "code, value, status"
        )
        rows = self.conn.execute(
            f"SELECT {cols} FROM device_logs "
            f"WHERE {where} ORDER BY event_time DESC "
            f"LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()

        columns = [
            "device_id", "event_id", "event_time",
            "event_from", "code", "value", "status",
        ]
        return [dict(zip(columns, r)) for r in rows], total

    def get_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent collection runs."""
        rows = self.conn.execute(
            "SELECT id, started_at, finished_at, devices_count, "
            "logs_collected, status FROM collection_runs "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        columns = [
            "id", "started_at", "finished_at",
            "devices_count", "logs_collected", "status",
        ]
        return [dict(zip(columns, r)) for r in rows]

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Return summary statistics about the database."""
        total_logs = self.conn.execute(
            "SELECT COUNT(*) FROM device_logs"
        ).fetchone()[0]
        total_devices = self.conn.execute(
            "SELECT COUNT(DISTINCT device_id) FROM device_logs"
        ).fetchone()[0]
        total_runs = self.conn.execute(
            "SELECT COUNT(*) FROM collection_runs"
        ).fetchone()[0]
        return {
            "total_logs": total_logs,
            "total_devices": total_devices,
            "total_runs": total_runs,
        }
