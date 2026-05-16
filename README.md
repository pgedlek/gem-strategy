# GEM Tool 📈

**Global Equity Momentum** strategy signal generator — CLI edition.

Based on Gary Antonacci's [Dual Momentum Investing](https://www.dualmomentum.net/) (2014).

---

## How it works

GEM rotates monthly between three positions based on momentum:

```
┌─────────────────────────────────────────────────────┐
│  1. RELATIVE  →  SPY vs EFA (12-month momentum)     │
│                  Which equity ETF is stronger?       │
│                                                      │
│  2. ABSOLUTE  →  Equity winner vs BIL (risk-free)   │
│                  Are equities worth holding at all?  │
│                                                      │
│  HOLD equity winner  ──OR──  HOLD BIL (safe haven)  │
└─────────────────────────────────────────────────────┘
```

**Default ETF universe:**

| Role | Ticker | Name |
|---|---|---|
| US Equity | SPY | SPDR S&P 500 ETF |
| Intl Equity | EFA | iShares MSCI EAFE ETF |
| Safe Haven / Risk-Free | BIL | SPDR Bloomberg 1-3M T-Bill ETF |

---

## Setup

```bash
# 1. Clone / copy the project
cd gem-tool

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

---

## Example output

```
          GEM STRATEGY SIGNAL
  Global Equity Momentum  ·  Antonacci (2014)
──────────────────────────────────────────────────────────────

  ETF                            Then       Now     12M Mom
  ────────────────────────────── ────────── ──────── ─────────
  US Equity    (SPY)            $420.11   $521.34   +24.10%  ◀ relative winner
  Intl Equity  (EFA)            $68.22    $74.55    +9.28%
  Risk-Free    (BIL)            $91.44    $91.80    +0.39%

──────────────────────────────────────────────────────────────

  Step 1 – Relative momentum
  Equity winner: SPDR S&P 500 ETF

  Step 2 – Absolute momentum
  ✓ Equity beats risk-free → stay in equities

──────────────────────────────────────────────────────────────

  CURRENT SIGNAL

  HOLD → SPY  SPDR S&P 500 ETF

  As of: 2025-05-15
──────────────────────────────────────────────────────────────
```

---

## Configuration

Edit `config.py` to change:

- **ETF tickers** — swap SPY → VTI, EFA → VEU, BIL → AGG, etc.
- **Lookback window** — `LOOKBACK_DAYS` (default 252 ≈ 12 months)
- **Skip window** — `SKIP_DAYS` (default 21 ≈ 1 month, skip-1 convention)

---

## Roadmap

- [x] CLI signal output
- [ ] Monthly backtest with performance stats
- [ ] CSV / JSON export
- [ ] FastAPI backend
- [ ] Web UI (React)
