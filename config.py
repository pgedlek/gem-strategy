# ── GEM Tool · Configuration ──────────────────────────────────────────────────

# ETF universe — original GEM instruments (Antonacci)
#
#   EQUITY_US   → S&P 500 proxy
#   EQUITY_INTL → MSCI ACWI ex-US proxy  (all non-US developed + emerging)
#   SAFE_HAVEN  → US Aggregate Bond Index proxy  (defensive hold)
#   RISK_FREE   → 3-Month T-Bill proxy  (absolute-momentum benchmark)

EQUITY_US = {
    "ticker": "SPY",
    "name":   "SPDR S&P 500 ETF",
}

EQUITY_INTL = {
    "ticker": "ACWX",
    "name":   "iShares MSCI ACWI ex-US ETF",
}

SAFE_HAVEN = {
    "ticker": "AGG",
    "name":   "iShares Core U.S. Aggregate Bond ETF",
}

# Risk-free / absolute-momentum benchmark
# Used to decide: are equities worth holding at all?
RISK_FREE = {
    "ticker": "BIL",
    "name":   "SPDR Bloomberg 1-3 Month T-Bill ETF",
}

# All tickers the tool needs to fetch (deduplicated)
ALL_TICKERS = list(dict.fromkeys([
    EQUITY_US["ticker"],
    EQUITY_INTL["ticker"],
    SAFE_HAVEN["ticker"],
    RISK_FREE["ticker"],
]))

# Momentum look-back window (trading days).
# Classic GEM = 12 months ≈ 252 trading days.
# The tool also skips the most-recent month (Jegadeesh & Titman skip)
# to avoid short-term reversal noise.
LOOKBACK_DAYS  = 252   # ~12 months
SKIP_DAYS      = 21    # ~1 month  (skip-1 convention)

# How many extra days to download so we always have enough data after gaps
DOWNLOAD_BUFFER = 30