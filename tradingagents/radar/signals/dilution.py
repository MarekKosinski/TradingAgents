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
