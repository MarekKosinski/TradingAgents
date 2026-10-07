# Radar — Dilution Screen (first slice) · Design

> Date: 2026-06-06
> Status: **approved design**, ready for implementation planning.
> Context: first implementation slice of the Opportunity Radar (see
> [`docs/RADAR_STRATEGY.md`](../../RADAR_STRATEGY.md), §7 build order step 1 and §9
> architecture). This slice stands up the `tradingagents/radar/` package foundation.

## 1. Goal & scope

Build a **standalone** dilution screen: given a list of tickers, fetch each
company's recent SEC filings, score its dilution risk into a graded severity, and
persist the results — runnable from a CLI, **independent of the deep-DD engine** (no
`options_squeeze_analyst` integration in this slice).

This delivers the doc's highest edge-per-effort piece (free data, high trap-avoidance,
"flag, don't kill") and lays the `radar/` package + SQLite store that later slices
(social collector, theme detector, DD integration) build on.

### In scope
- `tradingagents/radar/` package skeleton.
- EDGAR collector: ticker→CIK lookup + submissions-API fetch (heuristic, no full-text
  document parsing).
- Graded dilution scorer (pure function, 5 severity tiers) carrying a trade-shaping
  hint.
- SQLite store with `flags` + `runs` tables and idempotent migration.
- CLI to run the screen over a ticker list, persist results, and render a table / JSON.

### Out of scope (deferred to later slices)
- Full-text filing parsing (ATM program size, $ remaining, dilution % of float).
- Integration into `options_squeeze_analyst` / the DD engine.
- Form 4 insider screen, social collector, other signals, other store tables
  (`snapshots`, `signals`, `candidates`, `alerts`, `outcomes`).
- The `route_to_vendor` dataflow adapter (a future slice can wrap the collector).

## 2. Decisions (locked during brainstorming)

| # | Decision | Choice |
|---|---|---|
| 1 | Slice boundary | Standalone radar slice (signal module + store + CLI), no DD integration |
| 2 | Detection depth | Filing-type + recency **heuristic** from the EDGAR submissions index; no document downloads. Scoring kept isolated so a parser can replace it later. |
| 3 | Store scope | `flags` + `runs` tables + `db.py` scaffolding |
| 4 | EDGAR access location | **A** — self-contained in `radar/collectors/edgar.py` (not behind `route_to_vendor`); written cleanly so a future `dataflows` adapter can wrap it |

## 3. Module layout

```
tradingagents/radar/
  __init__.py
  config.py            # RadarConfig: db_path, SEC user_agent, recency windows, thresholds
  collectors/
    __init__.py
    edgar.py           # EdgarClient — CIK lookup (cached) + submissions fetch
  signals/
    __init__.py
    dilution.py        # score_dilution(filings, as_of, cfg) -> DilutionFlag  + thresholds
  store/
    __init__.py
    db.py              # connect(path) + migrate()  (idempotent CREATE IF NOT EXISTS)
    models.py          # DilutionFlag dataclass, insert_flag, start_run, finish_run
  cli.py               # `python -m tradingagents.radar.cli dilution LFVN,SPCE,...`
```

Four units, each with one responsibility: `edgar.py` (IO), `dilution.py` (pure logic),
`store/` (persistence), `cli.py` (wiring). The pure scorer holds the real logic and is
testable in isolation.

## 4. EDGAR collector — `collectors/edgar.py`

`EdgarClient` constructed with an **injected fetch callable** (default: a thin
`requests`/`urllib` wrapper) so tests never hit the network.

- `get_cik(ticker) -> str | None` — downloads SEC `company_tickers.json` once, caches
  it on disk under the radar home, maps `ticker → zero-padded 10-digit CIK`. Returns
  `None` if the ticker is unknown.
- `get_dilution_filings(ticker, lookback_days) -> list[Filing]` — calls
  `https://data.sec.gov/submissions/CIK##########.json`, normalizes the recent-filings
  arrays into `Filing{ form, filing_date, description, url }`, filtered to
  dilution-relevant forms (see §5).
- Sends the SEC-required `User-Agent` header (from `RadarConfig`, overridable via env);
  throttles requests to ≤ 10 req/s.

`Filing` is a small dataclass (or typed dict) — the scorer's input contract.

## 5. Dilution scoring — `signals/dilution.py` (the heart)

Pure function:

```python
def score_dilution(filings: list[Filing], as_of: date, cfg: RadarConfig) -> DilutionFlag
```

Relevant form types: `424B5`, `424B3`/`424B*` (prospectus supplements / takedowns),
`S-3`, `S-3ASR` (shelf registrations), `S-1` (registration), and `8-K` carrying an
ATM/sales-agreement reference. ATM detection keys off the keywords
`"at-the-market"`, `"atm"`, `"sales agreement"` in a filing description.

Severity tiers (first match wins, highest → lowest):

| Severity | Trigger | score (0–100) | shaping_hint |
|---|---|---|---|
| `active_atm` | ATM/sales-agreement keyword in a 424B*/prospectus/8-K within the active window | ~90 | shortest horizon, smallest size |
| `high` | recent `424B5` takedown within the active window (~90d) | ~75 | short-dated only, reduced size |
| `medium` | effective `S-3`/`S-3ASR`/`S-1` shelf on file, no recent takedown | ~50 | normal; note capacity overhang |
| `low` | only a stale shelf (older than the shelf-staleness window, ~365d) | ~20 | minimal effect |
| `none` | no dilution-relevant filings found | 0 | none |

Output:

```python
@dataclass
class DilutionFlag:
    ticker: str
    severity: str          # active_atm | high | medium | low | none
    score: float           # 0–100, for ranking
    reasons: list[str]     # human-readable, e.g. "424B5 filed 2026-05-20 (12d ago)"
    filings: list[dict]    # {form, filing_date, url} that drove the score
    shaping_hint: str      # trade-shaping consequence ("flag, don't kill")
    as_of: date
```

The `shaping_hint` carries the "flag, don't kill" principle in the data itself, so
later stages bend the play (horizon / size / expression) rather than dropping the
name. All windows and form lists live in `RadarConfig` / module constants, not inline
in the logic. Active window default 90 days; shelf-staleness default 365 days.

## 6. Store — `store/`

Idempotent migration (`CREATE TABLE IF NOT EXISTS`). Two tables:

```sql
runs(
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT,
    finished_at   TEXT,
    ticker_count  INTEGER,
    ok_count      INTEGER,
    error_count   INTEGER,
    source        TEXT          -- 'edgar'
);

flags(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT REFERENCES runs(run_id),
    ts        TEXT,
    ticker    TEXT,
    type      TEXT,             -- 'dilution'
    severity  TEXT,
    score     REAL,
    meta      TEXT,             -- JSON: reasons, filings, shaping_hint
    source    TEXT              -- 'edgar'
);
```

Helpers in `models.py`: `start_run() -> run_id`, `insert_flag(run_id, DilutionFlag)`,
`finish_run(run_id, ok_count, error_count)`. `run_id` is a generated identifier (a
uuid). History accrues across runs so the first appearance of an ATM is visible over
time.

## 7. CLI & data flow — `cli.py`

```
python -m tradingagents.radar.cli dilution LFVN,SPCE,AAPL [--file tickers.txt] [--json] [--db PATH]
```

- Tickers given as a comma-separated positional arg and/or `--file` (one per line).
- `--json` emits machine-readable output instead of the table; `--db` overrides the
  default DB path.

Flow:

1. Load `RadarConfig` (db path, user-agent, windows).
2. Open store, `start_run()`.
3. For each ticker: `EdgarClient.get_dilution_filings` → `score_dilution` →
   `insert_flag`. Per-ticker errors are caught and recorded (increment `error_count`);
   the batch continues.
4. `finish_run()` with counts.
5. Render a table sorted by severity then score (descending), or JSON.

Default DB path: `~/.tradingagents/radar/radar.db` (reuses the existing
`_TRADINGAGENTS_HOME` convention from `default_config.py`).

## 8. Error handling

- **Unknown ticker / CIK miss** → `DilutionFlag(severity="none", reasons=["not found
  in EDGAR"])`; counts as `ok` (a clean "no data" result), not an error.
- **Network / HTTP error for a ticker** → caught, recorded as a per-ticker error
  (`error_count += 1`), batch continues; the ticker is reported as errored in output.
- **Missing SEC `User-Agent`** → clear startup error before any fetch (SEC requires a
  declared contact).
- **Store migration** is idempotent; re-running is safe.

## 9. Testing (TDD)

- `score_dilution`: table-driven unit tests, one fixture filing-list per severity tier
  (`active_atm`, `high`, `medium`, `low`, `none`) + boundary cases on the recency
  windows.
- `EdgarClient`: injected fake fetch returning recorded `company_tickers.json` and
  submissions JSON; assert CIK resolution, form filtering, and unknown-ticker handling.
  No live network.
- `store`: `:memory:` sqlite — `start_run`/`insert_flag`/`finish_run` round-trip and
  read-back; migration idempotency.
- `cli`: end-to-end with a mocked `EdgarClient`; assert both rendered output and
  persisted rows; assert per-ticker error isolation (one bad ticker doesn't fail the
  batch).

## 10. Success criteria

- `python -m tradingagents.radar.cli dilution <tickers>` runs end-to-end against live
  EDGAR, prints a severity-ranked table, and writes one `flags` row per ticker plus a
  `runs` row.
- A known dilutive small-cap surfaces as `high`/`active_atm`; a large-cap with only an
  old shelf surfaces as `low`/`medium`; an unknown ticker yields `none` without
  crashing the batch.
- All unit tests pass with no network access.
