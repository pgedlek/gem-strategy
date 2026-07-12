# ── GEM Tool · Configuration ──────────────────────────────────────────────────

# Strategy profiles — each defines a 4-ETF universe for the GEM algorithm:
#
#   equity_us   → domestic equity leg
#   equity_intl → international/alternative equity leg (relative-momentum rival)
#   safe_haven  → defensive hold when equities lose absolute momentum
#   risk_free   → absolute-momentum benchmark (is equity worth holding at all?)

CLASSIC = {
    "key":   "classic",
    "label": "Classic GEM (Antonacci)",
    "equity_us":   {"ticker": "SPY",  "name": "SPDR S&P 500 ETF"},
    "equity_intl": {"ticker": "ACWX", "name": "iShares MSCI ACWI ex-US ETF"},
    "safe_haven":  {"ticker": "AGG",  "name": "iShares Core U.S. Aggregate Bond ETF"},
    "risk_free":   {"ticker": "BIL",  "name": "SPDR Bloomberg 1-3 Month T-Bill ETF"},
}

# Higher-beta variant: US tech-heavy growth vs. emerging markets, in place of
# broad US equity vs. developed/EM blend. Historically higher CAGR, but with
# deeper drawdowns — same GEM mechanics, riskier legs.
AGGRESSIVE = {
    "key":   "aggressive",
    "label": "Aggressive GEM (Nasdaq / Emerging Markets)",
    "equity_us":   {"ticker": "QQQ",  "name": "Invesco QQQ Trust (Nasdaq-100)"},
    "equity_intl": {"ticker": "EEM",  "name": "iShares MSCI Emerging Markets ETF"},
    "safe_haven":  {"ticker": "AGG",  "name": "iShares Core U.S. Aggregate Bond ETF"},
    "risk_free":   {"ticker": "BIL",  "name": "SPDR Bloomberg 1-3 Month T-Bill ETF"},
}

STRATEGIES = {
    CLASSIC["key"]:    CLASSIC,
    AGGRESSIVE["key"]: AGGRESSIVE,
}

DEFAULT_STRATEGY = CLASSIC["key"]

_ROLES = ("equity_us", "equity_intl", "safe_haven", "risk_free")


def get_strategy(key: str) -> dict:
    """Look up a strategy profile by key, raising a clear error if unknown."""
    try:
        return STRATEGIES[key]
    except KeyError:
        raise ValueError(
            f"Unknown strategy '{key}'. Available: {', '.join(STRATEGIES)}"
        ) from None


def strategy_tickers(profile: dict) -> list[str]:
    """All tickers a strategy profile needs fetched (deduplicated)."""
    return list(dict.fromkeys(profile[role]["ticker"] for role in _ROLES))


def strategy_name_map(profile: dict) -> dict[str, str]:
    """Ticker → display name for a strategy profile."""
    return {profile[role]["ticker"]: profile[role]["name"] for role in _ROLES}


# Momentum look-back window (trading days).
# Classic GEM = 12 months ≈ 252 trading days.
# The tool also skips the most-recent month (Jegadeesh & Titman skip)
# to avoid short-term reversal noise.
# Shared across all strategy profiles — only the instrument universe changes.
LOOKBACK_DAYS  = 252   # ~12 months
SKIP_DAYS      = 21    # ~1 month  (skip-1 convention)

# How many extra days to download so we always have enough data after gaps
DOWNLOAD_BUFFER = 30
