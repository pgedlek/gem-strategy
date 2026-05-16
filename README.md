# GEM Tool 📈
 
**Global Equity Momentum** strategy signal generator — CLI edition.
 
Based on Gary Antonacci's [Dual Momentum Investing](https://www.dualmomentum.net/) (2014).
 
---
 
## How it works
 
GEM rotates monthly between positions based on momentum:
 
```
┌──────────────────────────────────────────────────────────┐
│  1. RELATIVE  →  SPY vs ACWX (12-month momentum)         │
│                  Which equity ETF is stronger?           │
│                                                          │
│  2. ABSOLUTE  →  Equity winner vs BIL (risk-free)        │
│                  Are equities worth holding at all?      │
│                                                          │
│  HOLD equity winner  ──OR──  HOLD AGG (safe haven bonds) │
└──────────────────────────────────────────────────────────┘
```
 
**ETF universe (original Antonacci instruments):**
 
| Role | Ticker | Name | Original index |
|---|---|---|---|
| US Equity | `SPY` | SPDR S&P 500 ETF | S&P 500 |
| Intl Equity | `ACWX` | iShares MSCI ACWI ex-US ETF | MSCI ACWI ex-USA |
| Safe Haven | `AGG` | iShares Core U.S. Aggregate Bond ETF | Bloomberg US Aggregate Bond |
| Risk-Free benchmark | `BIL` | SPDR Bloomberg 1-3 Month T-Bill ETF | 3-Month US Treasury Bills |
 
> **Note:** `AGG` and `BIL` play different roles. `BIL` is only used as the absolute-momentum
> benchmark (step 2 comparison). `AGG` is what you actually *hold* during the defensive phase.
 
---
 
## Setup
 
```bash
# 1. Clone / copy the project
cd gem-strategy
 
# 2. Create a virtual environment (recommended)
python -m venv gem
source gem/bin/activate # Windows: .venv\Scripts\activate
 
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
  Intl Equity  (ACWX)           $50.22    $54.55    +8.62%
  Safe Haven   (AGG)            $95.10    $98.44    +3.51%
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
 
- **ETF tickers** — swap SPY → VTI, ACWX → VXUS, AGG → BND, etc.
- **Lookback window** — `LOOKBACK_TRADING_DAYS` (default 252 ≈ 12 months of trading days)
- **Skip window** — `SKIP_TRADING_DAYS` (default 21 ≈ 1 month of trading days, skip-1 convention)
---
 
## Roadmap
 
- [x] CLI signal output
- [ ] Monthly backtest with performance stats
- [ ] CSV / JSON export
- [ ] FastAPI backend
- [ ] Web UI (React)
 