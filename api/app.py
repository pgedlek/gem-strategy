"""
api/app.py
──────────
FastAPI application — GEM Strategy API.

Endpoints
─────────
GET /health          → service status + per-strategy cache state
GET /signal          → current GEM signal (cached daily)
GET /signal/scores   → momentum scores for all ETFs (cached daily)
GET /history         → monthly GEM signals for the past N months
GET /history/series   → momentum history, chart-ready
GET /performance     → raw daily prices for cumulative-return charting

Every signal/history endpoint accepts a `strategy` query param selecting
which strategy profile (config.STRATEGIES) to run — "classic" (default,
SPY/ACWX) or "aggressive" (QQQ/EEM).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.cache import signal_cache
from api.history import compute_history
from api.schemas import (
    PerformanceResponse,
    PriceHistoryPoint,
    SeriesPoint,
    SeriesResponse,
    HealthResponse,
    HistoricalEntry,
    HistoryResponse,
    MomentumScoreSchema,
    SignalResponse,
    SignalSchema,
    StrategyCacheStatus,
)
from config import DEFAULT_STRATEGY, STRATEGIES, get_strategy, strategy_tickers
from data.fetcher import fetch_price_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# Dynamic enum so FastAPI/Swagger renders a dropdown of valid strategy keys
# and rejects unknown ones with a 422, without hardcoding the choices here.
StrategyKey = Enum("StrategyKey", {key: key for key in STRATEGIES})

_strategy_query = Query(
    default=StrategyKey(DEFAULT_STRATEGY),
    description="Strategy profile to run: " + ", ".join(STRATEGIES),
)

PerformancePeriod = Literal["ytd", "1mo", "3mo", "6mo", "1y", "3y", "5y", "10y", "max"]


# ── Lifespan: warm the default strategy's cache on startup ────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming signal cache on startup…")
    try:
        await signal_cache.get_signal(DEFAULT_STRATEGY)
        logger.info("Cache warm. Ready to serve.")
    except Exception as exc:
        # Don't crash the server if Yahoo Finance is temporarily unavailable
        logger.warning("Cache warm-up failed: %s — will retry on first request.", exc)
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="GEM Strategy API",
    description=(
        "Global Equity Momentum signal API.\n\n"
        "Based on Gary Antonacci's *Dual Momentum Investing* (2014). "
        "Computes 12-month (skip-1-month) momentum to determine the optimal "
        "ETF to hold each month. Supports multiple strategy profiles — "
        "select via the `strategy` query param."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for now — tighten when the UI domain is known
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Helper: convert internal types → schema ───────────────────────────────────

def _to_signal_schema(signal) -> SignalSchema:
    return SignalSchema(
        hold_ticker    = signal.hold_ticker,
        hold_name      = signal.hold_name,
        equity_winner  = signal.equity_winner,
        beat_risk_free = signal.beat_risk_free,
        as_of_date     = signal.as_of_date,
    )


def _to_score_schemas(signal) -> dict[str, MomentumScoreSchema]:
    return {
        ticker: MomentumScoreSchema(
            ticker       = s.ticker,
            name         = s.name,
            price_then   = s.price_then,
            price_now    = s.price_now,
            momentum_pct = s.momentum_pct,
        )
        for ticker, s in signal.scores.items()
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    tags=["meta"],
)
async def health() -> HealthResponse:
    """Returns the service status and cache state for every strategy profile."""
    return HealthResponse(
        status     = "ok",
        version    = app.version,
        strategies = {
            key: StrategyCacheStatus(
                cache_populated = signal_cache.is_populated(key),
                cache_date      = signal_cache.cached_date(key),
            )
            for key in STRATEGIES
        },
    )


@app.get(
    "/signal",
    response_model=SignalResponse,
    summary="Current GEM signal",
    tags=["signal"],
)
async def get_signal(strategy: StrategyKey = _strategy_query) -> SignalResponse:
    """
    Returns the current GEM signal — which ETF to hold right now — for the
    selected strategy profile.

    Result is cached and recomputed once per calendar day.
    """
    try:
        signal, generated_at, cached = await signal_cache.get_signal(strategy.value)
    except Exception as exc:
        logger.error("Failed to compute signal: %s", exc)
        raise HTTPException(status_code=503, detail=f"Unable to compute signal: {exc}")

    return SignalResponse(
        strategy     = strategy.value,
        signal       = _to_signal_schema(signal),
        scores       = _to_score_schemas(signal),
        cached       = cached,
        generated_at = generated_at,
    )


@app.get(
    "/signal/scores",
    response_model=dict[str, MomentumScoreSchema],
    summary="Momentum scores for all ETFs",
    tags=["signal"],
)
async def get_scores(strategy: StrategyKey = _strategy_query) -> dict[str, MomentumScoreSchema]:
    """
    Returns the raw 12-month momentum score for each ETF in the selected
    strategy's universe.

    Useful for building charts or comparing instruments directly.
    Result is cached alongside the main signal.
    """
    try:
        signal, _, _ = await signal_cache.get_signal(strategy.value)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to compute scores: {exc}")

    return _to_score_schemas(signal)


@app.get(
    "/history",
    response_model=HistoryResponse,
    summary="Historical monthly GEM signals",
    tags=["history"],
)
async def get_history(
    months: int = Query(
        default=24,
        ge=1,
        le=120,
        description="Number of past months to return (1–120)",
    ),
    strategy: StrategyKey = _strategy_query,
) -> HistoryResponse:
    """
    Returns the GEM signal that would have been produced at the start of
    each calendar month for the past *months* months, for the selected
    strategy profile.

    This is a real backfill — each entry uses only the price data that
    would have been available at that rebalance date (no look-ahead bias).

    ⚠️ This endpoint fetches fresh price data on every call (not cached)
    and may take a few seconds.
    """
    try:
        loop = asyncio.get_event_loop()
        raw_entries = await loop.run_in_executor(None, compute_history, months, strategy.value)
    except Exception as exc:
        logger.error("History computation failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Unable to compute history: {exc}")

    entries = [HistoricalEntry(**e) for e in raw_entries]

    return HistoryResponse(
        strategy     = strategy.value,
        entries      = entries,
        months       = len(entries),
        generated_at = datetime.utcnow(),
    )


@app.get(
    "/history/series",
    response_model=SeriesResponse,
    summary="Momentum series per ticker — chart-ready",
    tags=["history"],
)
async def get_history_series(
    months: int = Query(
        default=24,
        ge=1,
        le=120,
        description="Number of past months to return (1–120)",
    ),
    strategy: StrategyKey = _strategy_query,
) -> SeriesResponse:
    """
    Returns 12-month momentum history shaped as one list per ticker —
    optimised for feeding directly into a multi-line chart (e.g. Recharts).

    Response shape:
    ```json
    {
      "strategy": "classic",
      "series": {
        "SPY":  [{ "date": "2024-06", "momentum_pct": 18.4 }, ...],
        "ACWX": [{ "date": "2024-06", "momentum_pct":  9.1 }, ...],
        "AGG":  [{ "date": "2024-06", "momentum_pct":  2.3 }, ...],
        "BIL":  [{ "date": "2024-06", "momentum_pct":  0.4 }, ...]
      },
      "months": 24,
      "generated_at": "..."
    }
    ```

    Points are ordered oldest → newest so they map directly to an x-axis.
    Uses the same underlying data as `/history` — no extra fetch cost.

    ⚠️ Fetches fresh price data on every call and may take a few seconds.
    """
    try:
        loop = asyncio.get_event_loop()
        raw_entries = await loop.run_in_executor(None, compute_history, months, strategy.value)
    except Exception as exc:
        logger.error("Series computation failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Unable to compute series: {exc}")

    # Pivot: entries (newest→oldest) → per-ticker series (oldest→newest)
    # raw_entries is already newest-first from compute_history, so reverse it
    chronological = list(reversed(raw_entries))

    series: dict[str, list[SeriesPoint]] = {}
    for entry in chronological:
        for ticker, score in entry["scores"].items():
            series.setdefault(ticker, []).append(
                SeriesPoint(
                    date         = entry["date"][:7],   # "YYYY-MM"
                    momentum_pct = score["momentum_pct"],
                )
            )

    return SeriesResponse(
        strategy     = strategy.value,
        series       = series,
        months       = len(chronological),
        generated_at = datetime.utcnow(),
    )


@app.get(
    "/performance",
    response_model=PerformanceResponse,
    summary="Raw price history for cumulative-return charting",
    tags=["history"],
)
async def get_performance(
    period: PerformancePeriod = Query(
        default="1y",
        description="Preset lookback period: ytd, 1mo, 3mo, 6mo, 1y, 3y, 5y, 10y, max",
    ),
    strategy: StrategyKey = _strategy_query,
) -> PerformanceResponse:
    """
    Returns raw daily adjusted-close prices for every ETF in the selected
    strategy's universe, over the requested period — one series per ticker,
    oldest → newest.

    Unlike `/signal`'s momentum scores, this is unprocessed price data: the
    client normalizes each series to a cumulative % return from its own
    first point (e.g. `(price / series[0].price - 1) * 100`), so the chart
    always starts every line at 0% regardless of the selected period.

    ⚠️ Fetches fresh price data on every call and may take a few seconds,
    longer for "10y" / "max".
    """
    try:
        profile = get_strategy(strategy.value)
        tickers = strategy_tickers(profile)
        loop = asyncio.get_event_loop()
        prices = await loop.run_in_executor(None, fetch_price_history, tickers, period)
    except Exception as exc:
        logger.error("Performance fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Unable to fetch performance: {exc}")

    series: dict[str, list[PriceHistoryPoint]] = {
        ticker: [
            PriceHistoryPoint(date=idx.strftime("%Y-%m-%d"), price=round(float(price), 2))
            for idx, price in prices[ticker].items()
        ]
        for ticker in tickers
    }

    return PerformanceResponse(
        strategy     = strategy.value,
        period       = period,
        series       = series,
        generated_at = datetime.utcnow(),
    )
