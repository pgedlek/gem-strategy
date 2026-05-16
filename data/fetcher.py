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


def _required_calendar_days() -> int:
    """
    Convert trading-day requirements to a calendar-day window.
    Markets are open ~252 days / year ≈ 5/7 of calendar days.
    Add buffer so we always have enough rows even after holidays / gaps.
    """
    trading_days_needed = LOOKBACK_DAYS + SKIP_DAYS + DOWNLOAD_BUFFER
    calendar_days = int(trading_days_needed * (7 / 5)) + 60
    return calendar_days


def fetch_prices(tickers: List[str]) -> pd.DataFrame:
    """
    Download adjusted-close prices for *tickers*.

    Returns
    -------
    pd.DataFrame
        Columns = tickers, index = pd.DatetimeIndex (ascending),
        NaN-forward-filled then remaining NaNs dropped.
    """
    end   = datetime.date.today()
    start = end - datetime.timedelta(days=_required_calendar_days())

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
