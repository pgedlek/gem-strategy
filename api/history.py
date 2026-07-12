"""
api/history.py
──────────────
Computes the GEM signal for each month-start in the available price history.

How it works:
  For every first trading day of each calendar month in the price series,
  we slice the DataFrame at that date and run compute_signal() as if
  that day were "today". This gives a realistic backfill of what signal
  GEM would have produced at each monthly rebalance point.

  Crucially, fetch_prices is called with extra_months = months so the
  download window is wide enough that every requested month-start slice
  already has a full 12-month lookback (LOOKBACK_DAYS + SKIP_DAYS rows)
  available before it — guaranteeing no entries are silently skipped.
"""

from __future__ import annotations

import logging
from typing import List

import pandas as pd

from config import DEFAULT_STRATEGY, LOOKBACK_DAYS, SKIP_DAYS, get_strategy, strategy_tickers
from data.fetcher import fetch_prices
from strategy.gem import GEMSignal, compute_signal

logger = logging.getLogger(__name__)

# Minimum rows needed before a month-start slice is valid
_MIN_ROWS = LOOKBACK_DAYS + SKIP_DAYS + 2


def _first_trading_days(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return the first trading day of each calendar month in *index*."""
    series = pd.Series(index, index=index)
    return pd.DatetimeIndex(
        series.groupby([series.index.year, series.index.month]).first()
    )


def compute_history(months: int = 24, strategy: str = DEFAULT_STRATEGY) -> List[dict]:
    """
    Fetch full price history for the given strategy profile and return one
    GEM signal per month, most-recent first, capped at *months* entries.

    fetch_prices is called with extra_months=months so the downloaded
    window extends far enough back that all requested month-starts have
    a complete 12-month lookback before them.

    Each dict matches the HistoricalEntry schema.
    """
    profile = get_strategy(strategy)
    tickers = strategy_tickers(profile)

    # Download enough history: standard window + one extra year per month
    # requested beyond the baseline lookback.
    prices = fetch_prices(tickers, extra_months=months)

    month_starts = _first_trading_days(prices.index)

    # Keep only the last `months` month-start dates
    month_starts = month_starts[-months:]

    results = []
    for date in month_starts:
        # Slice history up to and including this date
        slice_df = prices.loc[prices.index <= date]

        if len(slice_df) < _MIN_ROWS:
            # Should never happen now that the download window accounts for
            # extra_months, but kept as a safety net with a clear warning.
            logger.warning(
                "Skipping %s — not enough history (%d rows, need %d). "
                "This is unexpected; check DOWNLOAD_BUFFER in config.py.",
                date.date(), len(slice_df), _MIN_ROWS,
            )
            continue

        try:
            signal: GEMSignal = compute_signal(slice_df, profile)
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
