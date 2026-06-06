import json
from datetime import date

import pytest

from tradingagents.radar.config import RadarConfig
from tradingagents.radar.collectors.edgar import (
    _COMPANY_TICKERS_URL,
    EdgarClient,
    Filing,
)

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


@pytest.fixture
def client(tmp_path):
    # edgar_cache_dir points at tmp so the on-disk CIK cache never touches the
    # real home and tests never persist the fake fixture data.
    cfg = RadarConfig(sec_user_agent="Test test@example.com",
                      edgar_cache_dir=tmp_path / "cache")
    return EdgarClient(cfg, fetch=_fake_fetch)


@pytest.mark.unit
def test_get_cik_zero_pads(client):
    assert client.get_cik("LFVN") == "0001062292"


@pytest.mark.unit
def test_get_cik_unknown_returns_none(client):
    assert client.get_cik("ZZZZ") is None


@pytest.mark.unit
def test_cik_map_is_cached_on_disk(tmp_path):
    calls = []

    def counting_fetch(url, headers):
        calls.append(url)
        return _fake_fetch(url, headers)

    cfg = RadarConfig(sec_user_agent="Test test@example.com",
                      edgar_cache_dir=tmp_path / "cache")
    # First client downloads and writes the cache; a second fresh client reads
    # it from disk without re-fetching company_tickers.json.
    EdgarClient(cfg, fetch=counting_fetch).get_cik("LFVN")
    EdgarClient(cfg, fetch=counting_fetch).get_cik("LFVN")
    assert (tmp_path / "cache" / "company_tickers.json").exists()
    assert calls.count(_COMPANY_TICKERS_URL) == 1


@pytest.mark.unit
def test_get_dilution_filings_filters_to_relevant_forms(client):
    filings = client.get_dilution_filings("LFVN", lookback_days=3650)
    forms = sorted(f.form for f in filings)
    assert forms == ["424B5", "S-3"]  # 8-K and 10-Q dropped
    f424 = next(f for f in filings if f.form == "424B5")
    assert isinstance(f424, Filing)
    assert f424.filing_date.isoformat() == "2026-05-20"
    assert "1062292" in f424.url


@pytest.mark.unit
def test_get_dilution_filings_respects_lookback_window(client):
    # as_of=2026-06-01: 424B5 (2026-05-20) is 12d old, S-3 (2025-01-10) ~507d old.
    # A 90-day window keeps only the 424B5.
    filings = client.get_dilution_filings(
        "LFVN", lookback_days=90, as_of=date(2026, 6, 1)
    )
    assert [f.form for f in filings] == ["424B5"]


@pytest.mark.unit
def test_get_dilution_filings_unknown_ticker_returns_empty(client):
    assert client.get_dilution_filings("ZZZZ", lookback_days=3650) == []


@pytest.mark.unit
def test_missing_user_agent_raises():
    with pytest.raises(ValueError):
        EdgarClient(RadarConfig(sec_user_agent=None), fetch=_fake_fetch)
