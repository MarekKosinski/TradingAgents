"""Tests for short squeeze data fetcher in y_finance_options.py."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ticker_with_info(info_dict):
    """Build a mock yf.Ticker with given info dict."""
    ticker = MagicMock()
    ticker.info = info_dict
    type(ticker).options = PropertyMock(return_value=())
    return ticker


# ---------------------------------------------------------------------------
# Task 2.1: get_short_squeeze_data — normal case
# ---------------------------------------------------------------------------

class TestGetShortSqueezeData:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_returns_all_fields(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        info = {
            "shortPercentOfFloat": 0.15,
            "shortRatio": 3.5,
            "sharesShort": 10_000_000,
            "sharesShortPriorMonth": 8_000_000,
            "floatShares": 100_000_000,
            "sharesOutstanding": 120_000_000,
            "heldPercentInstitutions": 0.65,
            "heldPercentInsiders": 0.05,
            "currentPrice": 50.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("GME")

        assert "Short" in result or "short" in result
        assert "GME" in result
        assert "15" in result  # short% of float as percentage
        assert "3.5" in result  # short ratio / days to cover
        assert "10" in result  # shares short (in millions or raw)
        assert "Institutional" in result or "institutional" in result.lower()

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_mom_change_computed(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        info = {
            "shortPercentOfFloat": 0.15,
            "shortRatio": 3.5,
            "sharesShort": 10_000_000,
            "sharesShortPriorMonth": 8_000_000,
            "floatShares": 100_000_000,
            "sharesOutstanding": 120_000_000,
            "heldPercentInstitutions": 0.65,
            "heldPercentInsiders": 0.05,
            "currentPrice": 50.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("GME")

        # MoM change: (10M - 8M) / 8M = 25% increase
        assert "25" in result or "increase" in result.lower() or "rising" in result.lower()


# ---------------------------------------------------------------------------
# Task 2.2: Squeeze score calculation
# ---------------------------------------------------------------------------

class TestSqueezeScoring:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_extreme_squeeze_scenario(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        info = {
            "shortPercentOfFloat": 0.35,   # 35% short of float -> Extreme
            "shortRatio": 8.5,             # high days to cover
            "sharesShort": 50_000_000,
            "sharesShortPriorMonth": 40_000_000,  # rising
            "floatShares": 140_000_000,
            "sharesOutstanding": 200_000_000,
            "heldPercentInstitutions": 0.45,
            "heldPercentInsiders": 0.10,
            "currentPrice": 25.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("GME")
        assert "Extreme" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_low_squeeze_scenario(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        info = {
            "shortPercentOfFloat": 0.02,   # 2% short of float -> Low
            "shortRatio": 1.0,             # low days to cover
            "sharesShort": 5_000_000,
            "sharesShortPriorMonth": 6_000_000,  # declining
            "floatShares": 500_000_000,
            "sharesOutstanding": 600_000_000,
            "heldPercentInstitutions": 0.70,
            "heldPercentInsiders": 0.02,
            "currentPrice": 180.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("AAPL")
        assert "Low" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_high_squeeze_scenario(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        # 22% short of float -> base High, no modifiers to keep it at High
        info = {
            "shortPercentOfFloat": 0.22,   # 22% -> High (>20% but <=30%)
            "shortRatio": 4.0,             # below 5 -> no elevation
            "sharesShort": 20_000_000,
            "sharesShortPriorMonth": 22_000_000,  # declining -> no elevation
            "floatShares": 90_000_000,
            "sharesOutstanding": 110_000_000,
            "heldPercentInstitutions": 0.55,
            "heldPercentInsiders": 0.08,
            "currentPrice": 40.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("MEME")
        assert "High" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_medium_squeeze_scenario(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        # 12% short -> base Medium; no modifiers active to keep it at Medium
        info = {
            "shortPercentOfFloat": 0.12,   # 12% -> base Medium (>10%)
            "shortRatio": 3.0,             # below 5 -> no elevation
            "sharesShort": 15_000_000,
            "sharesShortPriorMonth": 16_000_000,  # declining -> no elevation
            "floatShares": 120_000_000,
            "sharesOutstanding": 150_000_000,
            "heldPercentInstitutions": 0.60,
            "heldPercentInsiders": 0.05,
            "currentPrice": 60.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("TEST")
        assert "Medium" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_modifiers_elevate_score(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        # 12% -> base Medium(1), DTC>5 -> +1=High(2), rising -> +1=Extreme(3)
        info = {
            "shortPercentOfFloat": 0.12,
            "shortRatio": 6.0,
            "sharesShort": 15_000_000,
            "sharesShortPriorMonth": 14_000_000,
            "floatShares": 120_000_000,
            "sharesOutstanding": 150_000_000,
            "heldPercentInstitutions": 0.60,
            "heldPercentInsiders": 0.05,
            "currentPrice": 60.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("TEST")
        assert "Extreme" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_partially_missing_fields(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        # Some fields are None -- should not crash
        info = {
            "shortPercentOfFloat": 0.10,
            "shortRatio": None,
            "sharesShort": 5_000_000,
            "sharesShortPriorMonth": None,
            "floatShares": 100_000_000,
            "sharesOutstanding": None,
            "heldPercentInstitutions": None,
            "heldPercentInsiders": None,
            "currentPrice": 50.0,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("TEST")
        # Should not crash and should still produce a report
        assert "Short" in result or "short" in result
        assert "TEST" in result


# ---------------------------------------------------------------------------
# Task 2.3: Edge case — empty/None info
# ---------------------------------------------------------------------------

class TestSqueezeEdgeCases:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_empty_info_returns_graceful_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        mock_ticker_cls.return_value = _make_ticker_with_info({})

        result = get_short_squeeze_data("FAKE")
        assert "no short interest" in result.lower() or "No short interest" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_none_info_returns_graceful_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        ticker = MagicMock()
        ticker.info = None
        mock_ticker_cls.return_value = ticker

        result = get_short_squeeze_data("FAKE")
        assert "no short interest" in result.lower() or "No short interest" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_all_none_fields_returns_graceful_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_short_squeeze_data

        info = {
            "shortPercentOfFloat": None,
            "shortRatio": None,
            "sharesShort": None,
            "sharesShortPriorMonth": None,
            "floatShares": None,
            "sharesOutstanding": None,
            "heldPercentInstitutions": None,
            "heldPercentInsiders": None,
        }
        mock_ticker_cls.return_value = _make_ticker_with_info(info)

        result = get_short_squeeze_data("FAKE")
        assert "no short interest" in result.lower() or "No short interest" in result
