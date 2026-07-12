"""
api/cache.py
────────────
Simple in-memory daily cache for the GEM signal, one entry per strategy.

Design:
  - On first request of the day for a given strategy, fetch prices and
    compute the signal for that strategy.
  - Subsequent requests for the same strategy return the cached result
    instantly.
  - At midnight (next calendar day) that strategy's cache entry is stale
    and recomputes — except across weekends, when markets are closed and
    there's no new trading data to fetch, so Friday's result keeps serving
    through Saturday and Sunday.
  - Thread-safe via a single asyncio.Lock — FastAPI is async and traffic
    is low-frequency (daily refresh), so one lock covering all strategies
    is enough; it just serializes concurrent refreshes across strategies.

For a production deployment you'd replace _entries with Redis, but the
interface (get_signal / invalidate) stays the same.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Optional

from config import DEFAULT_STRATEGY, get_strategy, strategy_tickers
from data.fetcher import fetch_prices
from strategy.gem import GEMSignal, compute_signal

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    signal:       GEMSignal
    generated_at: datetime
    cache_date:   date          # the calendar date this was computed on


class SignalCache:
    """Cache that refreshes once per (trading) calendar day, per strategy."""

    def __init__(self) -> None:
        self._entries: Dict[str, _CacheEntry] = {}
        self._lock:    asyncio.Lock = asyncio.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    async def get_signal(
        self, strategy: str = DEFAULT_STRATEGY, force_refresh: bool = False
    ) -> tuple[GEMSignal, datetime, bool]:
        """
        Returns (signal, generated_at, was_cached) for the given strategy.
        Recomputes if that strategy's cache is empty, stale (new trading
        day), or force_refresh=True.
        """
        async with self._lock:
            entry = self._entries.get(strategy)
            if force_refresh or self._is_stale(entry):
                entry = await self._refresh(strategy)
                return entry.signal, entry.generated_at, False

            return entry.signal, entry.generated_at, True

    def is_populated(self, strategy: str = DEFAULT_STRATEGY) -> bool:
        return strategy in self._entries

    def cached_date(self, strategy: str = DEFAULT_STRATEGY) -> Optional[str]:
        entry = self._entries.get(strategy)
        return entry.signal.as_of_date if entry else None

    def invalidate(self, strategy: Optional[str] = None) -> None:
        """Force the next request to recompute (useful for testing).

        With no argument, clears every strategy's cache entry.
        """
        if strategy is None:
            self._entries.clear()
        else:
            self._entries.pop(strategy, None)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _is_stale(self, entry: Optional[_CacheEntry]) -> bool:
        if entry is None:
            return True
        today = date.today()
        if today.weekday() >= 5:  # Saturday=5, Sunday=6 — markets closed, no new data possible
            return False
        return entry.cache_date < today

    async def _refresh(self, strategy: str) -> _CacheEntry:
        logger.info("Cache miss — fetching prices and computing GEM signal for '%s'…", strategy)
        profile = get_strategy(strategy)
        tickers = strategy_tickers(profile)

        # Run blocking I/O in a thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        prices = await loop.run_in_executor(None, fetch_prices, tickers)
        signal = await loop.run_in_executor(None, compute_signal, prices, profile)

        entry = _CacheEntry(
            signal       = signal,
            generated_at = datetime.utcnow(),
            cache_date   = date.today(),
        )
        self._entries[strategy] = entry
        logger.info(
            "Cache refreshed for '%s'. Signal: HOLD %s as of %s",
            strategy, signal.hold_ticker, signal.as_of_date,
        )
        return entry


# Module-level singleton — imported by the FastAPI app
signal_cache = SignalCache()
