"""Tests for the Options & Squeeze Analyst agent.

Covers:
- Task 4.1: Agent creation returns callable, returns correct state keys
- Task 4.2: Prompt construction includes all required elements
- Task 4.3: Report extraction — both tool-call and final-report branches
- Task 4.4: Import from package works
"""

from unittest.mock import MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda


def _build_mock_llm(ai_msg):
    """Build a mock LLM whose bind_tools returns a RunnableLambda.

    LangChain's prompt | llm pipe requires the RHS to be a Runnable.
    We use RunnableLambda so it participates in the chain natively,
    while capturing the prompt_value and tools list for assertions.
    """
    captured = {}

    def fake_invoke(prompt_value, config=None, **kwargs):
        captured["prompt_value"] = prompt_value
        return ai_msg

    mock_llm = MagicMock()

    def capture_bind_tools(tools):
        captured["tool_objects"] = tools
        return RunnableLambda(fake_invoke)

    mock_llm.bind_tools = capture_bind_tools

    return mock_llm, captured


# ---------------------------------------------------------------------------
# Task 4.1 — Agent creation returns callable with correct return shape
# ---------------------------------------------------------------------------

class TestAgentCreation:
    """Task 4.1: create_options_squeeze_analyst returns callable with correct keys."""

    def test_returns_callable(self):
        """create_options_squeeze_analyst(llm) should return a callable."""
        from tradingagents.agents.analysts.options_squeeze_analyst import (
            create_options_squeeze_analyst,
        )

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        node = create_options_squeeze_analyst(mock_llm)
        assert callable(node)

    def test_returns_correct_state_keys(self):
        """Calling the node should return dict with 'messages' and 'options_squeeze_report'."""
        from tradingagents.agents.analysts.options_squeeze_analyst import (
            create_options_squeeze_analyst,
        )

        ai_msg = AIMessage(content="Test report", id="test-id")
        mock_llm, captured = _build_mock_llm(ai_msg)
        node = create_options_squeeze_analyst(mock_llm)

        state = {
            "messages": [HumanMessage(content="AAPL")],
            "trade_date": "2026-05-09",
            "company_of_interest": "AAPL",
        }
        result = node(state)

        assert "messages" in result
        assert "options_squeeze_report" in result
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) == 1


# ---------------------------------------------------------------------------
# Task 4.2 — Prompt construction
# ---------------------------------------------------------------------------

class TestPromptConstruction:
    """Task 4.2: System prompt includes all required elements."""

    def _invoke_and_capture(self):
        """Helper: invoke the agent and return captured dict with tools and prompt."""
        from tradingagents.agents.analysts.options_squeeze_analyst import (
            create_options_squeeze_analyst,
        )

        ai_msg = AIMessage(content="Report", id="test-id")
        mock_llm, captured = _build_mock_llm(ai_msg)
        node = create_options_squeeze_analyst(mock_llm)

        state = {
            "messages": [HumanMessage(content="AAPL")],
            "trade_date": "2026-05-09",
            "company_of_interest": "AAPL",
        }
        node(state)
        return captured

    def test_all_six_tools_bound(self):
        """All 6 options/squeeze tools should be bound to the LLM."""
        captured = self._invoke_and_capture()
        tool_names = {t.name for t in captured["tool_objects"]}
        expected = {
            "get_options_expirations",
            "get_options_chain",
            "get_put_call_ratio",
            "get_unusual_options_activity",
            "get_iv_analysis",
            "get_short_squeeze_data",
        }
        assert expected == tool_names

    def test_prompt_mentions_key_topics(self):
        """System prompt should mention options chain, put/call, unusual activity, IV, squeeze."""
        captured = self._invoke_and_capture()
        # prompt_value is a ChatPromptValue; extract the system message text
        messages = captured["prompt_value"].to_messages()
        system_text = messages[0].content.lower()

        assert "options" in system_text
        assert "put/call" in system_text or "put call" in system_text
        assert "unusual" in system_text
        assert "implied volatility" in system_text or "iv" in system_text
        assert "squeeze" in system_text

    def test_prompt_includes_date_and_instrument(self):
        """Prompt should contain the current date and instrument context."""
        captured = self._invoke_and_capture()
        messages = captured["prompt_value"].to_messages()
        system_text = messages[0].content

        assert "2026-05-09" in system_text
        assert "AAPL" in system_text


# ---------------------------------------------------------------------------
# Task 4.3 — Report extraction: tool-call vs final
# ---------------------------------------------------------------------------

class TestReportExtraction:
    """Task 4.3: Conditional report extraction based on tool_calls."""

    def test_no_tool_calls_extracts_report(self):
        """When AIMessage has no tool_calls, options_squeeze_report = content."""
        from tradingagents.agents.analysts.options_squeeze_analyst import (
            create_options_squeeze_analyst,
        )

        ai_msg = AIMessage(content="Options report for AAPL", id="msg-1")
        mock_llm, _ = _build_mock_llm(ai_msg)
        node = create_options_squeeze_analyst(mock_llm)

        state = {
            "messages": [HumanMessage(content="AAPL")],
            "trade_date": "2026-05-09",
            "company_of_interest": "AAPL",
        }
        result = node(state)
        assert result["options_squeeze_report"] == "Options report for AAPL"

    def test_with_tool_calls_empty_report(self):
        """When AIMessage has tool_calls, options_squeeze_report should be empty string."""
        from tradingagents.agents.analysts.options_squeeze_analyst import (
            create_options_squeeze_analyst,
        )

        ai_msg = AIMessage(
            content="",
            id="msg-2",
            tool_calls=[{"name": "get_put_call_ratio", "args": {"ticker": "AAPL"}, "id": "tc1"}],
        )
        mock_llm, _ = _build_mock_llm(ai_msg)
        node = create_options_squeeze_analyst(mock_llm)

        state = {
            "messages": [HumanMessage(content="AAPL")],
            "trade_date": "2026-05-09",
            "company_of_interest": "AAPL",
        }
        result = node(state)
        assert result["options_squeeze_report"] == ""


# ---------------------------------------------------------------------------
# Task 4.4 — Package-level import
# ---------------------------------------------------------------------------

class TestPackageImport:
    """Task 4.4: Agent should be importable from the agents package."""

    def test_import_from_package(self):
        from tradingagents.agents import create_options_squeeze_analyst
        assert callable(create_options_squeeze_analyst)

    def test_in_all(self):
        import tradingagents.agents as agents_pkg
        assert "create_options_squeeze_analyst" in agents_pkg.__all__
