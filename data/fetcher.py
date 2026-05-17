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


def fetch_prices(tickers: List[str], extra_months: int = 0) -> pd.DataFrame:
    """
    Download adjusted-close prices for *tickers*.

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
