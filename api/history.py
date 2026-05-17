"""
api/history.py
──────────────
Computes the GEM signal for each month-end in the available price history.

How it works:
  For every first trading day of each calendar month in the price series,
  we slice the DataFrame at that date and run compute_signal() as if
  that day were "today". This gives a realistic backfill of what signal
  GEM would have produced at each monthly rebalance point.

Note: the earliest months are dropped if there isn't enough history
(LOOKBACK_DAYS + SKIP_DAYS rows before that date).
"""

from __future__ import annotations

import logging
from typing import List

import pandas as pd

from config import ALL_TICKERS, LOOKBACK_DAYS, SKIP_DAYS
from data.fetcher import fetch_prices
from strategy.gem import GEMSignal, compute_signal

logger = logging.getLogger(__name__)

# Minimum rows needed before a month-end slice is valid
_MIN_ROWS = LOOKBACK_DAYS + SKIP_DAYS + 2


def _first_trading_days(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return the first trading day of each calendar month in *index*."""
    series = pd.Series(index, index=index)
    return pd.DatetimeIndex(
        series.groupby([series.index.year, series.index.month]).first()
    )


def compute_history(months: int = 24) -> List[dict]:
    """
    Fetch full price history and return one GEM signal per month,
    most-recent first, capped at *months* entries.

    Each dict matches the HistoricalEntry schema.
    """
    prices = fetch_prices(ALL_TICKERS)
    month_starts = _first_trading_days(prices.index)

    # Keep only the last `months` month-start dates
    month_starts = month_starts[-months:]

    results = []
    for date in month_starts:
        # Slice history up to and including this date
        slice_df = prices.loc[prices.index <= date]

        if len(slice_df) < _MIN_ROWS:
            logger.debug("Skipping %s — not enough history (%d rows)", date.date(), len(slice_df))
            continue

        try:
            signal: GEMSignal = compute_signal(slice_df)
        except ValueError as exc:
            logger.warning("Skipping %s — %s", date.date(), exc)
            continue

        results.append({
            "date":           date.strftime("%Y-%m-%d"),
            "hold_ticker":    signal.hold_ticker,
            "hold_name":      signal.hold_name,
            "equity_winner":  signal.equity_winner,
            "beat_risk_free": signal.beat_risk_free,
            "scores": {
                ticker: {
                    "ticker":       s.ticker,
                    "name":         s.name,
                    "price_then":   s.price_then,
                    "price_now":    s.price_now,
                    "momentum_pct": s.momentum_pct,
                }
                for ticker, s in signal.scores.items()
            },
        })

    # Most-recent first
    results.reverse()
    return results
