import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT,
    finished_at   TEXT,
    ticker_count  INTEGER,
    ok_count      INTEGER,
    error_count   INTEGER,
    source        TEXT
);
CREATE TABLE IF NOT EXISTS flags (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT REFERENCES runs(run_id),
    ts        TEXT,
    ticker    TEXT,
    type      TEXT,
    severity  TEXT,
    score     REAL,
    meta      TEXT,
    source    TEXT
);
"""


def connect(db_path) -> sqlite3.Connection:
    """Open a SQLite connection, creating parent dirs for file-backed paths."""
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()
