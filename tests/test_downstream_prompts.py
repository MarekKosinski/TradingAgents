"""Tests for Phase 6: Downstream Prompt Updates & Integration.

Covers:
- Task 6.1: Bull researcher prompt includes options_squeeze_report
- Task 6.2: Bear researcher prompt includes options_squeeze_report
- Task 6.3: Trader prompt mentions options/squeeze analysis
- Task 6.4: Empty options_squeeze_report renders cleanly (no 'None' or errors)
"""

from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Task 6.1 -- Bull researcher prompt includes options_squeeze_report
# ---------------------------------------------------------------------------

class TestBullResearcherPrompt:
    """Task 6.1: Bull researcher reads options_squeeze_report from state."""

    def _invoke_bull_and_capture_prompt(self, options_squeeze_report="Options data here"):
        """Helper: invoke bull_node and capture the prompt passed to llm.invoke."""
        from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bull argument")
        node = create_bull_researcher(mock_llm)

        state = {
            "market_report": "Market data",
            "sentiment_report": "Sentiment data",
            "news_report": "News data",
            "fundamentals_report": "Fundamentals data",
            "options_squeeze_report": options_squeeze_report,
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "count": 0,
            },
        }
        node(state)
        prompt_arg = mock_llm.invoke.call_args[0][0]
        return prompt_arg

    def test_prompt_contains_options_squeeze_report_variable(self):
        """The bull researcher prompt should include the options_squeeze_report content."""
        prompt = self._invoke_bull_and_capture_prompt("Options flow data for AAPL")
        assert "Options flow data for AAPL" in prompt

    def test_prompt_labels_options_squeeze_section(self):
        """The prompt should have a label identifying the options/squeeze report section."""
        prompt = self._invoke_bull_and_capture_prompt()
        prompt_lower = prompt.lower()
        assert "options" in prompt_lower
        assert "squeeze" in prompt_lower or "short" in prompt_lower


# ---------------------------------------------------------------------------
# Task 6.2 -- Bear researcher prompt includes options_squeeze_report
# ---------------------------------------------------------------------------

class TestBearResearcherPrompt:
    """Task 6.2: Bear researcher reads options_squeeze_report from state."""

    def _invoke_bear_and_capture_prompt(self, options_squeeze_report="Options data here"):
        """Helper: invoke bear_node and capture the prompt passed to llm.invoke."""
        from tradingagents.agents.researchers.bear_researcher import create_bear_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bear argument")
        node = create_bear_researcher(mock_llm)

        state = {
            "market_report": "Market data",
            "sentiment_report": "Sentiment data",
            "news_report": "News data",
            "fundamentals_report": "Fundamentals data",
            "options_squeeze_report": options_squeeze_report,
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "count": 0,
            },
        }
        node(state)
        prompt_arg = mock_llm.invoke.call_args[0][0]
        return prompt_arg

    def test_prompt_contains_options_squeeze_report_variable(self):
        """The bear researcher prompt should include the options_squeeze_report content."""
        prompt = self._invoke_bear_and_capture_prompt("Options flow data for AAPL")
        assert "Options flow data for AAPL" in prompt

    def test_prompt_labels_options_squeeze_section(self):
        """The prompt should have a label identifying the options/squeeze report section."""
        prompt = self._invoke_bear_and_capture_prompt()
        prompt_lower = prompt.lower()
        assert "options" in prompt_lower
        assert "squeeze" in prompt_lower or "short" in prompt_lower


# ---------------------------------------------------------------------------
# Task 6.3 -- Trader prompt mentions options/squeeze analysis
# ---------------------------------------------------------------------------

class TestTraderPrompt:
    """Task 6.3: Trader prompt references options flow and short interest data."""

    def test_system_prompt_mentions_options(self):
        """Trader system message should mention options as a data dimension."""
        from tradingagents.agents.trader.trader import create_trader
        from tradingagents.agents.schemas import TraderProposal, render_trader_proposal

        captured_messages = {}

        mock_llm = MagicMock()

        # We need to capture the messages passed to invoke_structured_or_freetext.
        # Patch invoke_structured_or_freetext to capture messages and return a string.
        with patch(
            "tradingagents.agents.trader.trader.invoke_structured_or_freetext",
            return_value="Trade decision",
        ) as mock_invoke:
            node = create_trader(mock_llm)
            state = {
                "company_of_interest": "AAPL",
                "investment_plan": "Buy AAPL based on analysis.",
            }
            node(state)
            # invoke_structured_or_freetext is called with (structured_llm, llm, messages, render_fn, label)
            call_args = mock_invoke.call_args
            messages = call_args[0][2]  # Third positional arg
            captured_messages["messages"] = messages

        system_content = messages[0]["content"].lower()
        assert "options" in system_content or "short interest" in system_content

    def test_user_prompt_mentions_options(self):
        """Trader user message should mention options/squeeze insights as a data dimension."""
        from tradingagents.agents.trader.trader import create_trader

        captured_messages = {}

        mock_llm = MagicMock()

        with patch(
            "tradingagents.agents.trader.trader.invoke_structured_or_freetext",
            return_value="Trade decision",
        ) as mock_invoke:
            node = create_trader(mock_llm)
            state = {
                "company_of_interest": "AAPL",
                "investment_plan": "Buy AAPL based on analysis.",
            }
            node(state)
            call_args = mock_invoke.call_args
            messages = call_args[0][2]

        user_content = messages[1]["content"].lower()
        assert "options" in user_content or "short interest" in user_content or "squeeze" in user_content


# ---------------------------------------------------------------------------
# Task 6.4 -- Empty options_squeeze_report renders cleanly
# ---------------------------------------------------------------------------

class TestEmptyReportHandling:
    """Task 6.4: When options_squeeze_report is empty string, prompts render cleanly."""

    def test_bull_prompt_no_none_with_empty_report(self):
        """Bull prompt with empty options_squeeze_report should not contain 'None'."""
        from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bull argument")
        node = create_bull_researcher(mock_llm)

        state = {
            "market_report": "Market data",
            "sentiment_report": "Sentiment data",
            "news_report": "News data",
            "fundamentals_report": "Fundamentals data",
            "options_squeeze_report": "",
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "count": 0,
            },
        }
        node(state)
        prompt = mock_llm.invoke.call_args[0][0]
        # Should not contain literal "None" (which would indicate f-string rendered None)
        assert "None" not in prompt
        # Should not contain error-like text
        assert "error" not in prompt.lower()
        assert "traceback" not in prompt.lower()

    def test_bear_prompt_no_none_with_empty_report(self):
        """Bear prompt with empty options_squeeze_report should not contain 'None'."""
        from tradingagents.agents.researchers.bear_researcher import create_bear_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bear argument")
        node = create_bear_researcher(mock_llm)

        state = {
            "market_report": "Market data",
            "sentiment_report": "Sentiment data",
            "news_report": "News data",
            "fundamentals_report": "Fundamentals data",
            "options_squeeze_report": "",
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "count": 0,
            },
        }
        node(state)
        prompt = mock_llm.invoke.call_args[0][0]
        assert "None" not in prompt
        assert "error" not in prompt.lower()
        assert "traceback" not in prompt.lower()

    def test_bull_prompt_reads_cleanly_with_empty_report(self):
        """Bull prompt with empty report should still be a coherent prompt string."""
        from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bull argument")
        node = create_bull_researcher(mock_llm)

        state = {
            "market_report": "Market data",
            "sentiment_report": "Sentiment data",
            "news_report": "News data",
            "fundamentals_report": "Fundamentals data",
            "options_squeeze_report": "",
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "count": 0,
            },
        }
        node(state)
        prompt = mock_llm.invoke.call_args[0][0]
        # The prompt should be a non-empty string (not broken by the empty report)
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # The prompt is substantial even without the report
