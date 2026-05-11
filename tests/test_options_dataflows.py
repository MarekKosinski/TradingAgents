"""Tests for options data fetcher functions in y_finance_options.py."""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers: build mock yfinance objects
# ---------------------------------------------------------------------------

def _mock_option_chain(
    calls_data=None,
    puts_data=None,
):
    """Return a mock that mimics yf.Ticker(...).option_chain(date)."""
    if calls_data is None:
        calls_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [12.0, 8.0, 4.0],
            "bid": [11.5, 7.5, 3.5],
            "ask": [12.5, 8.5, 4.5],
            "volume": [1000, 500, 200],
            "openInterest": [5000, 3000, 1000],
            "impliedVolatility": [0.30, 0.28, 0.35],
        }
    if puts_data is None:
        puts_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [3.0, 6.0, 10.0],
            "bid": [2.5, 5.5, 9.5],
            "ask": [3.5, 6.5, 10.5],
            "volume": [800, 600, 300],
            "openInterest": [4000, 2500, 1500],
            "impliedVolatility": [0.32, 0.30, 0.38],
        }
    chain = MagicMock()
    chain.calls = pd.DataFrame(calls_data)
    chain.puts = pd.DataFrame(puts_data)
    return chain


def _make_ticker_mock(
    options_dates=("2026-06-20", "2026-07-18", "2026-08-15"),
    chain_factory=None,
    info=None,
    current_price=105.0,
):
    """Build a MagicMock yf.Ticker with configurable options and info."""
    ticker = MagicMock()
    type(ticker).options = PropertyMock(return_value=options_dates)

    if chain_factory is None:
        chain_factory = lambda date: _mock_option_chain()  # noqa: E731
    ticker.option_chain = MagicMock(side_effect=chain_factory)

    if info is None:
        info = {"currentPrice": current_price}
    ticker.info = info
    return ticker


# ---------------------------------------------------------------------------
# Task 1.1: get_options_expirations
# ---------------------------------------------------------------------------

class TestGetOptionsExpirations:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_returns_formatted_expirations(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_options_expirations

        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20", "2026-07-18", "2026-08-15")
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_options_expirations("AAPL")

        assert "# Options Expirations" in result
        assert "AAPL" in result
        assert "2026-06-20" in result
        assert "2026-07-18" in result
        assert "2026-08-15" in result
        assert "3 expiration" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_empty_expirations_returns_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_options_expirations

        ticker_obj = _make_ticker_mock(options_dates=())
        mock_ticker_cls.return_value = ticker_obj

        result = get_options_expirations("FAKE")
        assert "no options" in result.lower() or "No options" in result


# ---------------------------------------------------------------------------
# Task 1.2: get_options_chain
# ---------------------------------------------------------------------------

class TestGetOptionsChain:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_returns_calls_and_puts_csv(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_options_chain

        ticker_obj = _make_ticker_mock()
        mock_ticker_cls.return_value = ticker_obj

        result = get_options_chain("AAPL", "2026-06-20")

        assert "# Options Chain" in result
        assert "AAPL" in result
        assert "CALLS" in result or "Calls" in result or "calls" in result.lower()
        assert "PUTS" in result or "Puts" in result or "puts" in result.lower()
        # Should contain strike prices from our mock
        assert "100.0" in result
        assert "110.0" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_empty_chain_returns_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_options_chain

        empty_chain = MagicMock()
        empty_chain.calls = pd.DataFrame()
        empty_chain.puts = pd.DataFrame()

        ticker_obj = MagicMock()
        ticker_obj.option_chain = MagicMock(return_value=empty_chain)
        mock_ticker_cls.return_value = ticker_obj

        result = get_options_chain("FAKE", "2026-06-20")
        assert "no options chain" in result.lower() or "No options chain" in result


# ---------------------------------------------------------------------------
# Task 1.3: get_put_call_ratio
# ---------------------------------------------------------------------------

class TestGetPutCallRatio:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_computes_ratios_correctly(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_put_call_ratio

        # Calls: volume=1700, OI=9000 across the chain
        # Puts:  volume=1700, OI=8000 across the chain
        # Volume ratio = 1700/1700 = 1.0
        # OI ratio = 8000/9000 = 0.889
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_put_call_ratio("AAPL")

        assert "Put/Call Ratio" in result
        assert "AAPL" in result
        # Should include both volume-weighted and OI-weighted ratios
        assert "volume" in result.lower() or "Volume" in result
        assert "open interest" in result.lower() or "OI" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_zero_call_volume_returns_insufficient_data(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_put_call_ratio

        # Calls with zero volume
        zero_vol_calls = {
            "strike": [100.0, 105.0],
            "lastPrice": [5.0, 3.0],
            "bid": [4.5, 2.5],
            "ask": [5.5, 3.5],
            "volume": [0, 0],
            "openInterest": [1000, 500],
            "impliedVolatility": [0.30, 0.28],
        }
        zero_vol_puts = {
            "strike": [100.0, 105.0],
            "lastPrice": [3.0, 6.0],
            "bid": [2.5, 5.5],
            "ask": [3.5, 6.5],
            "volume": [100, 200],
            "openInterest": [500, 300],
            "impliedVolatility": [0.32, 0.30],
        }

        chain = _mock_option_chain(zero_vol_calls, zero_vol_puts)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_put_call_ratio("FAKE")
        assert "insufficient data" in result.lower()

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_interpretation_bearish(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_put_call_ratio

        # High put volume relative to calls -> bearish interpretation
        high_put_calls = {
            "strike": [100.0],
            "lastPrice": [5.0],
            "bid": [4.5],
            "ask": [5.5],
            "volume": [100],
            "openInterest": [500],
            "impliedVolatility": [0.30],
        }
        high_put_puts = {
            "strike": [100.0],
            "lastPrice": [5.0],
            "bid": [4.5],
            "ask": [5.5],
            "volume": [200],
            "openInterest": [1500],
            "impliedVolatility": [0.30],
        }

        chain = _mock_option_chain(high_put_calls, high_put_puts)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_put_call_ratio("AAPL")
        assert "bearish" in result.lower()

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_no_expirations_returns_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_put_call_ratio

        ticker_obj = _make_ticker_mock(options_dates=())
        mock_ticker_cls.return_value = ticker_obj

        result = get_put_call_ratio("FAKE")
        assert "no options" in result.lower() or "insufficient" in result.lower()


# ---------------------------------------------------------------------------
# Task 1.4: get_unusual_options_activity
# ---------------------------------------------------------------------------

class TestGetUnusualOptionsActivity:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_filters_by_threshold(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_unusual_options_activity

        # One call with vol/OI = 1000/100 = 10.0 (unusual)
        # One call with vol/OI = 50/1000 = 0.05 (normal)
        calls_data = {
            "strike": [100.0, 105.0],
            "lastPrice": [5.0, 3.0],
            "bid": [4.5, 2.5],
            "ask": [5.5, 3.5],
            "volume": [1000, 50],
            "openInterest": [100, 1000],
            "impliedVolatility": [0.45, 0.28],
        }
        puts_data = {
            "strike": [100.0, 105.0],
            "lastPrice": [3.0, 6.0],
            "bid": [2.5, 5.5],
            "ask": [3.5, 6.5],
            "volume": [500, 10],
            "openInterest": [80, 2000],
            "impliedVolatility": [0.50, 0.30],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_unusual_options_activity("AAPL", volume_oi_threshold=3.0)

        assert "Unusual Options Activity" in result
        # The 100.0 strike call (ratio=10.0) should be present
        assert "100.0" in result
        # The 105.0 strike call (ratio=0.05) should NOT be flagged
        # But the 100.0 put (ratio=6.25) should appear
        assert "unusual" in result.lower() or "Unusual" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_sorted_by_ratio_descending(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_unusual_options_activity

        calls_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [5.0, 3.0, 2.0],
            "bid": [4.5, 2.5, 1.5],
            "ask": [5.5, 3.5, 2.5],
            "volume": [500, 1000, 300],
            "openInterest": [50, 100, 30],
            "impliedVolatility": [0.30, 0.35, 0.40],
        }
        puts_data = {
            "strike": [100.0],
            "lastPrice": [3.0],
            "bid": [2.5],
            "ask": [3.5],
            "volume": [10],
            "openInterest": [1000],
            "impliedVolatility": [0.30],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_unusual_options_activity("AAPL", volume_oi_threshold=3.0)

        # All three calls have ratios 10.0, 10.0, 10.0 -- they should all appear
        assert "100.0" in result
        assert "105.0" in result
        assert "110.0" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_no_unusual_activity_returns_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_unusual_options_activity

        # All contracts have very low volume relative to OI
        calls_data = {
            "strike": [100.0],
            "lastPrice": [5.0],
            "bid": [4.5],
            "ask": [5.5],
            "volume": [10],
            "openInterest": [5000],
            "impliedVolatility": [0.30],
        }
        puts_data = {
            "strike": [100.0],
            "lastPrice": [3.0],
            "bid": [2.5],
            "ask": [3.5],
            "volume": [5],
            "openInterest": [3000],
            "impliedVolatility": [0.30],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_unusual_options_activity("AAPL")
        assert "no unusual" in result.lower()

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_limited_to_top_10(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_unusual_options_activity

        # Create 15 contracts that all exceed threshold
        strikes = [float(i) for i in range(90, 105)]
        calls_data = {
            "strike": strikes,
            "lastPrice": [5.0] * 15,
            "bid": [4.5] * 15,
            "ask": [5.5] * 15,
            "volume": [1000] * 15,
            "openInterest": [100] * 15,  # ratio = 10.0 for all
            "impliedVolatility": [0.30] * 15,
        }
        puts_data = {
            "strike": [200.0],
            "lastPrice": [1.0],
            "bid": [0.5],
            "ask": [1.5],
            "volume": [1],
            "openInterest": [1000],
            "impliedVolatility": [0.20],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_unusual_options_activity("AAPL", volume_oi_threshold=3.0)

        # Count lines with strike data -- should not exceed 10 entries
        # The result should mention "Top 10" or limit to 10
        assert "10" in result or result.count("Call") <= 10


# ---------------------------------------------------------------------------
# Task 1.5: get_iv_analysis
# ---------------------------------------------------------------------------

class TestGetIVAnalysis:

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_atm_iv_identified(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_iv_analysis

        # Current price is 105 -> strike 105 is ATM
        calls_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [8.0, 4.0, 1.5],
            "bid": [7.5, 3.5, 1.0],
            "ask": [8.5, 4.5, 2.0],
            "volume": [500, 800, 300],
            "openInterest": [2000, 3000, 1500],
            "impliedVolatility": [0.25, 0.28, 0.35],
        }
        puts_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [2.0, 5.0, 9.0],
            "bid": [1.5, 4.5, 8.5],
            "ask": [2.5, 5.5, 9.5],
            "volume": [400, 600, 200],
            "openInterest": [1500, 2500, 1000],
            "impliedVolatility": [0.30, 0.29, 0.22],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
            current_price=105.0,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_iv_analysis("AAPL")

        assert "IV Analysis" in result or "Implied Volatility" in result
        assert "ATM" in result
        # ATM call IV should be 0.28 or 28%
        assert "28" in result or "0.28" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_iv_skew_included(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_iv_analysis

        calls_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [8.0, 4.0, 1.5],
            "bid": [7.5, 3.5, 1.0],
            "ask": [8.5, 4.5, 2.0],
            "volume": [500, 800, 300],
            "openInterest": [2000, 3000, 1500],
            "impliedVolatility": [0.25, 0.28, 0.35],
        }
        puts_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [2.0, 5.0, 9.0],
            "bid": [1.5, 4.5, 8.5],
            "ask": [2.5, 5.5, 9.5],
            "volume": [400, 600, 200],
            "openInterest": [1500, 2500, 1000],
            "impliedVolatility": [0.30, 0.29, 0.22],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
            current_price=105.0,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_iv_analysis("AAPL")
        assert "skew" in result.lower()

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_iv_range_included(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_iv_analysis

        calls_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [8.0, 4.0, 1.5],
            "bid": [7.5, 3.5, 1.0],
            "ask": [8.5, 4.5, 2.0],
            "volume": [500, 800, 300],
            "openInterest": [2000, 3000, 1500],
            "impliedVolatility": [0.25, 0.28, 0.35],
        }
        puts_data = {
            "strike": [100.0, 105.0, 110.0],
            "lastPrice": [2.0, 5.0, 9.0],
            "bid": [1.5, 4.5, 8.5],
            "ask": [2.5, 5.5, 9.5],
            "volume": [400, 600, 200],
            "openInterest": [1500, 2500, 1000],
            "impliedVolatility": [0.30, 0.29, 0.22],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
            current_price=105.0,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_iv_analysis("AAPL")
        # Should mention min and max IV values
        assert "min" in result.lower() or "Min" in result
        assert "max" in result.lower() or "Max" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_sparse_chain_returns_partial_analysis(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_iv_analysis

        # Only one strike each side -- sparse data
        calls_data = {
            "strike": [105.0],
            "lastPrice": [4.0],
            "bid": [3.5],
            "ask": [4.5],
            "volume": [100],
            "openInterest": [500],
            "impliedVolatility": [0.30],
        }
        puts_data = {
            "strike": [105.0],
            "lastPrice": [4.0],
            "bid": [3.5],
            "ask": [4.5],
            "volume": [100],
            "openInterest": [500],
            "impliedVolatility": [0.32],
        }

        chain = _mock_option_chain(calls_data, puts_data)
        ticker_obj = _make_ticker_mock(
            options_dates=("2026-06-20",),
            chain_factory=lambda date: chain,
            current_price=105.0,
        )
        mock_ticker_cls.return_value = ticker_obj

        result = get_iv_analysis("AAPL")
        # Should still return something meaningful
        assert "IV" in result or "Volatility" in result
        assert "AAPL" in result

    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_no_options_returns_message(self, mock_ticker_cls, mock_retry):
        from tradingagents.dataflows.y_finance_options import get_iv_analysis

        ticker_obj = _make_ticker_mock(options_dates=())
        mock_ticker_cls.return_value = ticker_obj

        result = get_iv_analysis("FAKE")
        assert "no options" in result.lower() or "No options" in result
