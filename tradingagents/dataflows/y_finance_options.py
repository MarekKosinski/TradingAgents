"""Options chain and short squeeze data fetchers backed by yfinance.

All functions return formatted strings following the same convention as
``y_finance.py``: a ``# Header`` section followed by the data body.
"""

from datetime import datetime
from typing import Annotated

import pandas as pd
import yfinance as yf

from .stockstats_utils import yf_retry

# ---------------------------------------------------------------------------
# Squeeze-score thresholds (module-level constants)
# ---------------------------------------------------------------------------

_SQUEEZE_EXTREME_SHORT_PCT = 0.30
_SQUEEZE_HIGH_SHORT_PCT = 0.20
_SQUEEZE_MEDIUM_SHORT_PCT = 0.10
_SQUEEZE_ELEVATED_DAYS_TO_COVER = 5.0

# ---------------------------------------------------------------------------
# Maximum near-term expirations to consider for aggregated metrics
# ---------------------------------------------------------------------------

_MAX_NEAR_TERM_EXPIRATIONS = 4


# ---------------------------------------------------------------------------
# Phase 1: Options Data Fetchers
# ---------------------------------------------------------------------------

def get_options_expirations(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Return available options expiration dates for *ticker*."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        expirations = yf_retry(lambda: ticker_obj.options)

        if not expirations:
            return f"No options data available for '{ticker.upper()}' — this ticker may not have listed options."

        lines = [f"  {i + 1}. {exp}" for i, exp in enumerate(expirations)]

        header = f"# Options Expirations for {ticker.upper()}\n"
        header += f"# {len(expirations)} expiration date(s) available\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error retrieving options expirations for {ticker}: {str(e)}"


def get_options_chain(
    ticker: Annotated[str, "ticker symbol of the company"],
    expiration_date: Annotated[str, "options expiration date (YYYY-MM-DD)"],
) -> str:
    """Return calls and puts chain for *ticker* at a given *expiration_date*."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        chain = yf_retry(lambda: ticker_obj.option_chain(expiration_date))

        calls = chain.calls
        puts = chain.puts

        if calls.empty and puts.empty:
            return f"No options chain data available for '{ticker.upper()}' at expiration {expiration_date}."

        header = f"# Options Chain for {ticker.upper()} — Expiration: {expiration_date}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        sections = []
        if not calls.empty:
            sections.append(f"## CALLS ({len(calls)} contracts)\n{calls.to_csv(index=False)}")
        if not puts.empty:
            sections.append(f"## PUTS ({len(puts)} contracts)\n{puts.to_csv(index=False)}")

        return header + "\n\n".join(sections)

    except Exception as e:
        return f"Error retrieving options chain for {ticker}: {str(e)}"


def get_put_call_ratio(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Compute volume-weighted and OI-weighted put/call ratios across near-term expirations."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        expirations = yf_retry(lambda: ticker_obj.options)

        if not expirations:
            return f"No options data available for '{ticker.upper()}' — insufficient data to compute put/call ratio."

        # Use up to _MAX_NEAR_TERM_EXPIRATIONS nearest expirations
        near_exps = expirations[:_MAX_NEAR_TERM_EXPIRATIONS]

        total_call_volume = 0
        total_put_volume = 0
        total_call_oi = 0
        total_put_oi = 0

        for exp in near_exps:
            try:
                chain = yf_retry(lambda exp=exp: ticker_obj.option_chain(exp))
                total_call_volume += chain.calls["volume"].fillna(0).sum()
                total_put_volume += chain.puts["volume"].fillna(0).sum()
                total_call_oi += chain.calls["openInterest"].fillna(0).sum()
                total_put_oi += chain.puts["openInterest"].fillna(0).sum()
            except Exception:
                continue

        header = f"# Put/Call Ratio Analysis for {ticker.upper()}\n"
        header += f"# Based on {len(near_exps)} near-term expiration(s)\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        lines = []

        # Volume-weighted ratio
        if total_call_volume > 0:
            vol_ratio = total_put_volume / total_call_volume
            lines.append(f"Volume-Weighted Put/Call Ratio: {vol_ratio:.3f}")
            lines.append(f"  Total Put Volume: {int(total_put_volume)}")
            lines.append(f"  Total Call Volume: {int(total_call_volume)}")
        else:
            lines.append("Volume-Weighted Put/Call Ratio: insufficient data (zero call volume)")

        lines.append("")

        # OI-weighted ratio
        if total_call_oi > 0:
            oi_ratio = total_put_oi / total_call_oi
            lines.append(f"Open Interest Put/Call Ratio: {oi_ratio:.3f}")
            lines.append(f"  Total Put OI: {int(total_put_oi)}")
            lines.append(f"  Total Call OI: {int(total_call_oi)}")
        else:
            lines.append("Open Interest Put/Call Ratio: insufficient data (zero call OI)")

        lines.append("")

        # Interpretation
        if total_call_volume > 0:
            vol_ratio = total_put_volume / total_call_volume
            if vol_ratio > 1.0:
                lines.append(f"Interpretation: BEARISH — put/call volume ratio {vol_ratio:.2f} > 1.0 indicates elevated put buying / bearish sentiment.")
            elif vol_ratio < 0.7:
                lines.append(f"Interpretation: BULLISH — put/call volume ratio {vol_ratio:.2f} < 0.7 indicates elevated call buying / bullish sentiment.")
            else:
                lines.append(f"Interpretation: NEUTRAL — put/call volume ratio {vol_ratio:.2f} is within normal range (0.7-1.0).")
        else:
            lines.append("Interpretation: insufficient data to determine sentiment.")

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error computing put/call ratio for {ticker}: {str(e)}"


def get_unusual_options_activity(
    ticker: Annotated[str, "ticker symbol of the company"],
    volume_oi_threshold: Annotated[float, "minimum volume/OI ratio to flag as unusual"] = 3.0,
) -> str:
    """Identify options contracts with unusually high volume relative to open interest."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        expirations = yf_retry(lambda: ticker_obj.options)

        if not expirations:
            return f"No options data available for '{ticker.upper()}' — cannot scan for unusual activity."

        near_exps = expirations[:_MAX_NEAR_TERM_EXPIRATIONS]
        unusual = []

        for exp in near_exps:
            try:
                chain = yf_retry(lambda exp=exp: ticker_obj.option_chain(exp))
                for option_type, df in [("Call", chain.calls), ("Put", chain.puts)]:
                    if df.empty:
                        continue
                    for _, row in df.iterrows():
                        vol = row.get("volume", 0) or 0
                        oi = row.get("openInterest", 0) or 0
                        if oi > 0 and vol / oi > volume_oi_threshold:
                            unusual.append({
                                "expiration": exp,
                                "type": option_type,
                                "strike": row.get("strike", 0),
                                "volume": int(vol),
                                "openInterest": int(oi),
                                "vol_oi_ratio": round(vol / oi, 2),
                                "impliedVolatility": row.get("impliedVolatility", None),
                            })
            except Exception:
                continue

        header = f"# Unusual Options Activity for {ticker.upper()}\n"
        header += f"# Threshold: Volume/OI > {volume_oi_threshold}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        if not unusual:
            return header + f"No unusual options activity detected for {ticker.upper()} (no contracts with volume/OI > {volume_oi_threshold})."

        # Sort by ratio descending, limit to top 10
        unusual.sort(key=lambda x: x["vol_oi_ratio"], reverse=True)
        top = unusual[:10]

        lines = [f"Top {len(top)} Unusual Contracts (sorted by Volume/OI ratio):\n"]
        for i, item in enumerate(top, 1):
            iv_str = f"{item['impliedVolatility']:.2%}" if item["impliedVolatility"] is not None else "N/A"
            lines.append(
                f"  {i}. {item['type']} {item['strike']} exp {item['expiration']} — "
                f"Vol: {item['volume']}, OI: {item['openInterest']}, "
                f"Vol/OI: {item['vol_oi_ratio']}, IV: {iv_str}"
            )

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error scanning unusual options activity for {ticker}: {str(e)}"


def get_iv_analysis(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Analyze implied volatility: ATM IV, skew, and range for nearest expiration."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        expirations = yf_retry(lambda: ticker_obj.options)

        if not expirations:
            return f"No options data available for '{ticker.upper()}' — cannot perform IV analysis."

        info = yf_retry(lambda: ticker_obj.info)
        current_price = (info or {}).get("currentPrice") or (info or {}).get("regularMarketPrice")

        # Use nearest expiration
        nearest_exp = expirations[0]
        chain = yf_retry(lambda: ticker_obj.option_chain(nearest_exp))

        calls = chain.calls
        puts = chain.puts

        if calls.empty and puts.empty:
            return f"No options chain data available for '{ticker.upper()}' — cannot perform IV analysis."

        header = f"# IV Analysis for {ticker.upper()} — Nearest Expiration: {nearest_exp}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        lines = []

        if current_price:
            lines.append(f"Current Price: ${current_price:.2f}\n")

        # --- ATM IV ---
        atm_call_iv = None
        atm_put_iv = None

        if not calls.empty and current_price:
            calls_valid = calls.dropna(subset=["impliedVolatility"])
            if not calls_valid.empty:
                atm_idx = (calls_valid["strike"] - current_price).abs().idxmin()
                atm_call_iv = calls_valid.loc[atm_idx, "impliedVolatility"]
                atm_strike = calls_valid.loc[atm_idx, "strike"]
                lines.append(f"ATM Call IV: {atm_call_iv:.2%} (strike {atm_strike})")

        if not puts.empty and current_price:
            puts_valid = puts.dropna(subset=["impliedVolatility"])
            if not puts_valid.empty:
                atm_idx = (puts_valid["strike"] - current_price).abs().idxmin()
                atm_put_iv = puts_valid.loc[atm_idx, "impliedVolatility"]
                atm_strike = puts_valid.loc[atm_idx, "strike"]
                lines.append(f"ATM Put IV: {atm_put_iv:.2%} (strike {atm_strike})")

        if atm_call_iv is not None and atm_put_iv is not None:
            avg_atm = (atm_call_iv + atm_put_iv) / 2
            lines.append(f"ATM Average IV: {avg_atm:.2%}")

        lines.append("")

        # --- IV Skew (OTM puts vs OTM calls) ---
        if not calls.empty and not puts.empty and current_price:
            otm_calls = calls[calls["strike"] > current_price].dropna(subset=["impliedVolatility"])
            otm_puts = puts[puts["strike"] < current_price].dropna(subset=["impliedVolatility"])

            if not otm_calls.empty and not otm_puts.empty:
                avg_otm_call_iv = otm_calls["impliedVolatility"].mean()
                avg_otm_put_iv = otm_puts["impliedVolatility"].mean()
                skew = avg_otm_put_iv - avg_otm_call_iv

                lines.append(f"IV Skew (OTM Puts - OTM Calls): {skew:+.4f}")
                lines.append(f"  Avg OTM Put IV: {avg_otm_put_iv:.2%}")
                lines.append(f"  Avg OTM Call IV: {avg_otm_call_iv:.2%}")

                if skew > 0.05:
                    lines.append("  Interpretation: Significant put skew — elevated hedging demand / downside fear.")
                elif skew > 0:
                    lines.append("  Interpretation: Mild put skew — normal market conditions.")
                elif skew < -0.05:
                    lines.append("  Interpretation: Negative skew (call premium) — unusual upside speculation.")
                else:
                    lines.append("  Interpretation: Roughly flat skew.")
            else:
                lines.append("IV Skew: insufficient OTM data for skew calculation.")
        else:
            lines.append("IV Skew: insufficient data for skew calculation.")

        lines.append("")

        # --- IV Range ---
        all_iv = pd.concat([
            calls["impliedVolatility"].dropna() if not calls.empty else pd.Series(dtype=float),
            puts["impliedVolatility"].dropna() if not puts.empty else pd.Series(dtype=float),
        ])

        if not all_iv.empty:
            lines.append(f"IV Range: Min {all_iv.min():.2%} — Max {all_iv.max():.2%}")
            lines.append(f"IV Mean: {all_iv.mean():.2%}")
            lines.append(f"IV Median: {all_iv.median():.2%}")
        else:
            lines.append("IV Range: no IV data available.")

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error performing IV analysis for {ticker}: {str(e)}"


# ---------------------------------------------------------------------------
# Phase 2: Short Squeeze Data
# ---------------------------------------------------------------------------

def _compute_squeeze_score(
    short_pct: float | None,
    short_ratio: float | None,
    shares_short: int | None,
    shares_short_prior: int | None,
) -> str:
    """Return a qualitative squeeze rating: Low / Medium / High / Extreme.

    Scoring logic:
    - shortPercentOfFloat > 30% -> Extreme
    - shortPercentOfFloat > 20% -> High
    - shortPercentOfFloat > 10% -> Medium
    - otherwise -> Low

    Modifiers that can elevate the score by one level:
    - days-to-cover (shortRatio) > 5
    - rising short interest (MoM increase)
    """
    # Base score from short percent of float
    if short_pct is None:
        return "Unknown"

    if short_pct > _SQUEEZE_EXTREME_SHORT_PCT:
        level = 3  # Extreme
    elif short_pct > _SQUEEZE_HIGH_SHORT_PCT:
        level = 2  # High
    elif short_pct > _SQUEEZE_MEDIUM_SHORT_PCT:
        level = 1  # Medium
    else:
        level = 0  # Low

    # Modifier: elevated days-to-cover
    if short_ratio is not None and short_ratio > _SQUEEZE_ELEVATED_DAYS_TO_COVER:
        level = min(level + 1, 3)

    # Modifier: rising short interest
    if (
        shares_short is not None
        and shares_short_prior is not None
        and shares_short_prior > 0
        and shares_short > shares_short_prior
    ):
        level = min(level + 1, 3)

    labels = {0: "Low", 1: "Medium", 2: "High", 3: "Extreme"}
    return labels[level]


def get_short_squeeze_data(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Fetch short interest metrics and compute a squeeze score."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        info = yf_retry(lambda: ticker_obj.info)

        if not info:
            return f"No short interest data available for '{ticker.upper()}'."

        short_pct = info.get("shortPercentOfFloat")
        short_ratio = info.get("shortRatio")
        shares_short = info.get("sharesShort")
        shares_short_prior = info.get("sharesShortPriorMonth")
        float_shares = info.get("floatShares")
        shares_outstanding = info.get("sharesOutstanding")
        inst_pct = info.get("heldPercentInstitutions")
        insider_pct = info.get("heldPercentInsiders")

        # Check if we have any meaningful data at all
        key_fields = [short_pct, short_ratio, shares_short]
        if all(v is None for v in key_fields):
            return f"No short interest data available for '{ticker.upper()}'."

        header = f"# Short Squeeze Analysis for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        lines = []

        # Short interest metrics
        if short_pct is not None:
            lines.append(f"Short % of Float: {short_pct:.2%}")
        else:
            lines.append("Short % of Float: N/A")

        if short_ratio is not None:
            lines.append(f"Short Ratio (Days to Cover): {short_ratio}")
        else:
            lines.append("Short Ratio (Days to Cover): N/A")

        if shares_short is not None:
            lines.append(f"Shares Short: {shares_short:,}")
        else:
            lines.append("Shares Short: N/A")

        if shares_short_prior is not None:
            lines.append(f"Shares Short (Prior Month): {shares_short_prior:,}")
        else:
            lines.append("Shares Short (Prior Month): N/A")

        lines.append("")

        # Month-over-month change
        if shares_short is not None and shares_short_prior is not None and shares_short_prior > 0:
            mom_change = (shares_short - shares_short_prior) / shares_short_prior
            direction = "increase" if mom_change > 0 else "decrease"
            lines.append(f"MoM Short Interest Change: {mom_change:+.2%} ({direction})")
            if mom_change > 0:
                lines.append("  Short interest is RISING — shorts are adding positions.")
            else:
                lines.append("  Short interest is DECLINING — shorts are covering.")
        else:
            lines.append("MoM Short Interest Change: N/A")

        lines.append("")

        # Float and shares
        if float_shares is not None:
            lines.append(f"Float Shares: {float_shares:,}")
        if shares_outstanding is not None:
            lines.append(f"Shares Outstanding: {shares_outstanding:,}")

        lines.append("")

        # Institutional and insider holdings
        if inst_pct is not None:
            lines.append(f"Institutional Holdings: {inst_pct:.2%}")
        if insider_pct is not None:
            lines.append(f"Insider Holdings: {insider_pct:.2%}")

        lines.append("")

        # Squeeze score
        score = _compute_squeeze_score(short_pct, short_ratio, shares_short, shares_short_prior)
        lines.append(f"Squeeze Potential Score: {score}")

        if score == "Extreme":
            lines.append("  WARNING: Extremely high short interest. Conditions favorable for a short squeeze if positive catalyst occurs.")
        elif score == "High":
            lines.append("  ELEVATED: High short interest with potential for squeeze. Monitor for catalysts and volume spikes.")
        elif score == "Medium":
            lines.append("  MODERATE: Moderate short interest. Some squeeze potential but not a primary thesis driver.")
        else:
            lines.append("  LOW: Minimal short squeeze risk. Short interest is at normal levels.")

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error retrieving short squeeze data for {ticker}: {str(e)}"
