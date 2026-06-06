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
