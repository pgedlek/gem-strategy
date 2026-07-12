"""
api/schemas.py
──────────────
Pydantic models that define every JSON shape the API returns.
Keeping schemas separate from strategy dataclasses means the API
contract can evolve independently of the internal calculation logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ── Shared building blocks ────────────────────────────────────────────────────

class MomentumScoreSchema(BaseModel):
    ticker:       str   = Field(..., example="SPY")
    name:         str   = Field(..., example="SPDR S&P 500 ETF")
    price_then:   float = Field(..., description="Price ~13 months ago (start of lookback window)")
    price_now:    float = Field(..., description="Price ~1 month ago (end of lookback window, skip-1)")
    momentum_pct: float = Field(..., description="12-month momentum in percent")


class SignalSchema(BaseModel):
    hold_ticker:    str  = Field(..., example="SPY")
    hold_name:      str  = Field(..., example="SPDR S&P 500 ETF")
    equity_winner:  str  = Field(..., description="Winner of the relative-momentum comparison")
    beat_risk_free: bool = Field(..., description="True if equity winner beat the risk-free benchmark")
    as_of_date:     str  = Field(..., example="2025-05-15")


# ── /signal ───────────────────────────────────────────────────────────────────

class SignalResponse(BaseModel):
    strategy:     str      = Field(..., example="classic", description="Strategy profile used (config.STRATEGIES key)")
    signal:       SignalSchema
    scores:       Dict[str, MomentumScoreSchema]
    cached:       bool     = Field(..., description="True if result was served from cache")
    generated_at: datetime = Field(..., description="When this result was calculated")


# ── /history ──────────────────────────────────────────────────────────────────

class HistoricalEntry(BaseModel):
    date:           str   = Field(..., example="2025-04-01", description="First trading day of the month")
    hold_ticker:    str
    hold_name:      str
    equity_winner:  str
    beat_risk_free: bool
    scores:         Dict[str, MomentumScoreSchema]


class HistoryResponse(BaseModel):
    strategy:     str      = Field(..., example="classic", description="Strategy profile used (config.STRATEGIES key)")
    entries:      List[HistoricalEntry]
    months:       int      = Field(..., description="Number of months returned")
    generated_at: datetime


# ── /health ───────────────────────────────────────────────────────────────────

class StrategyCacheStatus(BaseModel):
    cache_populated: bool
    cache_date:      Optional[str] = Field(None, description="as_of_date of the cached signal")


class HealthResponse(BaseModel):
    status:     str      = Field(..., example="ok")
    version:    str      = Field(..., example="1.0.0")
    strategies: Dict[str, StrategyCacheStatus] = Field(
        ..., description="Cache status per strategy profile"
    )


# ── /history/series ───────────────────────────────────────────────────────────

class SeriesPoint(BaseModel):
    date:         str   = Field(..., example="2025-04", description="Month in YYYY-MM format")
    momentum_pct: float = Field(..., description="12-month momentum in percent")


class SeriesResponse(BaseModel):
    strategy:     str      = Field(..., example="classic", description="Strategy profile used (config.STRATEGIES key)")
    series:       Dict[str, List[SeriesPoint]] = Field(
        ...,
        description="One ordered list of data points per ticker, oldest → newest"
    )
    months:       int      = Field(..., description="Number of months returned per series")
    generated_at: datetime


# ── /performance ─────────────────────────────────────────────────────────────

class PriceHistoryPoint(BaseModel):
    date:  str   = Field(..., example="2025-04-15", description="Trading day, YYYY-MM-DD")
    price: float = Field(..., description="Adjusted close price")


class PerformanceResponse(BaseModel):
    strategy:     str      = Field(..., example="classic", description="Strategy profile used (config.STRATEGIES key)")
    period:       str      = Field(..., example="1y", description="Requested preset period")
    series:       Dict[str, List[PriceHistoryPoint]] = Field(
        ...,
        description="One ordered list of raw daily prices per ticker, oldest → newest. "
                     "Cumulative % return is computed client-side against each series' first point."
    )
    generated_at: datetime
