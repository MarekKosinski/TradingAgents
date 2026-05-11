# Tech Stack

## Language
- Python 3.10+ (tested on 3.14)

## Core Framework
- LangGraph — agent orchestration and state machine
- LangChain — LLM client abstraction (langchain-openai, langchain-anthropic, langchain-google-genai)

## Data
- yfinance — stock prices, fundamentals, news, financials (primary, free)
- Alpha Vantage — alternative data vendor (requires API key)
- stockstats — technical indicator calculation
- pandas — data manipulation

## Infrastructure
- SQLite — checkpoint persistence (langgraph-checkpoint-sqlite)
- Redis — optional caching
- Docker — containerized deployment

## CLI
- Typer + Rich + Questionary — interactive terminal UI

## Testing
- pytest (test.py and tests/ directory)

## Package Management
- pip / setuptools (pyproject.toml)
- uv (uv.lock present)
