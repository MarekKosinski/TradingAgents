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
