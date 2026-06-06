import argparse
import json
import sys
from datetime import date
from pathlib import Path

from tradingagents.radar.config import RadarConfig
from tradingagents.radar.collectors.edgar import EdgarClient
from tradingagents.radar.signals.dilution import SEVERITY_RANK, score_dilution
from tradingagents.radar.store.db import connect, migrate
from tradingagents.radar.store.models import finish_run, insert_flag, start_run


def _parse_tickers(positional: str, file_path: str | None) -> list[str]:
    tickers = []
    if positional:
        tickers += [t.strip().upper() for t in positional.split(",") if t.strip()]
    if file_path:
        with open(file_path) as fh:
            tickers += [line.strip().upper() for line in fh if line.strip()]
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


def _flag_dict(f) -> dict:
    return {"ticker": f.ticker, "severity": f.severity, "score": f.score,
            "reasons": f.reasons, "filings": f.filings,
            "shaping_hint": f.shaping_hint,
            "as_of": f.as_of.isoformat() if f.as_of else None}


def run_dilution(args) -> int:
    cfg = RadarConfig.from_env()
    if args.db:
        cfg.db_path = Path(args.db)

    try:
        tickers = _parse_tickers(args.tickers, args.file)
    except OSError as exc:
        print(f"Could not read ticker file: {exc}", file=sys.stderr)
        return 2
    if not tickers:
        print("No tickers provided.", file=sys.stderr)
        return 2

    try:
        client = EdgarClient(cfg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    as_of = date.today()
    lookback = max(cfg.active_window_days, cfg.shelf_stale_days)
    conn = connect(cfg.db_path)
    try:
        migrate(conn)
        run_id = start_run(conn, source="edgar", ticker_count=len(tickers))

        results, ok, errors = [], 0, 0
        for ticker in tickers:
            try:
                filings = client.get_dilution_filings(ticker, lookback_days=lookback,
                                                      as_of=as_of)
                flag = score_dilution(filings, as_of, cfg)
                flag.ticker = ticker
                insert_flag(conn, run_id, flag)
                results.append(flag)
                ok += 1
            except Exception as exc:  # per-ticker isolation
                print(f"ERROR {ticker}: {exc}", file=sys.stderr)
                errors += 1

        finish_run(conn, run_id, ok_count=ok, error_count=errors)
    finally:
        conn.close()

    if args.json:
        print(json.dumps([_flag_dict(f) for f in results], indent=2))
    else:
        print(_render_table(results))
    # Partial failure is still success; only a wholly-failed run signals non-zero.
    return 1 if ok == 0 and errors > 0 else 0


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
