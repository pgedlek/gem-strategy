"""
api/cache.py
────────────
Simple in-memory daily cache for the GEM signal.

Design:
  - On first request of the day, fetch prices and compute the signal.
  - Subsequent requests return the cached result instantly.
  - At midnight (next calendar day) the cache is stale and recomputes.
  - Thread-safe via asyncio.Lock — FastAPI is async, so one lock is enough.

For a production deployment you'd replace _store with Redis, but the
interface (get_signal / invalidate) stays the same.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from config import ALL_TICKERS
from data.fetcher import fetch_prices
from strategy.gem import GEMSignal, compute_signal

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    signal:       GEMSignal
    generated_at: datetime
    cache_date:   date          # the calendar date this was computed on


class SignalCache:
    """Singleton cache that refreshes once per calendar day."""

    def __init__(self) -> None:
        self._entry:  Optional[_CacheEntry] = None
        self._lock:   asyncio.Lock = asyncio.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    async def get_signal(self, force_refresh: bool = False) -> tuple[GEMSignal, datetime, bool]:
        """
        Returns (signal, generated_at, was_cached).
        Recomputes if the cache is empty, stale (new day), or force_refresh=True.
        """
        async with self._lock:
            if force_refresh or self._is_stale():
                await self._refresh()
                return self._entry.signal, self._entry.generated_at, False

            return self._entry.signal, self._entry.generated_at, True

    def is_populated(self) -> bool:
        return self._entry is not None

    def cached_date(self) -> Optional[str]:
        if self._entry is None:
            return None
        return self._entry.signal.as_of_date

    def invalidate(self) -> None:
        """Force the next request to recompute (useful for testing)."""
        self._entry = None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _is_stale(self) -> bool:
        if self._entry is None:
            return True
        return self._entry.cache_date < date.today()

    async def _refresh(self) -> None:
        logger.info("Cache miss — fetching prices and computing GEM signal…")
        # Run blocking I/O in a thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        prices = await loop.run_in_executor(None, fetch_prices, ALL_TICKERS)
        signal = await loop.run_in_executor(None, compute_signal, prices)

        self._entry = _CacheEntry(
            signal       = signal,
            generated_at = datetime.utcnow(),
            cache_date   = date.today(),
        )
        logger.info("Cache refreshed. Signal: HOLD %s as of %s", signal.hold_ticker, signal.as_of_date)


# Module-level singleton — imported by the FastAPI app
signal_cache = SignalCache()
