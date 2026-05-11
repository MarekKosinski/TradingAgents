# Specification: Options Data & Short Squeeze Analyst

## Overview

Add a 5th analyst agent ("Options & Squeeze Analyst") to the TradingAgents multi-agent pipeline. This agent uses new LangChain tools backed by yfinance to fetch options chain data, compute options-derived signals (put/call ratio, unusual activity, implied volatility analysis), and evaluate short squeeze potential (short interest, days to cover, float analysis). The new agent runs in parallel with the existing 4 analysts, and its report flows into the existing researcher debate, trader, and risk management stages.

## Background

TradingAgents currently covers technicals, fundamentals, news, and social sentiment through 4 analyst agents. The product gap analysis (product.md) explicitly identifies missing coverage for:
- Options data (chains, IV, Greeks, unusual flow)
- Short interest and squeeze mechanics
- Float and shares outstanding analysis

All required data is available from yfinance at no cost, using `ticker.options`, `ticker.option_chain(date)`, and fields within `ticker.info`. No new API keys or paid services are needed.

## Functional Requirements

### FR-1: Options Chain Data Fetcher (dataflow layer)
**Description:** Add functions to `tradingagents/dataflows/y_finance.py` that fetch options chain data from yfinance.
**Acceptance Criteria:**
- `get_options_chain(ticker, expiration_date)` returns formatted string with calls and puts (strike, lastPrice, bid, ask, volume, openInterest, impliedVolatility)
- `get_options_expirations(ticker)` returns list of available expiration dates
- Handles tickers with no options (e.g., some ETFs, international) gracefully with informative message
- Uses existing `yf_retry` pattern for resilience
- Output format matches existing dataflow conventions (header comment + CSV/table string)
**Priority:** P0

### FR-2: Put/Call Ratio Calculator (dataflow layer)
**Description:** Compute put/call ratio from options chain data.
**Acceptance Criteria:**
- `get_put_call_ratio(ticker)` computes volume-weighted and open-interest-weighted P/C ratios across all near-term expirations
- Returns formatted string with both ratios and interpretation guidance (>1.0 bearish, <0.7 bullish, etc.)
- Handles missing/zero volume gracefully (returns "insufficient data" message)
**Priority:** P0

### FR-3: Unusual Options Activity Detector (dataflow layer)
**Description:** Identify options contracts with abnormally high volume relative to open interest.
**Acceptance Criteria:**
- `get_unusual_options_activity(ticker, volume_oi_threshold)` returns contracts where volume/openInterest exceeds threshold (default 3.0)
- Returns top 10 unusual contracts sorted by volume/OI ratio
- Includes strike, expiration, type (call/put), volume, OI, implied volatility
- Returns informative message when no unusual activity detected
**Priority:** P0

### FR-4: Implied Volatility Analysis (dataflow layer)
**Description:** Analyze IV across the options chain to identify skew and term structure signals.
**Acceptance Criteria:**
- `get_iv_analysis(ticker)` returns IV summary: ATM IV for nearest expiration, IV skew (OTM puts vs OTM calls), IV rank relative to chain range
- Includes interpretation text (high IV = expensive options / fear, skew toward puts = hedging demand)
- Gracefully handles chains with sparse data
**Priority:** P1

### FR-5: Short Interest & Squeeze Indicators (dataflow layer)
**Description:** Fetch short interest data from yfinance `ticker.info` and compute squeeze indicators.
**Acceptance Criteria:**
- `get_short_squeeze_data(ticker)` returns formatted report with:
  - Short percent of float (`shortPercentOfFloat`)
  - Short ratio / days to cover (`shortRatio`)
  - Shares short vs prior month (`sharesShort`, `sharesShortPriorMonth`) with month-over-month change
  - Float shares and shares outstanding
  - Institutional and insider holdings percentages
- Computes squeeze score: qualitative rating (Low/Medium/High/Extreme) based on short% > 20%, days-to-cover > 5, rising short interest, low float
- Handles missing fields gracefully (yfinance does not always populate all fields)
**Priority:** P0

### FR-6: Interface Layer Registration
**Description:** Register new dataflow functions in `tradingagents/dataflows/interface.py`.
**Acceptance Criteria:**
- New category `"options_squeeze_data"` added to `TOOLS_CATEGORIES` with all new tool names
- All new methods added to `VENDOR_METHODS` with yfinance implementations
- `default_config.py` `data_vendors` includes `"options_squeeze_data": "yfinance"`
- Vendor routing works correctly for all new methods
**Priority:** P0

### FR-7: LangChain Tool Definitions
**Description:** Create `tradingagents/agents/utils/options_squeeze_tools.py` with `@tool`-decorated functions.
**Acceptance Criteria:**
- `get_options_chain` tool with ticker and expiration_date parameters
- `get_put_call_ratio` tool with ticker parameter
- `get_unusual_options_activity` tool with ticker and optional threshold parameter
- `get_iv_analysis` tool with ticker parameter
- `get_short_squeeze_data` tool with ticker parameter
- All tools route through `route_to_vendor()` following existing pattern
- All tools have proper docstrings matching existing tool documentation style
**Priority:** P0

### FR-8: Options & Squeeze Analyst Agent
**Description:** Create `tradingagents/agents/analysts/options_squeeze_analyst.py` with a new analyst node.
**Acceptance Criteria:**
- `create_options_squeeze_analyst(llm)` follows exact same pattern as `create_fundamentals_analyst`
- System prompt instructs the agent to:
  - First check options expirations availability
  - Analyze put/call ratios for sentiment
  - Scan for unusual options activity
  - Assess implied volatility levels and skew
  - Evaluate short squeeze potential
  - Synthesize into actionable report with risk assessment
- Returns `{"messages": [result], "options_squeeze_report": report}`
- Produces markdown table summary at end of report (matching other analyst conventions)
**Priority:** P0

### FR-9: Agent State Extension
**Description:** Add new report field to `AgentState`.
**Acceptance Criteria:**
- `options_squeeze_report: Annotated[str, "Report from the Options & Squeeze Analyst"]` added to `AgentState`
- Initial state in `Propagator.create_initial_state()` includes `"options_squeeze_report": ""`
- State logged in `_log_state()` includes `options_squeeze_report`
**Priority:** P0

### FR-10: Graph Wiring
**Description:** Wire the new analyst into the LangGraph pipeline.
**Acceptance Criteria:**
- `"options_squeeze"` is a valid entry in `selected_analysts` parameter
- Default `selected_analysts` updated to include `"options_squeeze"` (5 analysts total)
- New analyst runs in the sequential analyst chain (after fundamentals, before researchers)
- Tool node created with all 5 options/squeeze tools
- Conditional logic `should_continue_options_squeeze` method added
- Works correctly when `"options_squeeze"` is excluded from `selected_analysts`
**Priority:** P0

### FR-11: Researcher/Trader Prompt Updates
**Description:** Update downstream agents to reference the new options/squeeze report.
**Acceptance Criteria:**
- Bull and bear researcher prompts include `options_squeeze_report` in their context
- Researcher prompts mention options flow and short squeeze data as available dimensions
- Trader prompt mentions options/squeeze insights as part of the analysis foundation
- When options_squeeze analyst is not selected, the empty report does not confuse downstream agents
**Priority:** P1

## Non-Functional Requirements

### NFR-1: Performance
- Options chain fetching must not add more than 5 seconds per ticker (yfinance is cached per session)
- Agent should make at most 6 tool calls to avoid LLM token waste
- No new external dependencies beyond what yfinance already provides

### NFR-2: Backwards Compatibility
- Existing pipelines without `"options_squeeze"` in `selected_analysts` must work identically
- Saved state JSON format must be additive only (new field, no changes to existing fields)
- Default config changes must be backwards compatible

### NFR-3: Testing
- All dataflow functions must have unit tests with mocked yfinance responses
- Tool definitions must have integration-style tests verifying routing
- Agent node must have tests verifying prompt construction and state updates
- Graph wiring must have tests verifying the new analyst appears in the compiled graph
- Coverage target: 80% for all new code

### NFR-4: Error Resilience
- All new dataflow functions must handle yfinance returning None/empty gracefully
- Agent must produce a useful report even if some tools return error messages
- Missing options data (common for small-cap, international stocks) must not crash the pipeline

## User Stories

### US-1: Options-Aware Analysis
**As** a trader using TradingAgents,
**I want** the system to analyze options flow and short interest alongside technicals and fundamentals,
**So that** I get a more complete picture of market positioning before making a trade decision.

**Given** I run TradingAgents for ticker "GME"
**When** the pipeline executes with the default analyst configuration
**Then** the final decision includes consideration of options activity and short squeeze potential

### US-2: Selective Analyst Configuration
**As** a developer integrating TradingAgents,
**I want** to optionally exclude the options/squeeze analyst,
**So that** I can run faster pipelines when I only need traditional analysis dimensions.

**Given** I create `TradingAgentsGraph(selected_analysts=["market", "fundamentals"])`
**When** the pipeline executes
**Then** only market and fundamentals analysts run, and no options/squeeze data is fetched

### US-3: Graceful Degradation for Unsupported Tickers
**As** a user analyzing international or small-cap stocks,
**I want** the options/squeeze analyst to handle missing data gracefully,
**So that** the pipeline completes successfully even when options data is unavailable.

**Given** I analyze a ticker with no listed options (e.g., some foreign ADRs)
**When** the options/squeeze analyst runs
**Then** it reports "no options data available" and still provides short interest analysis from ticker.info

## Technical Considerations

- **Dataflow pattern:** New functions go in `y_finance.py` (or a new `y_finance_options.py` if cleaner), registered in `interface.py` with `VENDOR_METHODS` and `TOOLS_CATEGORIES`
- **Tool pattern:** New file `options_squeeze_tools.py` with `@tool` decorators calling `route_to_vendor()`
- **Agent pattern:** New file `options_squeeze_analyst.py` following `fundamentals_analyst.py` template exactly
- **Graph wiring:** Extends `setup.py` analyst selection with new `"options_squeeze"` key; extends `conditional_logic.py` with `should_continue_options_squeeze`
- **State:** Single new field `options_squeeze_report` in `AgentState`; initialized empty in `Propagator`
- **No Greeks computation:** yfinance does not provide Greeks; computing Black-Scholes is out of scope for v1. The IV data from the chain is sufficient.
- **Alpha Vantage:** No options data equivalent in Alpha Vantage integration. The new category only has yfinance implementation. This is acceptable per the vendor fallback pattern.

## Out of Scope

- Greeks calculation (Black-Scholes, binomial) — would require `scipy` or `py_vollib` dependency
- Historical options data / IV time series — yfinance only provides current snapshot
- Dark pool data — requires paid data feeds
- Options strategy suggestions (straddle, strangle, spread) — analysis only, not strategy
- Real-time streaming options data
- Alpha Vantage options data integration (not available in their free/standard tiers)

## Open Questions

1. **File organization:** Should options dataflow functions go into `y_finance.py` (co-located with existing functions) or a new `y_finance_options.py` (cleaner separation)? Recommendation: new file for separation of concerns.
2. **Squeeze scoring thresholds:** The qualitative squeeze score thresholds (Short% > 20% = High, etc.) are based on common market conventions. Should these be configurable? Recommendation: hardcode sensible defaults for v1, make configurable later if needed.
3. **Default analyst list:** Adding a 5th analyst increases token cost and latency. Should `options_squeeze` be in the default list or opt-in? Recommendation: include in default list since the product gap analysis identifies this as a key missing dimension.
