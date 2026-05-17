# GEM Tool 📈

**Global Equity Momentum** strategy signal generator — CLI + REST API.

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

## Project structure

```
gem-tool/
├── server.py              ← API entry point (start here for the backend)
├── main.py                ← CLI entry point
├── config.py              ← ETF universe & strategy parameters
├── requirements.txt
├── api/
│   ├── app.py             ← FastAPI app, routes, CORS middleware
│   ├── cache.py           ← Daily in-memory signal cache (async-safe)
│   ├── history.py         ← Monthly backfill logic (no look-ahead bias)
│   └── schemas.py         ← Pydantic response models
├── data/
│   └── fetcher.py         ← yfinance download & cleaning
└── strategy/
    └── gem.py             ← GEM signal algorithm
```

---

## Setup

```bash
# 1. Clone / copy the project
cd gem-strategy

# 2. Create a virtual environment (recommended)
python -m venv gem
source gem/bin/activate      # Windows: gem\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the API server

```bash
python server.py
```

The server starts on `http://localhost:8000` with auto-reload enabled (development mode).

For production:

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Interactive API docs (Swagger UI) are available at **`http://localhost:8000/docs`** once the server is running.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service status and cache state |
| `GET` | `/signal` | Current GEM signal — which ETF to hold now |
| `GET` | `/signal/scores` | Raw 12-month momentum % for all 4 ETFs |
| `GET` | `/history?months=N` | Monthly GEM signals for the past N months (1–120) |

### Caching

`/signal` and `/signal/scores` are served from an in-memory cache that refreshes once per calendar day. The cache warms automatically on server startup. The `cached` field in the response tells you whether the result was freshly computed or served from cache.

`/history` fetches fresh price data on every call. It downloads a wider price window proportional to the number of months requested, ensuring every month-start entry has a full 12-month lookback available — no look-ahead bias, no silently skipped entries.

### Example responses

**`GET /signal`**
```json
{
  "signal": {
    "hold_ticker": "SPY",
    "hold_name": "SPDR S&P 500 ETF",
    "equity_winner": "SPY",
    "beat_risk_free": true,
    "as_of_date": "2025-05-15"
  },
  "scores": {
    "SPY":  { "ticker": "SPY",  "momentum_pct": 24.10 },
    "ACWX": { "ticker": "ACWX", "momentum_pct":  8.62 },
    "AGG":  { "ticker": "AGG",  "momentum_pct":  3.51 },
    "BIL":  { "ticker": "BIL",  "momentum_pct":  0.39 }
  },
  "cached": true,
  "generated_at": "2025-05-15T08:01:34.000Z"
}
```

**`GET /history?months=3`**
```json
{
  "entries": [
    { "date": "2025-05-01", "hold_ticker": "SPY",  "beat_risk_free": true,  "equity_winner": "SPY"  },
    { "date": "2025-04-01", "hold_ticker": "AGG",  "beat_risk_free": false, "equity_winner": "SPY"  },
    { "date": "2025-03-01", "hold_ticker": "ACWX", "beat_risk_free": true,  "equity_winner": "ACWX" }
  ],
  "months": 3,
  "generated_at": "2025-05-15T09:14:22.000Z"
}
```

---

## Running the CLI

```bash
python main.py
```

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
- **Lookback window** — `LOOKBACK_DAYS` (default 252 ≈ 12 months of trading days)
- **Skip window** — `SKIP_DAYS` (default 21 ≈ 1 month of trading days, skip-1 convention)

---

## Testing

A Postman collection (`GEM_Strategy_API.postman_collection.json`) is included with requests and automated test scripts for all endpoints, including edge cases and validation errors.

Import it in Postman via **Import → drag the file in**. The `base_url` variable defaults to `http://localhost:8000`.

---

## Roadmap

- [x] CLI signal output
- [x] FastAPI backend with daily cache
- [x] Momentum scores endpoint
- [x] Historical signals endpoint (no look-ahead bias)
- [x] Postman collection
- [ ] Monthly backtest with performance stats
- [ ] CSV / JSON export
- [ ] Web UI (React)
