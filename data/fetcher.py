"""
data/fetcher.py
───────────────
Downloads adjusted-close prices from Yahoo Finance via yfinance.
Returns a clean pandas DataFrame indexed by date.
"""

from __future__ import annotations

import datetime
from typing import List

import pandas as pd
import yfinance as yf

from config import LOOKBACK_DAYS, SKIP_DAYS, DOWNLOAD_BUFFER

# Calendar-day offsets for each preset performance-chart period.
# "ytd" and "max" are handled separately (they need today's date / a fixed
# floor rather than a fixed offset).
_PERIOD_OFFSETS = {
    "1mo": pd.DateOffset(months=1),
    "3mo": pd.DateOffset(months=3),
    "6mo": pd.DateOffset(months=6),
    "1y":  pd.DateOffset(years=1),
    "3y":  pd.DateOffset(years=3),
    "5y":  pd.DateOffset(years=5),
    "10y": pd.DateOffset(years=10),
}


def _required_calendar_days(extra_months: int = 0) -> int:
    """
    Convert trading-day requirements to a calendar-day window.
    Markets are open ~252 days / year ≈ 5/7 of calendar days.
    Add buffer so we always have enough rows even after holidays / gaps.

    extra_months: additional calendar months to prepend to the window,
                  used by compute_history so every requested month-start
                  has a full 12-month lookback available before it.
    """
    trading_days_needed = LOOKBACK_DAYS + SKIP_DAYS + DOWNLOAD_BUFFER
    calendar_days = int(trading_days_needed * (7 / 5)) + 60
    calendar_days += extra_months * 31   # 31 days/month is a safe ceiling
    return calendar_days


def _shape_prices(raw: pd.DataFrame, tickers: List[str]) -> pd.DataFrame:
    """
    Turn a raw yf.download() result into a clean Close-price DataFrame:
    columns = tickers, ascending DatetimeIndex, gaps forward-filled.
    """
    # yfinance returns MultiIndex columns when >1 ticker
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        # single ticker edge-case
        prices = raw[["Close"]]
        prices.columns = tickers

    # Ensure all requested tickers are present
    missing = set(tickers) - set(prices.columns)
    if missing:
        raise ValueError(f"Could not download data for: {missing}")

    # Forward-fill small gaps (weekends already absent, but some ETFs have
    # occasional missing days); then drop rows where any price is still NaN
    prices = prices.ffill().dropna()
    prices.index = pd.to_datetime(prices.index)
    prices.sort_index(inplace=True)

    return prices


def fetch_prices(tickers: List[str], extra_months: int = 0) -> pd.DataFrame:
    """
    Download adjusted-close prices for *tickers*, sized around the GEM
    momentum lookback window (LOOKBACK_DAYS + SKIP_DAYS + buffer).

    Parameters
    ----------
    tickers : list of ticker symbols to download
    extra_months : extend the download window this many months into the past,
                   on top of the standard LOOKBACK + SKIP + BUFFER window.
                   Use this when computing historical signals so every
                   month-start slice has enough rows for a full momentum calc.

    Returns
    -------
    pd.DataFrame
        Columns = tickers, index = pd.DatetimeIndex (ascending),
        NaN-forward-filled then remaining NaNs dropped.
    """
    end   = datetime.date.today()
    start = end - datetime.timedelta(days=_required_calendar_days(extra_months))

    raw = yf.download(
        tickers=tickers,
        start=str(start),
        end=str(end),
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    return _shape_prices(raw, tickers)


def fetch_price_history(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    """
    Download adjusted-close prices for *tickers* over a preset calendar
    period, for cumulative-return charting — unlike fetch_prices, the window
    isn't sized around the GEM momentum lookback, just the requested range.

    period: one of "ytd", "1mo", "3mo", "6mo", "1y", "3y", "5y", "10y", "max"
    """
    today = pd.Timestamp.today().normalize()

    if period == "max":
        start = pd.Timestamp("1990-01-01")
    elif period == "ytd":
        start = pd.Timestamp(year=today.year, month=1, day=1)
    elif period in _PERIOD_OFFSETS:
        start = today - _PERIOD_OFFSETS[period]
    else:
        raise ValueError(f"Unknown period '{period}'. Available: ytd, {', '.join(_PERIOD_OFFSETS)}, max")

    end = today + pd.Timedelta(days=1)  # yf.download's end is exclusive

    raw = yf.download(
        tickers=tickers,
        start=str(start.date()),
        end=str(end.date()),
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    return _shape_prices(raw, tickers)
