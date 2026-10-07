# Radar Dilution Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone CLI dilution screen that scores a list of tickers' SEC-filing-based dilution risk into graded severities and persists results to SQLite.

**Architecture:** A new self-contained `tradingagents/radar/` package: an EDGAR collector (ticker→CIK + submissions fetch, injectable fetch for tests), a pure dilution scorer (5 severity tiers + trade-shaping hint), a SQLite store (`runs` + `flags`), and a CLI that wires them. No integration with the DD engine in this slice.

**Tech Stack:** Python 3, `requests` (HTTP), `sqlite3` (stdlib), `argparse` (stdlib), `pytest` (tests, with injected fakes — no live network).

**Spec:** `docs/superpowers/specs/2026-06-06-radar-dilution-screen-design.md`

---

## File Structure

- `tradingagents/radar/__init__.py` — package marker.
- `tradingagents/radar/config.py` — `RadarConfig` dataclass + `from_env()`.
- `tradingagents/radar/signals/__init__.py` — package marker.
- `tradingagents/radar/signals/dilution.py` — `DilutionFlag` dataclass, severity constants, `score_dilution()`.
- `tradingagents/radar/collectors/__init__.py` — package marker.
- `tradingagents/radar/collectors/edgar.py` — `Filing` dataclass, `EdgarClient`, dilution form constants.
- `tradingagents/radar/store/__init__.py` — package marker.
- `tradingagents/radar/store/db.py` — `connect()`, `migrate()`.
- `tradingagents/radar/store/models.py` — `start_run()`, `insert_flag()`, `finish_run()`.
- `tradingagents/radar/cli.py` — argparse CLI + table/JSON rendering.
- `tests/test_radar_config.py`, `tests/test_radar_dilution_scorer.py`, `tests/test_radar_edgar_client.py`, `tests/test_radar_store.py`, `tests/test_radar_cli.py`.

Dependency direction (no cycles): `cli` → {`config`, `collectors.edgar`, `signals.dilution`, `store`}; `store.models` → `signals.dilution` (for `DilutionFlag`); everything else is leaf.

---

## Task 1: Package skeleton + RadarConfig

**Files:**
- Create: `tradingagents/radar/__init__.py` (empty)
- Create: `tradingagents/radar/config.py`
- Test: `tests/test_radar_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_radar_config.py
import os
from pathlib import Path

import pytest

from tradingagents.radar.config import RadarConfig


@pytest.mark.unit
def test_defaults_use_tradingagents_home():
    cfg = RadarConfig()
    assert cfg.db_path == Path.home() / ".tradingagents" / "radar" / "radar.db"
    assert cfg.active_window_days == 90
    assert cfg.shelf_stale_days == 365


@pytest.mark.unit
def test_from_env_reads_user_agent(monkeypatch):
    monkeypatch.setenv("RADAR_SEC_USER_AGENT", "Acme Research contact@acme.com")
    cfg = RadarConfig.from_env()
    assert cfg.sec_user_agent == "Acme Research contact@acme.com"


@pytest.mark.unit
def test_from_env_user_agent_defaults_none(monkeypatch):
    monkeypatch.delenv("RADAR_SEC_USER_AGENT", raising=False)
    cfg = RadarConfig.from_env()
    assert cfg.sec_user_agent is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_radar_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.radar'`

- [ ] **Step 3: Create the package marker and config**

Create empty `tradingagents/radar/__init__.py`.

```python
# tradingagents/radar/config.py
import os
from dataclasses import dataclass, field
from pathlib import Path

_RADAR_HOME = Path.home() / ".tradingagents" / "radar"


@dataclass
class RadarConfig:
    """Configuration for the radar screens. Defaults reuse the ~/.tradingagents home."""

    db_path: Path = field(default_factory=lambda: _RADAR_HOME / "radar.db")
    edgar_cache_dir: Path = field(default_factory=lambda: _RADAR_HOME / "cache")
    sec_user_agent: str | None = None
    active_window_days: int = 90
    shelf_stale_days: int = 365

    @classmethod
    def from_env(cls) -> "RadarConfig":
        cfg = cls()
        ua = os.environ.get("RADAR_SEC_USER_AGENT")
        if ua:
            cfg.sec_user_agent = ua
        return cfg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_radar_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tradingagents/radar/__init__.py tradingagents/radar/config.py tests/test_radar_config.py
git commit -m "feat(radar): add package skeleton and RadarConfig"
```

---

## Task 2: SQLite store (db + models)

**Files:**
- Create: `tradingagents/radar/store/__init__.py` (empty)
- Create: `tradingagents/radar/store/db.py`
- Create: `tradingagents/radar/store/models.py`
- Create: `tradingagents/radar/signals/__init__.py` (empty)
- Create: `tradingagents/radar/signals/dilution.py` (minimal — just `DilutionFlag` for now; scoring added in Task 4)
- Test: `tests/test_radar_store.py`

> Note: `store.models` needs the `DilutionFlag` type, so this task creates `signals/dilution.py` containing only the dataclass + severity constants. Task 4 adds the `score_dilution()` function to the same file.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_radar_store.py
import json
import sqlite3
from datetime import date

import pytest

from tradingagents.radar.store.db import connect, migrate
from tradingagents.radar.store.models import finish_run, insert_flag, start_run
from tradingagents.radar.signals.dilution import DilutionFlag


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_radar_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.radar.store'`

- [ ] **Step 3: Create signals/dilution.py (dataclass only), db.py, models.py**

Create empty `tradingagents/radar/signals/__init__.py` and `tradingagents/radar/store/__init__.py`.

```python
# tradingagents/radar/signals/dilution.py
from dataclasses import dataclass, field
from datetime import date

SEVERITY_ACTIVE_ATM = "active_atm"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITY_NONE = "none"

SEVERITY_RANK = {
    SEVERITY_ACTIVE_ATM: 4,
    SEVERITY_HIGH: 3,
    SEVERITY_MEDIUM: 2,
    SEVERITY_LOW: 1,
    SEVERITY_NONE: 0,
}


@dataclass
class DilutionFlag:
    ticker: str
    severity: str
    score: float
    reasons: list[str] = field(default_factory=list)
    filings: list[dict] = field(default_factory=list)
    shaping_hint: str = ""
    as_of: date | None = None
```

```python
# tradingagents/radar/store/db.py
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
```

```python
# tradingagents/radar/store/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_radar_store.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tradingagents/radar/signals/ tradingagents/radar/store/ tests/test_radar_store.py
git commit -m "feat(radar): add SQLite store (runs + flags) and DilutionFlag"
```

---

## Task 3: EDGAR collector

**Files:**
- Create: `tradingagents/radar/collectors/__init__.py` (empty)
- Create: `tradingagents/radar/collectors/edgar.py`
- Test: `tests/test_radar_edgar_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_radar_edgar_client.py
import json

import pytest

from tradingagents.radar.config import RadarConfig
from tradingagents.radar.collectors.edgar import EdgarClient, Filing

_COMPANY_TICKERS = json.dumps({
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1062292, "ticker": "LFVN", "title": "LifeVantage Corp"},
})

_SUBMISSIONS = json.dumps({
    "filings": {
        "recent": {
            "form":                ["424B5", "S-3", "8-K", "10-Q"],
            "filingDate":          ["2026-05-20", "2025-01-10", "2026-05-01", "2026-04-01"],
            "primaryDocument":     ["d1.htm", "d2.htm", "d3.htm", "d4.htm"],
            "primaryDocDescription": ["Prospectus", "Shelf registration", "8-K", "10-Q"],
            "accessionNumber":     ["0001-26-1", "0001-25-2", "0001-26-3", "0001-26-4"],
        }
    }
})


def _fake_fetch(url, headers):
    if "company_tickers" in url:
        return _COMPANY_TICKERS
    if "submissions/CIK0001062292" in url:
        return _SUBMISSIONS
    raise AssertionError(f"unexpected url: {url}")


def _client():
    cfg = RadarConfig(sec_user_agent="Test test@example.com")
    return EdgarClient(cfg, fetch=_fake_fetch)


@pytest.mark.unit
def test_get_cik_zero_pads():
    assert _client().get_cik("LFVN") == "0001062292"


@pytest.mark.unit
def test_get_cik_unknown_returns_none():
    assert _client().get_cik("ZZZZ") is None


@pytest.mark.unit
def test_get_dilution_filings_filters_to_relevant_forms():
    filings = _client().get_dilution_filings("LFVN", lookback_days=3650)
    forms = sorted(f.form for f in filings)
    assert forms == ["424B5", "S-3"]  # 8-K and 10-Q dropped
    f424 = next(f for f in filings if f.form == "424B5")
    assert isinstance(f424, Filing)
    assert f424.filing_date.isoformat() == "2026-05-20"
    assert "1062292" in f424.url


@pytest.mark.unit
def test_get_dilution_filings_unknown_ticker_returns_empty():
    assert _client().get_dilution_filings("ZZZZ", lookback_days=3650) == []


@pytest.mark.unit
def test_missing_user_agent_raises():
    with pytest.raises(ValueError):
        EdgarClient(RadarConfig(sec_user_agent=None), fetch=_fake_fetch)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_radar_edgar_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tradingagents.radar.collectors'`

- [ ] **Step 3: Implement the collector**

Create empty `tradingagents/radar/collectors/__init__.py`.

```python
# tradingagents/radar/collectors/edgar.py
import json
from dataclasses import dataclass
from datetime import date

# Forms that signal dilution capacity or activity (heuristic, no doc parsing).
SHELF_FORMS = {"S-3", "S-3ASR", "S-1"}
PROSPECTUS_FORMS = {"424B5", "424B3", "424B2", "424B4"}
DILUTION_FORMS = SHELF_FORMS | PROSPECTUS_FORMS

_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"


@dataclass
class Filing:
    form: str
    filing_date: date
    description: str
    url: str


def _default_fetch(url: str, headers: dict) -> str:
    import requests
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


class EdgarClient:
    """Reads SEC EDGAR submission metadata. `fetch` is injectable for tests."""

    def __init__(self, config, fetch=None):
        if not config.sec_user_agent:
            raise ValueError(
                "SEC requires a User-Agent. Set RADAR_SEC_USER_AGENT "
                "(e.g. 'Your Name your@email.com')."
            )
        self.config = config
        self._fetch = fetch or _default_fetch
        self._cik_map = None

    def _headers(self) -> dict:
        return {"User-Agent": self.config.sec_user_agent}

    def _load_cik_map(self) -> dict:
        if self._cik_map is None:
            raw = json.loads(self._fetch(_COMPANY_TICKERS_URL, self._headers()))
            self._cik_map = {
                row["ticker"].upper(): f"{int(row['cik_str']):010d}"
                for row in raw.values()
            }
        return self._cik_map

    def get_cik(self, ticker: str) -> str | None:
        return self._load_cik_map().get(ticker.upper())

    def get_dilution_filings(self, ticker: str, lookback_days: int) -> list[Filing]:
        cik = self.get_cik(ticker)
        if cik is None:
            return []
        url = _SUBMISSIONS_URL.format(cik=cik)
        data = json.loads(self._fetch(url, self._headers()))
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        docs = recent.get("primaryDocument", [])
        descs = recent.get("primaryDocDescription", [])
        accs = recent.get("accessionNumber", [])

        today = date.today()
        out: list[Filing] = []
        for i, form in enumerate(forms):
            if form not in DILUTION_FORMS:
                continue
            try:
                fdate = date.fromisoformat(dates[i])
            except (ValueError, IndexError):
                continue
            if (today - fdate).days > lookback_days:
                continue
            acc_nodash = accs[i].replace("-", "") if i < len(accs) else ""
            doc = docs[i] if i < len(docs) else ""
            out.append(Filing(
                form=form,
                filing_date=fdate,
                description=descs[i] if i < len(descs) else "",
                url=_ARCHIVE_URL.format(cik=int(cik), acc=acc_nodash, doc=doc),
            ))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_radar_edgar_client.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add tradingagents/radar/collectors/ tests/test_radar_edgar_client.py
git commit -m "feat(radar): add EDGAR collector (CIK lookup + dilution filings)"
```

---

## Task 4: Dilution scorer

**Files:**
- Modify: `tradingagents/radar/signals/dilution.py` (add constants + `score_dilution()`)
- Test: `tests/test_radar_dilution_scorer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_radar_dilution_scorer.py
from datetime import date

import pytest

from tradingagents.radar.config import RadarConfig
from tradingagents.radar.collectors.edgar import Filing
from tradingagents.radar.signals.dilution import (
    SEVERITY_ACTIVE_ATM,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_NONE,
    score_dilution,
)

AS_OF = date(2026, 6, 1)
CFG = RadarConfig()  # active_window_days=90, shelf_stale_days=365


def _f(form, days_ago, desc=""):
    from datetime import timedelta
    return Filing(form=form, filing_date=AS_OF - timedelta(days=days_ago),
                  description=desc, url="http://x")


@pytest.mark.unit
def test_none_when_no_relevant_filings():
    flag = score_dilution([], AS_OF, CFG)
    assert flag.severity == SEVERITY_NONE
    assert flag.score == 0


@pytest.mark.unit
def test_active_atm_from_atm_prospectus_in_window():
    flag = score_dilution([_f("424B5", 10, "At-the-Market sales agreement prospectus")],
                          AS_OF, CFG)
    assert flag.severity == SEVERITY_ACTIVE_ATM
    assert flag.score == 90
    assert "short" in flag.shaping_hint.lower()


@pytest.mark.unit
def test_high_from_recent_424b5_takedown():
    flag = score_dilution([_f("424B5", 12, "Prospectus supplement")], AS_OF, CFG)
    assert flag.severity == SEVERITY_HIGH
    assert flag.score == 75


@pytest.mark.unit
def test_medium_from_effective_shelf():
    flag = score_dilution([_f("S-3", 120, "Shelf registration")], AS_OF, CFG)
    assert flag.severity == SEVERITY_MEDIUM
    assert flag.score == 50


@pytest.mark.unit
def test_low_from_stale_shelf_only():
    flag = score_dilution([_f("S-3", 400, "Shelf registration")], AS_OF, CFG)
    assert flag.severity == SEVERITY_LOW
    assert flag.score == 20


@pytest.mark.unit
def test_old_424b5_outside_window_is_not_high():
    # A 424B5 older than the active window should fall through to none here
    # (it is a takedown form, not a shelf, so no medium/low).
    flag = score_dilution([_f("424B5", 200, "Prospectus supplement")], AS_OF, CFG)
    assert flag.severity == SEVERITY_NONE


@pytest.mark.unit
def test_active_atm_takes_precedence_over_shelf():
    flag = score_dilution(
        [_f("S-3", 30, "Shelf"), _f("424B5", 5, "at-the-market offering")],
        AS_OF, CFG,
    )
    assert flag.severity == SEVERITY_ACTIVE_ATM
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_radar_dilution_scorer.py -v`
Expected: FAIL with `ImportError: cannot import name 'score_dilution'`

- [ ] **Step 3: Add the scorer to dilution.py**

Append to `tradingagents/radar/signals/dilution.py`:

```python
import re

from tradingagents.radar.collectors.edgar import (
    PROSPECTUS_FORMS,
    SHELF_FORMS,
    Filing,
)

_ATM_RE = re.compile(r"at-the-market|sales agreement|\batm\b", re.IGNORECASE)

_SCORE = {
    SEVERITY_ACTIVE_ATM: 90.0,
    SEVERITY_HIGH: 75.0,
    SEVERITY_MEDIUM: 50.0,
    SEVERITY_LOW: 20.0,
    SEVERITY_NONE: 0.0,
}

_SHAPING = {
    SEVERITY_ACTIVE_ATM: "shortest horizon, smallest size",
    SEVERITY_HIGH: "short-dated only, reduced size",
    SEVERITY_MEDIUM: "normal; note capacity overhang",
    SEVERITY_LOW: "minimal effect",
    SEVERITY_NONE: "none",
}


def _is_atm(filing: Filing) -> bool:
    return bool(_ATM_RE.search(filing.description or ""))


def _reason(filing: Filing, as_of) -> str:
    days = (as_of - filing.filing_date).days
    return f"{filing.form} filed {filing.filing_date.isoformat()} ({days}d ago)"


def _to_dict(filing: Filing) -> dict:
    return {"form": filing.form, "filing_date": filing.filing_date.isoformat(),
            "url": filing.url}


def score_dilution(filings: list, as_of, cfg) -> "DilutionFlag":
    """Classify dilution risk from filing types + recency. First match wins,
    highest severity to lowest."""
    active = [f for f in filings if (as_of - f.filing_date).days <= cfg.active_window_days]

    atm = [f for f in active if f.form in PROSPECTUS_FORMS and _is_atm(f)]
    if atm:
        return _build(SEVERITY_ACTIVE_ATM, atm, as_of)

    takedown = [f for f in active if f.form == "424B5"]
    if takedown:
        return _build(SEVERITY_HIGH, takedown, as_of)

    shelf = [f for f in filings if f.form in SHELF_FORMS]
    fresh_shelf = [f for f in shelf if (as_of - f.filing_date).days <= cfg.shelf_stale_days]
    if fresh_shelf:
        return _build(SEVERITY_MEDIUM, fresh_shelf, as_of)
    if shelf:
        return _build(SEVERITY_LOW, shelf, as_of)

    return _build(SEVERITY_NONE, [], as_of)


def _build(severity, filings, as_of) -> "DilutionFlag":
    return DilutionFlag(
        ticker="",  # set by caller
        severity=severity,
        score=_SCORE[severity],
        reasons=[_reason(f, as_of) for f in filings],
        filings=[_to_dict(f) for f in filings],
        shaping_hint=_SHAPING[severity],
        as_of=as_of,
    )
```

> Note: `score_dilution` returns a flag with `ticker=""`; the CLI sets `flag.ticker`
> after calling it (the scorer is ticker-agnostic — it only sees filings).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_radar_dilution_scorer.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add tradingagents/radar/signals/dilution.py tests/test_radar_dilution_scorer.py
git commit -m "feat(radar): add graded dilution scorer (5 severity tiers)"
```

---

## Task 5: CLI

**Files:**
- Create: `tradingagents/radar/cli.py`
- Test: `tests/test_radar_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_radar_cli.py
import sqlite3

import pytest

from tradingagents.radar import cli
from tradingagents.radar.collectors.edgar import Filing
from datetime import date, timedelta


class _FakeClient:
    """Stands in for EdgarClient. Raises for 'BOOM' to test error isolation."""

    def __init__(self, *args, **kwargs):
        pass

    def get_dilution_filings(self, ticker, lookback_days):
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
def test_requires_user_agent_handled(tmp_path, monkeypatch, capsys):
    # Real EdgarClient construction fails without a user agent -> non-zero exit.
    monkeypatch.delenv("RADAR_SEC_USER_AGENT", raising=False)
    exit_code = cli.main(["dilution", "AAPL", "--db", str(tmp_path / "r.db")])
    assert exit_code != 0
    assert "User-Agent" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_radar_cli.py -v`
Expected: FAIL with `ImportError: cannot import name 'cli'` (or `EdgarClient` attr missing)

- [ ] **Step 3: Implement the CLI**

```python
# tradingagents/radar/cli.py
import argparse
import json
import sys

from tradingagents.radar.config import RadarConfig
from tradingagents.radar.collectors.edgar import EdgarClient
from tradingagents.radar.signals.dilution import SEVERITY_RANK, score_dilution
from tradingagents.radar.store.db import connect, migrate
from tradingagents.radar.store.models import finish_run, insert_flag, start_run


def _parse_tickers(positional, file_path) -> list[str]:
    tickers = []
    if positional:
        tickers += [t.strip().upper() for t in positional.split(",") if t.strip()]
    if file_path:
        with open(file_path) as fh:
            tickers += [line.strip().upper() for line in fh if line.strip()]
    # de-dupe preserving order
    seen, out = set(), []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _render_table(flags) -> str:
    rows = sorted(flags, key=lambda f: (SEVERITY_RANK[f.severity], f.score),
                  reverse=True)
    lines = [f"{'TICKER':<8} {'SEVERITY':<12} {'SCORE':>6}  REASONS"]
    for f in rows:
        reasons = "; ".join(f.reasons) or "-"
        lines.append(f"{f.ticker:<8} {f.severity:<12} {f.score:>6.0f}  {reasons}")
    return "\n".join(lines)


def run_dilution(args) -> int:
    cfg = RadarConfig.from_env()
    if args.db:
        from pathlib import Path
        cfg.db_path = Path(args.db)

    tickers = _parse_tickers(args.tickers, args.file)
    if not tickers:
        print("No tickers provided.", file=sys.stderr)
        return 2

    try:
        client = EdgarClient(cfg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    lookback = max(cfg.active_window_days, cfg.shelf_stale_days)
    conn = connect(cfg.db_path)
    migrate(conn)
    run_id = start_run(conn, source="edgar", ticker_count=len(tickers))

    results, ok, errors = [], 0, 0
    for ticker in tickers:
        try:
            filings = client.get_dilution_filings(ticker, lookback_days=lookback)
            flag = score_dilution(filings, _today(), cfg)
            flag.ticker = ticker
            insert_flag(conn, run_id, flag)
            results.append(flag)
            ok += 1
        except Exception as exc:  # per-ticker isolation
            print(f"ERROR {ticker}: {exc}", file=sys.stderr)
            errors += 1

    finish_run(conn, run_id, ok_count=ok, error_count=errors)

    if args.json:
        print(json.dumps([_flag_dict(f) for f in results], indent=2))
    else:
        print(_render_table(results))
    return 0


def _today():
    from datetime import date
    return date.today()


def _flag_dict(f) -> dict:
    return {"ticker": f.ticker, "severity": f.severity, "score": f.score,
            "reasons": f.reasons, "filings": f.filings,
            "shaping_hint": f.shaping_hint,
            "as_of": f.as_of.isoformat() if f.as_of else None}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="radar")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dilution", help="Screen tickers for dilution risk via EDGAR")
    d.add_argument("tickers", nargs="?", default="",
                   help="comma-separated tickers, e.g. LFVN,SPCE,AAPL")
    d.add_argument("--file", help="path to a file with one ticker per line")
    d.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    d.add_argument("--db", help="override the SQLite DB path")
    args = parser.parse_args(argv)

    if args.command == "dilution":
        return run_dilution(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_radar_cli.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tradingagents/radar/cli.py tests/test_radar_cli.py
git commit -m "feat(radar): add dilution screen CLI with error isolation"
```

---

## Task 6: Full suite + live smoke check

**Files:** none (verification only)

- [ ] **Step 1: Run the full radar test suite**

Run: `pytest tests/test_radar_*.py -v`
Expected: PASS (all radar tests green)

- [ ] **Step 2: Confirm no regressions in the broader suite**

Run: `pytest -q`
Expected: no new failures introduced by the radar package (pre-existing failures, if any, unchanged).

- [ ] **Step 3: Live smoke test against real EDGAR (manual)**

```bash
export RADAR_SEC_USER_AGENT="Your Name your@email.com"
python -m tradingagents.radar.cli dilution AAPL,GME --db /tmp/radar_smoke.db
```
Expected: a printed table with one row per ticker; a large-cap like `AAPL` typically
`low`/`medium`/`none`. Verify rows persisted:

```bash
sqlite3 /tmp/radar_smoke.db "SELECT ticker, severity, score FROM flags;"
sqlite3 /tmp/radar_smoke.db "SELECT ok_count, error_count FROM runs;"
```
Expected: one flag row per ticker, one run row with matching counts.

- [ ] **Step 4: Commit (if any doc/fixups needed)**

```bash
git add -A
git commit -m "test(radar): verify dilution screen end-to-end" --allow-empty
```

---

## Self-Review

**Spec coverage:**
- Standalone slice (no DD integration) → Tasks 1–5, no `options_squeeze_analyst` changes. ✓
- EDGAR collector (CIK + submissions, injectable fetch, heuristic) → Task 3. ✓
- Graded 5-tier scorer + shaping hint → Task 4. ✓
- Store `flags` + `runs` + idempotent migration → Task 2. ✓
- CLI over ticker list, persist, table/JSON, per-ticker error isolation → Task 5. ✓
- Error handling (unknown ticker → none; network → per-ticker error; missing UA → startup error) → Tasks 3, 5. ✓
- Testing (table-driven scorer, fake-fetch client, :memory: store, mocked CLI) → Tasks 2–5. ✓
- Success criteria (live run + persistence) → Task 6. ✓

**Placeholder scan:** No TBD/TODO; every code step has full code. ✓

**Type consistency:** `DilutionFlag` fields (ticker, severity, score, reasons, filings, shaping_hint, as_of) consistent across Tasks 2, 4, 5. `Filing` fields (form, filing_date, description, url) consistent across Tasks 3, 4, 5. `score_dilution(filings, as_of, cfg)`, `EdgarClient(config, fetch)`, `start_run/insert_flag/finish_run` signatures consistent across tasks. `SEVERITY_*` constants and `SEVERITY_RANK` defined in Task 2/4, used in Task 5. ✓
