"""
strategy/gem.py
───────────────
Implements Gary Antonacci's Global Equity Momentum (GEM) signal.

Algorithm (classic GEM):
  1. Compute 12-month (skip-1-month) total return for each candidate ETF.
  2. RELATIVE momentum: compare US equity vs International equity.
     → Winner advances to step 3.
  3. ABSOLUTE momentum: compare the winner against the risk-free rate (BIL).
     → If winner > BIL  → HOLD the equity winner
     → If winner ≤ BIL  → HOLD the safe-haven bond (defensive)

Reference: Antonacci, "Dual Momentum Investing" (2014)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pandas as pd

from config import (
    EQUITY_US, EQUITY_INTL, SAFE_HAVEN, RISK_FREE,
    LOOKBACK_DAYS, SKIP_DAYS,
)


# ── Data class for a single ETF's momentum snapshot ──────────────────────────

@dataclass
class MomentumScore:
    ticker:         str
    name:           str
    price_now:      float
    price_then:     float
    momentum_pct:   float          # (price_now / price_then - 1) * 100


# ── Data class for the overall GEM decision ───────────────────────────────────

@dataclass
class GEMSignal:
    # The ETF to hold right now
    hold_ticker:    str
    hold_name:      str
    # Detailed scores for every candidate
    scores:         Dict[str, MomentumScore] = field(default_factory=dict)
    # Explanation path
    equity_winner:  str  = ""   # winner of relative-momentum comparison
    beat_risk_free: bool = True  # did equity beat BIL?
    # Prices as of today
    as_of_date:     str  = ""


# ── Core calculation ──────────────────────────────────────────────────────────

def _momentum(prices: pd.DataFrame, ticker: str) -> MomentumScore:
    """
    12-month (skip-1-month) momentum for a single ticker.

    We look back LOOKBACK_DAYS trading days, but skip the most recent
    SKIP_DAYS to avoid short-term reversal (Jegadeesh & Titman, 1993).

    Returns price 'then' (= LOOKBACK_DAYS ago) and price 'now'
    (= SKIP_DAYS ago, i.e. ~1 month before today).
    """
    col = prices[ticker]

    if len(col) < LOOKBACK_DAYS + SKIP_DAYS:
        raise ValueError(
            f"Not enough price history for {ticker}. "
            f"Need {LOOKBACK_DAYS + SKIP_DAYS} rows, got {len(col)}."
        )

    price_now  = col.iloc[-(SKIP_DAYS + 1)]   # ~1 month ago (skip-1)
    price_then = col.iloc[-(LOOKBACK_DAYS + SKIP_DAYS + 1)]  # ~13 months ago

    momentum_pct = (price_now / price_then - 1) * 100

    # Map ticker → name from config
    name_map = {
        EQUITY_US["ticker"]:   EQUITY_US["name"],
        EQUITY_INTL["ticker"]: EQUITY_INTL["name"],
        SAFE_HAVEN["ticker"]:  SAFE_HAVEN["name"],
        RISK_FREE["ticker"]:   RISK_FREE["name"],
    }

    return MomentumScore(
        ticker       = ticker,
        name         = name_map.get(ticker, ticker),
        price_now    = round(price_now, 2),
        price_then   = round(price_then, 2),
        momentum_pct = round(momentum_pct, 2),
    )


def compute_signal(prices: pd.DataFrame) -> GEMSignal:
    """
    Run the full GEM algorithm on a price DataFrame and return a GEMSignal.
    """
    us_ticker   = EQUITY_US["ticker"]
    intl_ticker = EQUITY_INTL["ticker"]
    rf_ticker   = RISK_FREE["ticker"]
    sh_ticker   = SAFE_HAVEN["ticker"]

    # ── Step 1: Compute momentum for all candidates ───────────────────────────
    scores: Dict[str, MomentumScore] = {}
    for ticker in [us_ticker, intl_ticker, rf_ticker]:
        scores[ticker] = _momentum(prices, ticker)

    # If safe-haven ≠ risk-free, score it too (in this config they're both BIL)
    if sh_ticker not in scores:
        scores[sh_ticker] = _momentum(prices, sh_ticker)

    as_of_date = prices.index[-1].strftime("%Y-%m-%d")

    # ── Step 2: Relative momentum – US vs International ───────────────────────
    us_mom   = scores[us_ticker].momentum_pct
    intl_mom = scores[intl_ticker].momentum_pct

    if us_mom >= intl_mom:
        equity_winner        = us_ticker
        equity_winner_name   = EQUITY_US["name"]
    else:
        equity_winner        = intl_ticker
        equity_winner_name   = EQUITY_INTL["name"]

    # ── Step 3: Absolute momentum – equity winner vs risk-free ────────────────
    equity_mom  = scores[equity_winner].momentum_pct
    rf_mom      = scores[rf_ticker].momentum_pct
    beat_rf     = equity_mom > rf_mom

    if beat_rf:
        hold_ticker = equity_winner
        hold_name   = equity_winner_name
    else:
        hold_ticker = sh_ticker
        hold_name   = SAFE_HAVEN["name"]

    return GEMSignal(
        hold_ticker    = hold_ticker,
        hold_name      = hold_name,
        scores         = scores,
        equity_winner  = equity_winner,
        beat_risk_free = beat_rf,
        as_of_date     = as_of_date,
    )