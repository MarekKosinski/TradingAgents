"""End-to-end smoke tests for the options/squeeze analyst integration.

Task 6.5: Verifies that the full pipeline compiles, initial state is correct,
agent nodes produce expected outputs with mock state, and prompt templates
render without errors when given state containing options_squeeze_report.
"""

from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(content="Mock response"):
    """Create a mock LLM that returns a fixed AIMessage for both direct and piped invocation."""
    ai_msg = AIMessage(content=content, id="mock-id")

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = ai_msg

    # bind_tools must return a Runnable so prompt | llm works
    def fake_bind_tools(tools):
        return RunnableLambda(lambda x: ai_msg)

    mock_llm.bind_tools = fake_bind_tools

    # For structured output binding (Trader, Research Manager)
    mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
    mock_llm.bind = MagicMock(return_value=mock_llm)

    return mock_llm


# ---------------------------------------------------------------------------
# Test: Graph compiles with all 5 analysts
# ---------------------------------------------------------------------------

class TestGraphCompilationWithAllAnalysts:
    """Verify the graph compiles with all 5 analysts including options_squeeze."""

    def test_graph_compiles_with_five_analysts(self):
        """StateGraph with all 5 analysts should compile without errors."""
        from tradingagents.graph.setup import GraphSetup
        from tradingagents.graph.conditional_logic import ConditionalLogic

        mock_llm = _make_mock_llm()
        tool_nodes = {
            "market": MagicMock(),
            "social": MagicMock(),
            "news": MagicMock(),
            "fundamentals": MagicMock(),
            "options_squeeze": MagicMock(),
        }
        cl = ConditionalLogic()
        gs = GraphSetup(mock_llm, mock_llm, tool_nodes, cl)

        selected = ["market", "social", "news", "fundamentals", "options_squeeze"]
        workflow = gs.setup_graph(selected_analysts=selected)
        graph = workflow.compile()
        assert graph is not None

    def test_all_five_analyst_nodes_present(self):
        """The compiled workflow should have nodes for all 5 analysts."""
        from tradingagents.graph.setup import GraphSetup
        from tradingagents.graph.conditional_logic import ConditionalLogic

        mock_llm = _make_mock_llm()
        tool_nodes = {
            "market": MagicMock(),
            "social": MagicMock(),
            "news": MagicMock(),
            "fundamentals": MagicMock(),
            "options_squeeze": MagicMock(),
        }
        cl = ConditionalLogic()
        gs = GraphSetup(mock_llm, mock_llm, tool_nodes, cl)

        selected = ["market", "social", "news", "fundamentals", "options_squeeze"]
        workflow = gs.setup_graph(selected_analysts=selected)
        node_names = set(workflow.nodes.keys())

        assert "Market Analyst" in node_names
        assert "Social Analyst" in node_names
        assert "News Analyst" in node_names
        assert "Fundamentals Analyst" in node_names
        assert "Options_squeeze Analyst" in node_names

    def test_options_squeeze_tool_and_clear_nodes_present(self):
        """The workflow should have tools and Msg Clear nodes for options_squeeze."""
        from tradingagents.graph.setup import GraphSetup
        from tradingagents.graph.conditional_logic import ConditionalLogic

        mock_llm = _make_mock_llm()
        tool_nodes = {
            "market": MagicMock(),
            "social": MagicMock(),
            "news": MagicMock(),
            "fundamentals": MagicMock(),
            "options_squeeze": MagicMock(),
        }
        cl = ConditionalLogic()
        gs = GraphSetup(mock_llm, mock_llm, tool_nodes, cl)

        selected = ["market", "social", "news", "fundamentals", "options_squeeze"]
        workflow = gs.setup_graph(selected_analysts=selected)
        node_names = set(workflow.nodes.keys())

        assert "tools_options_squeeze" in node_names
        assert "Msg Clear Options_squeeze" in node_names


# ---------------------------------------------------------------------------
# Test: Initial state has all required fields
# ---------------------------------------------------------------------------

class TestInitialStateCompleteness:
    """Verify the initial state includes all required fields."""

    def test_initial_state_has_options_squeeze_report(self):
        """Propagator initial state should include options_squeeze_report."""
        from tradingagents.graph.propagation import Propagator

        prop = Propagator()
        state = prop.create_initial_state("AAPL", "2026-05-09")
        assert "options_squeeze_report" in state
        assert state["options_squeeze_report"] == ""

    def test_initial_state_has_all_report_fields(self):
        """All 5 analyst report fields should be in the initial state."""
        from tradingagents.graph.propagation import Propagator

        prop = Propagator()
        state = prop.create_initial_state("AAPL", "2026-05-09")

        expected_fields = [
            "market_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
            "options_squeeze_report",
        ]
        for field in expected_fields:
            assert field in state, f"Missing field: {field}"
            assert isinstance(state[field], str), f"Field {field} is not a string"


# ---------------------------------------------------------------------------
# Test: Agent node functions produce expected output with mock state
# ---------------------------------------------------------------------------

class TestAgentNodesWithMockState:
    """Verify agent nodes can be called with mock state containing all fields."""

    def _build_full_state(self):
        """Build a complete mock state dict with all required fields."""
        return {
            "messages": [HumanMessage(content="Analyze AAPL")],
            "company_of_interest": "AAPL",
            "trade_date": "2026-05-09",
            "sender": "",
            "market_report": "Market is up",
            "sentiment_report": "Sentiment is positive",
            "news_report": "Good earnings news",
            "fundamentals_report": "Strong balance sheet",
            "options_squeeze_report": "High put/call ratio, elevated short interest",
            "investment_debate_state": {
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "judge_decision": "",
                "count": 0,
            },
            "investment_plan": "",
            "trader_investment_plan": "",
            "risk_debate_state": {
                "aggressive_history": "",
                "conservative_history": "",
                "neutral_history": "",
                "history": "",
                "latest_speaker": "",
                "current_aggressive_response": "",
                "current_conservative_response": "",
                "current_neutral_response": "",
                "judge_decision": "",
                "count": 0,
            },
            "final_trade_decision": "",
            "past_context": "",
        }

    def test_options_squeeze_analyst_with_full_state(self):
        """Options squeeze analyst should produce report from full state."""
        from tradingagents.agents.analysts.options_squeeze_analyst import (
            create_options_squeeze_analyst,
        )

        mock_llm = _make_mock_llm("Options analysis: elevated put/call ratio")
        node = create_options_squeeze_analyst(mock_llm)

        state = self._build_full_state()
        result = node(state)

        assert "options_squeeze_report" in result
        assert "messages" in result
        assert result["options_squeeze_report"] == "Options analysis: elevated put/call ratio"

    def test_bull_researcher_with_full_state_including_options(self):
        """Bull researcher should work with state containing options_squeeze_report."""
        from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bull case with options support")
        node = create_bull_researcher(mock_llm)

        state = self._build_full_state()
        result = node(state)

        assert "investment_debate_state" in result
        # Verify the options data made it into the prompt
        prompt = mock_llm.invoke.call_args[0][0]
        assert "High put/call ratio, elevated short interest" in prompt

    def test_bear_researcher_with_full_state_including_options(self):
        """Bear researcher should work with state containing options_squeeze_report."""
        from tradingagents.agents.researchers.bear_researcher import create_bear_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Bear case with options warning")
        node = create_bear_researcher(mock_llm)

        state = self._build_full_state()
        result = node(state)

        assert "investment_debate_state" in result
        prompt = mock_llm.invoke.call_args[0][0]
        assert "High put/call ratio, elevated short interest" in prompt


# ---------------------------------------------------------------------------
# Test: Prompt templates render without errors with options_squeeze_report
# ---------------------------------------------------------------------------

class TestPromptTemplateRendering:
    """Verify prompt templates render cleanly with various options_squeeze_report values."""

    def test_bull_prompt_with_rich_options_report(self):
        """Bull prompt should render cleanly with a detailed options report."""
        from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Response")
        node = create_bull_researcher(mock_llm)

        rich_report = (
            "## Options Analysis for AAPL\n"
            "Put/Call Ratio: 0.85 (slightly bullish)\n"
            "Unusual Activity: 5 contracts detected\n"
            "IV Skew: Puts trading at premium\n"
            "Short Interest: 1.2% of float\n"
            "Squeeze Score: Low"
        )

        state = {
            "market_report": "Market data",
            "sentiment_report": "Sentiment data",
            "news_report": "News data",
            "fundamentals_report": "Fundamentals data",
            "options_squeeze_report": rich_report,
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

        # The entire rich report should appear in the prompt
        assert "Put/Call Ratio: 0.85" in prompt
        assert "Squeeze Score: Low" in prompt

    def test_bear_prompt_with_empty_options_report(self):
        """Bear prompt should render cleanly when options report is empty string."""
        from tradingagents.agents.researchers.bear_researcher import create_bear_researcher

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Response")
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

        # Should not have None, should still have the label
        assert "None" not in prompt
        assert "Options flow and short squeeze analysis:" in prompt
        # Other reports should still be present
        assert "Market data" in prompt
        assert "Fundamentals data" in prompt

    def test_trader_prompt_references_options_dimension(self):
        """Trader prompt should mention options as part of the analysis foundation."""
        from tradingagents.agents.trader.trader import create_trader

        mock_llm = MagicMock()

        with patch(
            "tradingagents.agents.trader.trader.invoke_structured_or_freetext",
            return_value="Decision: Buy",
        ) as mock_invoke:
            node = create_trader(mock_llm)
            state = {
                "company_of_interest": "AAPL",
                "investment_plan": "Buy recommendation based on all analysis.",
            }
            node(state)

            messages = mock_invoke.call_args[0][2]
            system_msg = messages[0]["content"].lower()
            user_msg = messages[1]["content"].lower()

            # System prompt mentions options
            assert "options" in system_msg
            # User prompt mentions options data
            assert "options" in user_msg
