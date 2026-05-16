#!/usr/bin/env python3
"""
main.py  –  GEM Tool CLI
────────────────────────
Run:
    python main.py

Prints the current GEM signal to stdout with a clean, colour-coded layout.
"""

from __future__ import annotations

import sys

from config import ALL_TICKERS, EQUITY_US, EQUITY_INTL, RISK_FREE, SAFE_HAVEN
from data.fetcher import fetch_prices
from strategy.gem import GEMSignal, compute_signal


# ── ANSI colour helpers (graceful fallback on Windows / dumb terminals) ───────

def _supports_color() -> bool:
    import os
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and os.name != "nt"


USE_COLOR = _supports_color()

RESET  = "\033[0m"  if USE_COLOR else ""
BOLD   = "\033[1m"  if USE_COLOR else ""
GREEN  = "\033[32m" if USE_COLOR else ""
RED    = "\033[31m" if USE_COLOR else ""
YELLOW = "\033[33m" if USE_COLOR else ""
CYAN   = "\033[36m" if USE_COLOR else ""
DIM    = "\033[2m"  if USE_COLOR else ""


def _pct_color(pct: float) -> str:
    color = GREEN if pct >= 0 else RED
    sign  = "+" if pct >= 0 else ""
    return f"{color}{sign}{pct:.2f}%{RESET}"


# ── Rendering ─────────────────────────────────────────────────────────────────

def print_signal(signal: GEMSignal) -> None:
    width = 62
    line  = "─" * width

    print()
    print(f"{BOLD}{CYAN}{'GEM STRATEGY SIGNAL':^{width}}{RESET}")
    print(f"{DIM}{'Global Equity Momentum  ·  Antonacci (2014)':^{width}}{RESET}")
    print(line)

    # ── Momentum scores table ─────────────────────────────────────────────────
    ticker_label = {
        EQUITY_US["ticker"]:   f"US Equity    ({EQUITY_US['ticker']})",
        EQUITY_INTL["ticker"]: f"Intl Equity  ({EQUITY_INTL['ticker']})",
        SAFE_HAVEN["ticker"]:  f"Safe Haven   ({SAFE_HAVEN['ticker']})",
        RISK_FREE["ticker"]:   f"Risk-Free    ({RISK_FREE['ticker']})",
    }

    print(f"\n  {'ETF':<30} {'Then':>8}  {'Now':>8}  {'12M Mom':>9}")
    print(f"  {'─'*30} {'─'*8}  {'─'*8}  {'─'*9}")

    for ticker, score in signal.scores.items():
        label   = ticker_label.get(ticker, ticker)
        mom_str = _pct_color(score.momentum_pct)
        winner_mark = (
            f"  {YELLOW}◀ relative winner{RESET}"
            if ticker == signal.equity_winner and signal.beat_risk_free
            else ""
        )
        print(
            f"  {label:<30} "
            f"${score.price_then:>7.2f}  "
            f"${score.price_now:>7.2f}  "
            f"{mom_str:>9}"
            f"{winner_mark}"
        )

    print()
    print(line)

    # ── Decision path ─────────────────────────────────────────────────────────
    eq_winner_name = next(
        v["name"] for v in [EQUITY_US, EQUITY_INTL]
        if v["ticker"] == signal.equity_winner
    )
    print(f"\n  {BOLD}Step 1 – Relative momentum{RESET}")
    print(f"  Equity winner: {CYAN}{eq_winner_name}{RESET}")

    print(f"\n  {BOLD}Step 2 – Absolute momentum{RESET}")
    if signal.beat_risk_free:
        print(f"  {GREEN}✓ Equity beats risk-free → stay in equities{RESET}")
    else:
        print(f"  {RED}✗ Equity below risk-free → rotate to safe haven{RESET}")

    print()
    print(line)

    # ── Final signal ──────────────────────────────────────────────────────────
    hold_color = GREEN if signal.hold_ticker != SAFE_HAVEN["ticker"] else YELLOW
    print(f"\n  {BOLD}CURRENT SIGNAL{RESET}")
    print(
        f"\n  {BOLD}HOLD → "
        f"{hold_color}{signal.hold_ticker}  "
        f"{signal.hold_name}{RESET}"
    )
    print(f"\n  {DIM}As of: {signal.as_of_date}{RESET}")
    print()
    print(line)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{DIM}Fetching price data from Yahoo Finance…{RESET}", end="", flush=True)

    try:
        prices = fetch_prices(ALL_TICKERS)
    except Exception as exc:
        print(f"\n{RED}Error fetching data: {exc}{RESET}")
        sys.exit(1)

    print(f"  {GREEN}done{RESET}")

    try:
        signal = compute_signal(prices)
    except Exception as exc:
        print(f"{RED}Error computing signal: {exc}{RESET}")
        sys.exit(1)

    print_signal(signal)


if __name__ == "__main__":
    main()