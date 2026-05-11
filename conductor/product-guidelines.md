# Product Guidelines

## Voice & Tone
- Agent reports should be professional, analytical, and data-driven
- No hype or emotional language in trading recommendations
- Clear reasoning chains: data → interpretation → recommendation

## Design Standards
- New data tools must follow the existing vendor-abstraction pattern (interface.py routing)
- Agent tools return formatted markdown strings for LLM consumption
- All data retrieval must support both yfinance and Alpha Vantage where possible
- New analysts/tools should integrate into the existing LangGraph pipeline without breaking the flow

## Code Conventions
- Python 3.10+ compatible
- Follow existing patterns: tools in `agents/utils/*_tools.py`, data fetching in `dataflows/`
- New tool functions must be registered via the interface layer
- Configuration-driven: new features should be toggleable via `default_config.py`
