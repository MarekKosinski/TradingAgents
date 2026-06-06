import json
import sqlite3
import uuid
from datetime import datetime, timezone

from tradingagents.radar.signals.dilution import DilutionFlag


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(conn: sqlite3.Connection, source: str, ticker_count: int) -> str:
    run_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO runs (run_id, started_at, finished_at, ticker_count, "
        "ok_count, error_count, source) VALUES (?, ?, NULL, ?, 0, 0, ?)",
        (run_id, _now_iso(), ticker_count, source),
    )
    conn.commit()
    return run_id


def insert_flag(conn: sqlite3.Connection, run_id: str, flag: DilutionFlag,
                source: str = "edgar") -> None:
    meta = json.dumps({
        "reasons": flag.reasons,
        "filings": flag.filings,
        "shaping_hint": flag.shaping_hint,
    })
    conn.execute(
        "INSERT INTO flags (run_id, ts, ticker, type, severity, score, meta, source) "
        "VALUES (?, ?, ?, 'dilution', ?, ?, ?, ?)",
        (run_id, _now_iso(), flag.ticker, flag.severity, flag.score, meta, source),
    )
    conn.commit()


def finish_run(conn: sqlite3.Connection, run_id: str, ok_count: int,
               error_count: int) -> None:
    conn.execute(
        "UPDATE runs SET finished_at = ?, ok_count = ?, error_count = ? "
        "WHERE run_id = ?",
        (_now_iso(), ok_count, error_count, run_id),
    )
    conn.commit()
