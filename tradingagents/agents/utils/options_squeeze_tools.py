from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_options_expirations(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Retrieve available options expiration dates for a given ticker symbol.
    Uses the configured options_squeeze_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A formatted list of available options expiration dates
    """
    return route_to_vendor("get_options_expirations", ticker)


@tool
def get_options_chain(
    ticker: Annotated[str, "ticker symbol of the company"],
    expiration_date: Annotated[str, "options expiration date (YYYY-MM-DD)"],
) -> str:
    """
    Retrieve the options chain (calls and puts) for a given ticker and expiration date.
    Uses the configured options_squeeze_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
        expiration_date (str): Options expiration date in YYYY-MM-DD format
    Returns:
        str: A formatted report containing calls and puts chain data
    """
    return route_to_vendor("get_options_chain", ticker, expiration_date)


@tool
def get_put_call_ratio(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Compute volume-weighted and open-interest-weighted put/call ratios for a ticker.
    Uses the configured options_squeeze_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A formatted report with put/call ratios and sentiment interpretation
    """
    return route_to_vendor("get_put_call_ratio", ticker)


@tool
def get_unusual_options_activity(
    ticker: Annotated[str, "ticker symbol of the company"],
    volume_oi_threshold: Annotated[float, "minimum volume/OI ratio to flag as unusual"] = 3.0,
) -> str:
    """
    Identify options contracts with unusually high volume relative to open interest.
    Uses the configured options_squeeze_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
        volume_oi_threshold (float): Minimum volume/OI ratio to flag (default 3.0)
    Returns:
        str: A formatted report of unusual options activity sorted by volume/OI ratio
    """
    return route_to_vendor("get_unusual_options_activity", ticker, volume_oi_threshold)


@tool
def get_iv_analysis(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Analyze implied volatility across the options chain: ATM IV, skew, and range.
    Uses the configured options_squeeze_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A formatted IV analysis report with ATM IV, skew, and range data
    """
    return route_to_vendor("get_iv_analysis", ticker)


@tool
def get_short_squeeze_data(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Retrieve short interest metrics and compute a squeeze potential score.
    Uses the configured options_squeeze_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A formatted report with short interest data and squeeze potential rating
    """
    return route_to_vendor("get_short_squeeze_data", ticker)
