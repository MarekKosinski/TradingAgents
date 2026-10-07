import re
from dataclasses import dataclass, field
from datetime import date

from tradingagents.radar.collectors.edgar import (
    PROSPECTUS_FORMS,
    SHELF_FORMS,
    Filing,
)
from tradingagents.radar.config import RadarConfig

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


def _reason(filing: Filing, as_of: date) -> str:
    days = (as_of - filing.filing_date).days
    return f"{filing.form} filed {filing.filing_date.isoformat()} ({days}d ago)"


def _to_dict(filing: Filing) -> dict:
    return {"form": filing.form, "filing_date": filing.filing_date.isoformat(),
            "url": filing.url}


def score_dilution(filings: list[Filing], as_of: date, cfg: RadarConfig) -> DilutionFlag:
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


def _build(severity: str, filings: list[Filing], as_of: date) -> DilutionFlag:
    return DilutionFlag(
        ticker="",  # set by caller
        severity=severity,
        score=_SCORE[severity],
        reasons=[_reason(f, as_of) for f in filings],
        filings=[_to_dict(f) for f in filings],
        shaping_hint=_SHAPING[severity],
        as_of=as_of,
    )
