"""SQLite helpers for the trading game backend."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(config.DB_PATH)
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_ROOT / DB_PATH
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        # Migrate databases created before accounts existed: add the auth columns
        # if they are missing. The sessions table is handled by the schema above.
        existing = _column_names(conn, "players")
        for column in ("password_hash", "recovery_hash"):
            if column not in existing:
                conn.execute(f"ALTER TABLE players ADD COLUMN {column} TEXT")
