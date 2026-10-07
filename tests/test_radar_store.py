import json
from datetime import date

import pytest

from tradingagents.radar.store.db import connect, migrate
from tradingagents.radar.store.models import finish_run, insert_flag, start_run
from tradingagents.radar.signals.dilution import DilutionFlag


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    return c


@pytest.mark.unit
def test_migrate_is_idempotent(conn):
    migrate(conn)  # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"runs", "flags"} <= tables


@pytest.mark.unit
def test_run_and_flag_roundtrip(conn):
    run_id = start_run(conn, source="edgar", ticker_count=1)
    flag = DilutionFlag(
        ticker="LFVN",
        severity="high",
        score=75.0,
        reasons=["424B5 filed 2026-05-20 (12d ago)"],
        filings=[{"form": "424B5", "filing_date": "2026-05-20", "url": "http://x"}],
        shaping_hint="short-dated only, reduced size",
        as_of=date(2026, 6, 1),
    )
    insert_flag(conn, run_id, flag)
    finish_run(conn, run_id, ok_count=1, error_count=0)

    row = conn.execute("SELECT * FROM flags WHERE run_id = ?", (run_id,)).fetchone()
    assert row["ticker"] == "LFVN"
    assert row["severity"] == "high"
    assert row["type"] == "dilution"
    assert json.loads(row["meta"])["shaping_hint"] == "short-dated only, reduced size"

    run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    assert run["ok_count"] == 1 and run["error_count"] == 0
    assert run["finished_at"] is not None
