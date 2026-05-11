"""Tests for options/squeeze interface registration, config, and tool wrappers."""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Task 3.1: Interface registration
# ---------------------------------------------------------------------------

class TestInterfaceRegistration:
    """Verify the options_squeeze_data category is registered in interface.py."""

    def test_category_exists(self):
        from tradingagents.dataflows.interface import TOOLS_CATEGORIES
        assert "options_squeeze_data" in TOOLS_CATEGORIES

    def test_category_has_all_tools(self):
        from tradingagents.dataflows.interface import TOOLS_CATEGORIES
        tools = TOOLS_CATEGORIES["options_squeeze_data"]["tools"]
        expected = [
            "get_options_expirations",
            "get_options_chain",
            "get_put_call_ratio",
            "get_unusual_options_activity",
            "get_iv_analysis",
            "get_short_squeeze_data",
        ]
        for method in expected:
            assert method in tools, f"{method} missing from options_squeeze_data tools"

    def test_get_category_for_method_returns_options_squeeze(self):
        from tradingagents.dataflows.interface import get_category_for_method
        methods = [
            "get_options_expirations",
            "get_options_chain",
            "get_put_call_ratio",
            "get_unusual_options_activity",
            "get_iv_analysis",
            "get_short_squeeze_data",
        ]
        for method in methods:
            assert get_category_for_method(method) == "options_squeeze_data", (
                f"get_category_for_method('{method}') did not return 'options_squeeze_data'"
            )

    def test_all_methods_in_vendor_methods(self):
        from tradingagents.dataflows.interface import VENDOR_METHODS
        methods = [
            "get_options_expirations",
            "get_options_chain",
            "get_put_call_ratio",
            "get_unusual_options_activity",
            "get_iv_analysis",
            "get_short_squeeze_data",
        ]
        for method in methods:
            assert method in VENDOR_METHODS, f"{method} missing from VENDOR_METHODS"
            assert "yfinance" in VENDOR_METHODS[method], (
                f"{method} missing yfinance implementation in VENDOR_METHODS"
            )

    def test_vendor_methods_point_to_correct_functions(self):
        from tradingagents.dataflows.interface import VENDOR_METHODS
        from tradingagents.dataflows.y_finance_options import (
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        )

        expected_mapping = {
            "get_options_expirations": get_options_expirations,
            "get_options_chain": get_options_chain,
            "get_put_call_ratio": get_put_call_ratio,
            "get_unusual_options_activity": get_unusual_options_activity,
            "get_iv_analysis": get_iv_analysis,
            "get_short_squeeze_data": get_short_squeeze_data,
        }

        for method, expected_fn in expected_mapping.items():
            actual_fn = VENDOR_METHODS[method]["yfinance"]
            assert actual_fn is expected_fn, (
                f"VENDOR_METHODS['{method}']['yfinance'] does not point to the correct function"
            )


# ---------------------------------------------------------------------------
# Task 3.2: Default config
# ---------------------------------------------------------------------------

class TestDefaultConfig:

    def test_options_squeeze_data_in_data_vendors(self):
        from tradingagents.default_config import DEFAULT_CONFIG
        vendors = DEFAULT_CONFIG["data_vendors"]
        assert "options_squeeze_data" in vendors
        assert vendors["options_squeeze_data"] == "yfinance"

    def test_get_config_includes_options_squeeze(self):
        from tradingagents.dataflows.config import get_config
        config = get_config()
        vendors = config.get("data_vendors", {})
        assert "options_squeeze_data" in vendors
        assert vendors["options_squeeze_data"] == "yfinance"


# ---------------------------------------------------------------------------
# Task 3.3: Tool wrappers
# ---------------------------------------------------------------------------

class TestToolWrappers:

    def test_tools_can_be_imported(self):
        from tradingagents.agents.utils.options_squeeze_tools import (
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        )
        # All imports succeed

    def test_tools_are_invocable(self):
        from tradingagents.agents.utils.options_squeeze_tools import (
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        )
        for tool_fn in [
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        ]:
            assert hasattr(tool_fn, "invoke"), f"{tool_fn.name} has no invoke method"
            assert hasattr(tool_fn, "name"), f"tool missing name attribute"

    def test_tools_have_docstrings(self):
        from tradingagents.agents.utils.options_squeeze_tools import (
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        )
        for tool_fn in [
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        ]:
            assert tool_fn.description, f"{tool_fn.name} has no description"


# ---------------------------------------------------------------------------
# Task 3.4: Tool routing end-to-end
# ---------------------------------------------------------------------------

class TestToolRouting:

    @patch("tradingagents.dataflows.interface.get_config")
    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_get_options_expirations_routes(self, mock_ticker_cls, mock_retry, mock_config):
        mock_config.return_value = {
            "data_vendors": {"options_squeeze_data": "yfinance"},
            "tool_vendors": {},
        }
        from tradingagents.agents.utils.options_squeeze_tools import get_options_expirations

        ticker = MagicMock()
        type(ticker).options = property(lambda self: ("2026-06-20",))
        mock_ticker_cls.return_value = ticker

        result = get_options_expirations.invoke({"ticker": "AAPL"})
        assert "Options Expirations" in result or "AAPL" in result

    @patch("tradingagents.dataflows.interface.get_config")
    @patch("tradingagents.dataflows.y_finance_options.yf_retry", side_effect=lambda fn: fn())
    @patch("tradingagents.dataflows.y_finance_options.yf.Ticker")
    def test_get_short_squeeze_data_routes(self, mock_ticker_cls, mock_retry, mock_config):
        mock_config.return_value = {
            "data_vendors": {"options_squeeze_data": "yfinance"},
            "tool_vendors": {},
        }
        from tradingagents.agents.utils.options_squeeze_tools import get_short_squeeze_data

        ticker = MagicMock()
        ticker.info = {
            "shortPercentOfFloat": 0.15,
            "shortRatio": 3.5,
            "sharesShort": 10_000_000,
            "sharesShortPriorMonth": 8_000_000,
            "floatShares": 100_000_000,
            "sharesOutstanding": 120_000_000,
            "heldPercentInstitutions": 0.65,
            "heldPercentInsiders": 0.05,
        }
        mock_ticker_cls.return_value = ticker

        result = get_short_squeeze_data.invoke({"ticker": "GME"})
        assert "Short" in result or "GME" in result


# ---------------------------------------------------------------------------
# Task 3.5: agent_utils imports
# ---------------------------------------------------------------------------

class TestAgentUtilsImports:

    def test_tools_importable_from_agent_utils(self):
        from tradingagents.agents.utils.agent_utils import (
            get_options_expirations,
            get_options_chain,
            get_put_call_ratio,
            get_unusual_options_activity,
            get_iv_analysis,
            get_short_squeeze_data,
        )
        # All imports succeed
