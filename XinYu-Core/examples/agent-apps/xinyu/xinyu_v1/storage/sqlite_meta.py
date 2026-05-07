"""SQLite metadata store for v1 runtime bookkeeping."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


@dataclass(slots=True)
class SQLiteMetaStore:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        conn.executescript(SCHEMA)
        return conn

    def set_json(self, key: str, value: dict[str, Any], *, updated_at: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kv(key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False, sort_keys=True), updated_at),
            )

    def get_json(self, key: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        if not row:
            return {}
        try:
            value = json.loads(str(row[0]))
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    def append_audit(self, event_type: str, payload: dict[str, Any], *, created_at: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit(event_type, payload, created_at) VALUES (?, ?, ?)",
                (event_type, json.dumps(payload, ensure_ascii=False, sort_keys=True), created_at),
            )

