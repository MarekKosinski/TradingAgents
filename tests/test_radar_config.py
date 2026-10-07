from pathlib import Path

import pytest

from tradingagents.radar.config import RadarConfig


@pytest.mark.unit
def test_defaults_use_tradingagents_home():
    cfg = RadarConfig()
    assert cfg.db_path == Path.home() / ".tradingagents" / "radar" / "radar.db"
    assert cfg.edgar_cache_dir == Path.home() / ".tradingagents" / "radar" / "cache"
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
