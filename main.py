import json
import os

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use Claude Code's OAuth token from subscription (no API billing)
creds_path = os.path.expanduser("~/.claude/.credentials.json")
with open(creds_path) as f:
    creds = json.load(f)
os.environ["ANTHROPIC_API_KEY"] = creds["claudeAiOauth"]["accessToken"]

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "anthropic"
config["deep_think_llm"] = "claude-sonnet-4-20250514"
config["quick_think_llm"] = "claude-sonnet-4-20250514"
config["max_debate_rounds"] = 1

# Configure data vendors (default uses yfinance, no extra API keys needed)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",           # Options: alpha_vantage, yfinance
    "technical_indicators": "yfinance",      # Options: alpha_vantage, yfinance
    "fundamental_data": "yfinance",          # Options: alpha_vantage, yfinance
    "news_data": "yfinance",                 # Options: alpha_vantage, yfinance
}

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("OPEN", "2026-05-04")
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
