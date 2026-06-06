import sqlite3
from datetime import date, timedelta

import pytest

from tradingagents.radar import cli
from tradingagents.radar.collectors.edgar import Filing


class _FakeClient:
    """Stands in for EdgarClient. Raises for 'BOOM' to test error isolation."""

    def __init__(self, *args, **kwargs):
        pass

    def get_dilution_filings(self, ticker, lookback_days, as_of=None):
        if ticker == "BOOM":
            raise RuntimeError("network down")
        if ticker == "DILUTE":
            return [Filing("424B5", date.today() - timedelta(days=5),
                           "at-the-market sales agreement", "http://x")]
        return []  # clean "none"


@pytest.mark.unit
def test_run_screen_persists_and_isolates_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "EdgarClient", _FakeClient)
    db = tmp_path / "radar.db"
    exit_code = cli.main([
        "dilution", "DILUTE,CLEAN,BOOM", "--db", str(db),
    ])
    assert exit_code == 0

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    flags = {r["ticker"]: r["severity"] for r in conn.execute("SELECT * FROM flags")}
    assert flags["DILUTE"] == "active_atm"
    assert flags["CLEAN"] == "none"
    assert "BOOM" not in flags  # errored ticker not flagged

    run = conn.execute("SELECT * FROM runs").fetchone()
    assert run["ok_count"] == 2 and run["error_count"] == 1


@pytest.mark.unit
def test_all_tickers_failing_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "EdgarClient", _FakeClient)
    db = tmp_path / "radar.db"
    exit_code = cli.main(["dilution", "BOOM", "--db", str(db)])
    assert exit_code == 1

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    run = conn.execute("SELECT * FROM runs").fetchone()
    assert run["ok_count"] == 0 and run["error_count"] == 1


@pytest.mark.unit
def test_requires_user_agent_handled(tmp_path, monkeypatch, capsys):
    # Real EdgarClient construction fails without a user agent -> non-zero exit.
    monkeypatch.delenv("RADAR_SEC_USER_AGENT", raising=False)
    exit_code = cli.main(["dilution", "AAPL", "--db", str(tmp_path / "r.db")])
    assert exit_code != 0
    assert "User-Agent" in capsys.readouterr().err
