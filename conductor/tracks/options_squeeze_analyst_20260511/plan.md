# Implementation Plan: Options Data & Short Squeeze Analyst

## Overview

This plan adds a 5th analyst agent to the TradingAgents pipeline in 6 phases, progressing from data layer through tools, agent, wiring, and integration. Each phase builds on the previous one and ends with a verification checkpoint. All tasks follow TDD: write a failing test first, implement the minimum code to pass, then refactor.

**Total estimated effort:** 12-16 hours across 6 phases.

---

## Phase 1: Options Data Fetchers (dataflow layer)

**Goal:** Implement the raw data fetching functions for options chains and related computations in a new `y_finance_options.py` module.

Tasks:

- [ ] Task 1.1: Create `tests/test_options_dataflows.py` with test for `get_options_expirations` — mock `yf.Ticker` to return a list of expiration date strings; assert formatted output includes header and dates. Then implement `tradingagents/dataflows/y_finance_options.py::get_options_expirations`. (TDD: Write test with mocked yfinance, implement function, verify format matches existing dataflow conventions.)

- [ ] Task 1.2: Test and implement `get_options_chain(ticker, expiration_date)` — mock `ticker.option_chain(date)` returning DataFrames with calls/puts columns (strike, lastPrice, bid, ask, volume, openInterest, impliedVolatility). Assert output is header + CSV string. Handle empty chain gracefully. (TDD: Red — test expects CSV output with header; Green — implement with `yf_retry`; Refactor — extract common formatting if needed.)

- [ ] Task 1.3: Test and implement `get_put_call_ratio(ticker)` — mock `ticker.options` (2 expirations) and `ticker.option_chain` for each. Assert volume-weighted and OI-weighted ratios are computed correctly. Test edge case: zero total call volume returns "insufficient data". (TDD: Red — test with known volumes expects specific ratios; Green — implement aggregation logic; Refactor.)

- [ ] Task 1.4: Test and implement `get_unusual_options_activity(ticker, volume_oi_threshold=3.0)` — mock chain data with some contracts having volume/OI > 3.0 and some below. Assert only contracts above threshold are returned, sorted by ratio descending, limited to 10. Test with no unusual activity returns informative message. (TDD: Red — test asserts top-N filtering; Green — implement; Refactor.)

- [ ] Task 1.5: Test and implement `get_iv_analysis(ticker)` — mock chain with known IV values across strikes. Assert ATM IV identification (strike nearest current price), OTM put vs OTM call IV skew calculation, and min/max IV range. Test sparse chain (few strikes) returns partial analysis. (TDD: Red — test expects specific ATM IV and skew direction; Green — implement; Refactor.)

- [ ] Verification: Run `pytest tests/test_options_dataflows.py -v` and confirm all 5+ tests pass with mocked yfinance. Manually verify one function against live yfinance for a liquid ticker (AAPL or SPY) to sanity-check format. [checkpoint marker]

---

## Phase 2: Short Squeeze Data Fetcher (dataflow layer)

**Goal:** Implement short interest and squeeze indicator functions using `ticker.info` fields.

Tasks:

- [ ] Task 2.1: Create `tests/test_squeeze_dataflows.py` with test for `get_short_squeeze_data(ticker)` — mock `ticker.info` returning dict with `shortPercentOfFloat`, `shortRatio`, `sharesShort`, `sharesShortPriorMonth`, `floatShares`, `sharesOutstanding`, `heldPercentInstitutions`, `heldPercentInsiders`. Assert all fields appear in output. Assert month-over-month change is computed correctly (e.g., shares short increased 15%). (TDD: Red — test expects formatted report with all metrics; Green — implement in `y_finance_options.py`; Refactor.)

- [ ] Task 2.2: Test squeeze score calculation — test with high-squeeze scenario (shortPercentOfFloat=0.35, shortRatio=8.5, rising short interest, low float) expects "Extreme" rating. Test with low-squeeze scenario (shortPercentOfFloat=0.02, shortRatio=1.0) expects "Low" rating. Test with partially missing fields (some None) still produces report without crashing. (TDD: Red — test expects specific ratings; Green — implement scoring logic; Refactor — extract thresholds to module-level constants.)

- [ ] Task 2.3: Test edge case — mock `ticker.info` returning empty dict or None. Assert function returns graceful "No short interest data available" message. (TDD: Red — test with empty info; Green — add guard clause; Refactor.)

- [ ] Verification: Run `pytest tests/test_squeeze_dataflows.py -v` and confirm all tests pass. [checkpoint marker]

---

## Phase 3: Interface Registration & Tool Definitions

**Goal:** Register new dataflow functions in the routing layer and create LangChain tool wrappers.

Tasks:

- [ ] Task 3.1: Test interface registration — in `tests/test_options_dataflows.py` (or new file `tests/test_options_interface.py`), test that `get_category_for_method("get_options_chain")` returns `"options_squeeze_data"`, and that `VENDOR_METHODS["get_options_chain"]["yfinance"]` points to the correct function. Repeat for all 6 new methods. Then update `interface.py`: add imports from `y_finance_options`, add `"options_squeeze_data"` to `TOOLS_CATEGORIES`, add all methods to `VENDOR_METHODS`. (TDD: Red — import and assert category/vendor mapping; Green — add registrations; Refactor.)

- [ ] Task 3.2: Update `default_config.py` — add `"options_squeeze_data": "yfinance"` to `data_vendors`. Test that `get_config()["data_vendors"]["options_squeeze_data"]` returns `"yfinance"`. (TDD: Red — test config key exists; Green — add to DEFAULT_CONFIG; Refactor.)

- [ ] Task 3.3: Create `tradingagents/agents/utils/options_squeeze_tools.py` — test that each `@tool` function exists, is callable, and has a docstring. Then implement 5 tools (`get_options_chain`, `get_put_call_ratio`, `get_unusual_options_activity`, `get_iv_analysis`, `get_short_squeeze_data`) all calling `route_to_vendor()`. Also add `get_options_expirations` as a 6th tool. (TDD: Red — import and assert tool attributes; Green — implement `@tool` wrappers; Refactor.)

- [ ] Task 3.4: Test tool routing end-to-end — mock the yfinance backend, call each tool function, assert it routes through `route_to_vendor` and returns expected data format. (TDD: Red — call tool, assert output; Green — verify routing works; Refactor.)

- [ ] Task 3.5: Update `agent_utils.py` — add imports of all new tools so they are available from the central utility module (matching how existing tools are imported there). Test import. (TDD: Red — test `from tradingagents.agents.utils.agent_utils import get_options_chain`; Green — add imports; Refactor.)

- [ ] Verification: Run `pytest tests/test_options_interface.py tests/test_options_dataflows.py -v`. Verify all tools can be imported from `agent_utils`. [checkpoint marker]

---

## Phase 4: Options & Squeeze Analyst Agent

**Goal:** Create the new analyst agent node following the existing analyst pattern.

Tasks:

- [ ] Task 4.1: Test agent creation — in `tests/test_options_squeeze_agent.py`, test that `create_options_squeeze_analyst(mock_llm)` returns a callable. Call it with a minimal state dict (messages, trade_date, company_of_interest). Assert result dict contains `"messages"` and `"options_squeeze_report"` keys. (TDD: Red — test callable and return shape; Green — create `tradingagents/agents/analysts/options_squeeze_analyst.py` with skeleton; Refactor.)

- [ ] Task 4.2: Test agent prompt construction — mock LLM to capture the prompt. Assert system message mentions options chain, put/call ratio, unusual activity, IV analysis, short squeeze. Assert tool names include all 6 tools. Assert current_date and instrument_context are injected. (TDD: Red — test prompt content assertions; Green — implement full prompt; Refactor.)

- [ ] Task 4.3: Test agent report extraction — mock LLM returning AIMessage with no tool_calls and content = "Options report...". Assert `options_squeeze_report` in result equals the content. Mock LLM returning AIMessage with tool_calls. Assert `options_squeeze_report` is empty string (tool loop continues). (TDD: Red — test both branches; Green — implement conditional report extraction; Refactor.)

- [ ] Task 4.4: Register agent in `__init__.py` — add `from .analysts.options_squeeze_analyst import create_options_squeeze_analyst` to `tradingagents/agents/__init__.py` and `__all__`. Test import from package. (TDD: Red — test import; Green — add to __init__.py; Refactor.)

- [ ] Verification: Run `pytest tests/test_options_squeeze_agent.py -v`. Confirm agent follows exact same pattern as fundamentals_analyst. [checkpoint marker]

---

## Phase 5: Graph Wiring & State Integration

**Goal:** Wire the new analyst into the LangGraph pipeline so it runs as part of the analyst chain.

Tasks:

- [ ] Task 5.1: Extend `AgentState` — add `options_squeeze_report` field. Test by instantiating state dict with the new field. (TDD: Red — test field exists in AgentState annotation; Green — add field; Refactor.)

- [ ] Task 5.2: Extend `Propagator.create_initial_state()` — add `"options_squeeze_report": ""` to initial state. Test that returned state includes the key. (TDD: Red — test key in initial state; Green — add to dict; Refactor.)

- [ ] Task 5.3: Add `should_continue_options_squeeze` to `ConditionalLogic` — follows exact same pattern as `should_continue_fundamentals`. Test with mock state containing tool_calls returns `"tools_options_squeeze"`, without returns `"Msg Clear Options_squeeze"`. (TDD: Red — test both branches; Green — implement method; Refactor.)

- [ ] Task 5.4: Extend `GraphSetup.setup_graph()` — add `"options_squeeze"` handling block (create analyst node, delete node, tool node). Update default `selected_analysts` parameter to include `"options_squeeze"`. Test by calling `setup_graph()` and verifying the workflow has the new nodes. (TDD: Red — test node names in compiled graph; Green — add wiring block; Refactor.)

- [ ] Task 5.5: Extend `TradingAgentsGraph._create_tool_nodes()` — add `"options_squeeze"` tool node with all 6 tools. Test the tool node dict has the new key. (TDD: Red — test key exists; Green — add ToolNode; Refactor.)

- [ ] Task 5.6: Update `TradingAgentsGraph.__init__` default `selected_analysts` — add `"options_squeeze"`. Update `_log_state()` to include `options_squeeze_report` in the JSON output. Test log output contains the new field. (TDD: Red — test default includes new analyst, test log dict; Green — update defaults and log method; Refactor.)

- [ ] Task 5.7: Test backward compatibility — instantiate `TradingAgentsGraph(selected_analysts=["market", "fundamentals"])` (without options_squeeze). Assert graph compiles and does not contain options_squeeze nodes. (TDD: Red — test exclusion; Green — verify existing conditional logic handles it; Refactor.)

- [ ] Verification: Run full test suite `pytest tests/ -v`. Verify no existing tests broken. Verify new analyst appears in default graph. [checkpoint marker]

---

## Phase 6: Downstream Prompt Updates & Integration

**Goal:** Update researcher, trader, and risk agent prompts to reference the new options/squeeze data dimension.

Tasks:

- [ ] Task 6.1: Update bull researcher prompt — add `options_squeeze_report` to the context variables. Add "Options flow and short squeeze analysis: {options_squeeze_report}" to the resources section. Test by checking the prompt string contains the new variable reference. (TDD: Red — test prompt includes "options_squeeze_report"; Green — update `bull_researcher.py`; Refactor.)

- [ ] Task 6.2: Update bear researcher prompt — same pattern as bull. Add options/squeeze report to context. Test prompt content. (TDD: Red — test prompt; Green — update `bear_researcher.py`; Refactor.)

- [ ] Task 6.3: Update trader prompt — add mention of options and short squeeze insights in the system message context. The trader receives the investment_plan which already synthesizes all reports, but the system prompt should acknowledge this data dimension exists. Test prompt content. (TDD: Red — test system message mentions options; Green — update `trader.py`; Refactor.)

- [ ] Task 6.4: Ensure graceful handling of empty report — test that when `options_squeeze_report` is empty string (analyst not selected), the bull/bear researcher prompts still read naturally (no "None" or error text in prompt). (TDD: Red — test with empty report; Green — verify f-string handles empty gracefully; Refactor.)

- [ ] Task 6.5: End-to-end smoke test — create an integration test that instantiates `TradingAgentsGraph` with all 5 analysts using fully mocked LLMs and mocked yfinance. Invoke `propagate("AAPL", "2026-05-09")` and assert the final state contains non-empty `options_squeeze_report` and `final_trade_decision`. (TDD: Red — test full pipeline; Green — verify all wiring works; Refactor.)

- [ ] Verification: Run `pytest tests/ -v --tb=short`. All tests pass. Run `python -c "from tradingagents.graph.trading_graph import TradingAgentsGraph; g = TradingAgentsGraph(); print('OK')"` with mocked LLM to verify import chain is clean. [checkpoint marker]

---

## File Change Summary

**New files:**
- `tradingagents/dataflows/y_finance_options.py` — options chain + squeeze data fetchers
- `tradingagents/agents/utils/options_squeeze_tools.py` — LangChain `@tool` wrappers
- `tradingagents/agents/analysts/options_squeeze_analyst.py` — analyst agent node
- `tests/test_options_dataflows.py` — dataflow unit tests
- `tests/test_squeeze_dataflows.py` — squeeze data unit tests
- `tests/test_options_interface.py` — interface registration tests
- `tests/test_options_squeeze_agent.py` — agent unit tests

**Modified files:**
- `tradingagents/dataflows/interface.py` — new category, vendor methods, imports
- `tradingagents/default_config.py` — new data_vendors entry
- `tradingagents/agents/utils/agent_utils.py` — new tool imports
- `tradingagents/agents/utils/agent_states.py` — new report field in AgentState
- `tradingagents/agents/__init__.py` — export new agent creator
- `tradingagents/graph/setup.py` — new analyst wiring block, updated default
- `tradingagents/graph/trading_graph.py` — new tool node, updated default, log update
- `tradingagents/graph/propagation.py` — new field in initial state
- `tradingagents/graph/conditional_logic.py` — new should_continue method
- `tradingagents/agents/researchers/bull_researcher.py` — prompt update
- `tradingagents/agents/researchers/bear_researcher.py` — prompt update
- `tradingagents/agents/trader/trader.py` — prompt update
