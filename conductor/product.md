# Product Guide: TradingAgents

## Overview
TradingAgents is a multi-agent LLM-powered financial trading framework that mirrors real-world trading firm dynamics. Specialized agents (analysts, researchers, traders, risk managers) collaborate to evaluate market conditions and produce buy/hold/sell decisions.

## Target Users
- Quantitative traders and retail investors wanting AI-assisted analysis
- Financial researchers studying LLM-based decision-making
- Developers building automated trading pipelines

## Problems Solved
- Manual stock analysis is time-consuming and biased toward single perspectives
- Retail investors lack access to multi-perspective institutional-style analysis
- Existing tools don't combine fundamentals, technicals, sentiment, and risk management in a structured workflow

## Key Features
- Multi-agent pipeline: 4 analysts → bull/bear researchers → trader → risk team → portfolio manager
- Multi-provider LLM support (OpenAI, Anthropic, Google, xAI, DeepSeek, Ollama, OpenRouter, etc.)
- Data from yfinance (free) or Alpha Vantage
- Decision memory with reflection on past trades
- Checkpoint/resume for crash recovery
- Interactive CLI and Python API

## Current Gaps
- No options data (chains, IV, Greeks, unusual flow)
- No short interest or squeeze mechanics
- No institutional ownership or dark pool data
- No float or shares outstanding analysis
- Limited to basic technicals (MA, RSI, MACD, Bollinger, ATR, MFI)

## Success Metrics
- Accuracy of buy/sell signals vs realized returns
- Coverage of data dimensions considered in analysis
- Reliability of pipeline (no crashes on free-tier models)
