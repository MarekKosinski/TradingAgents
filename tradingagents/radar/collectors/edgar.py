import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

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
            raw = json.loads(self._read_cik_source())
            self._cik_map = {
                row["ticker"].upper(): f"{int(row['cik_str']):010d}"
                for row in raw.values()
            }
        return self._cik_map

    def _read_cik_source(self) -> str:
        """Return company_tickers.json text, caching it on disk to avoid
        re-downloading ~1MB on every run. The cache is best-effort: a write
        failure falls back to the live response."""
        cache = Path(self.config.edgar_cache_dir) / "company_tickers.json"
        if cache.exists():
            return cache.read_text()
        text = self._fetch(_COMPANY_TICKERS_URL, self._headers())
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(text)
        except OSError:
            pass  # caching is an optimization, not a requirement
        return text

    def get_cik(self, ticker: str) -> str | None:
        return self._load_cik_map().get(ticker.upper())

    def get_dilution_filings(self, ticker: str, lookback_days: int,
                             as_of: date | None = None) -> list[Filing]:
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

        today = as_of or date.today()
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
