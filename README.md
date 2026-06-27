# StockVision AI

> A full-stack AI-assisted stock scanner that identifies the **top 10 bullish picks** from India's Nifty 100 universe in real time — powered by a FastAPI backend, a multi-factor scoring model, and a React + AWS Cloudscape frontend.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)
![Cloudscape](https://img.shields.io/badge/AWS-Cloudscape_Design-FF9900?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Scoring Model](#scoring-model)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Clone the Repository](#clone-the-repository)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Testing](#testing)
- [Property-Based Testing](#property-based-testing)
- [Design Decisions](#design-decisions)
- [Portfolio Notes](#portfolio-notes)
- [License](#license)

---

## Overview

StockVision AI scans the **Nifty 100** universe (Nifty 50 + Nifty Next 50) every time a user loads the page. For each of the 100 large-cap NSE stocks it:

1. Fetches 252 calendar days of OHLCV data via **yfinance** (async, rate-limited)
2. Computes **SMA50, SMA200, 20-session average volume, and 52-week high**
3. Scores each stock on a **0–100 bullish scale** using three binary signals
4. Returns the **top 10 ranked picks** as a JSON payload
5. Renders them in a **sortable table with inline 30-day sparklines**

The entire pipeline — from raw market data to rendered UI — completes in under 60 seconds on a standard broadband connection.

---

## System Architecture

```
┌───────────────────────────────────────────────────────┐
│                    Browser (SPA)                       │
│   React 18 + AWS Cloudscape + Recharts                 │
│   http://localhost:5173                                │
│                                                        │
│   App.tsx ──── GET /api/scan ──────────────────────┐  │
│      │                                             │  │
│   ScanHeader                  JSON response ◀──────┘  │
│   PicksTable (sortable)                               │
│   Sparkline (30d, colour-coded)                       │
└───────────────────────────────────────────────────────┘
                        │ HTTP / CORS
                        ▼
┌───────────────────────────────────────────────────────┐
│                  FastAPI Backend                       │
│   http://localhost:8000                               │
│                                                        │
│   router.py  →  scanner.py  →  data_fetcher.py        │
│   (dedup)       (orchestrate)   (async + semaphore)   │
│                      │                                │
│               indicators.py   scorer.py               │
│               (SMA, vol, 52w)  (score + rank)         │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
                   yfinance API
                 (NSE market data)
```

**Key design choices:**

- **Single `GET /api/scan` endpoint** — keeps integration trivial; no websockets, no polling.
- **`asyncio.Semaphore`** — caps concurrent yfinance downloads at 5 to avoid rate-limiting while keeping total scan time low.
- **In-flight deduplication** — a shared `asyncio.Future` + `asyncio.Lock` ensures that if two browser tabs hit `/api/scan` simultaneously, only one scan runs and both tabs get the same result.
- **Pure indicator functions** — `compute_indicators()` is side-effect-free and takes only a pandas DataFrame, making it trivially testable without mocking.

---

## Scoring Model

Each stock receives a **Bullish Score from 0 to 100** based on three binary signals:

| Signal | Condition | Weight |
|---|---|---|
| **SMA Trend** | `close > SMA50` AND `close > SMA200` | 40 pts |
| **Volume Surge** | `last_volume > 1.5 × avg_volume_20` | 35 pts |
| **52W High Proximity** | `close >= 0.75 × 52w_high` | 25 pts |

**Possible scores:** `{0, 25, 35, 40, 60, 65, 75, 100}`

Ties at the same score are broken by **descending volume ratio** (current volume ÷ 20-session average). The top 10 ranked picks are returned, ordered highest score first.

Stocks are excluded from scoring if:
- yfinance returns no data or an error
- Fewer than 150 trading bars are available
- Fewer than 200 closing prices or 20 volume data points exist

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.111 + Uvicorn |
| Data fetching | yfinance 0.2.61 (async via `ThreadPoolExecutor`) |
| Data processing | pandas 2.2, NumPy 1.26 |
| Config | pydantic-settings 2.2 |
| Timezone handling | pytz 2024.1 |
| Testing | pytest 8.2, Hypothesis 6.112 (property-based) |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript 5.5 |
| Build tool | Vite 5 |
| UI components | AWS Cloudscape Design System 3.x |
| Charts | Recharts 2.12 |
| Testing | Vitest 2 |

---

## Project Structure

```
StockVision-AI/
├── backend/
│   ├── __init__.py
│   ├── config.py           # Settings via pydantic-settings + .env
│   ├── market_calendar.py  # NSE/BSE trading day utilities
│   ├── universe.py         # NIFTY_100 symbol list + company name map
│   ├── indicators.py       # Pure: compute_indicators(symbol, df) → Indicators
│   ├── scorer.py           # compute_score(ind), rank_stocks(indicators, ...)
│   ├── data_fetcher.py     # async fetch_ohlcv(symbol, sem) via yfinance
│   ├── scanner.py          # run_scan() — orchestrates the full pipeline
│   ├── router.py           # GET /api/scan + in-flight deduplication
│   └── main.py             # FastAPI app, CORS, router registration
├── frontend/
│   ├── .env                # VITE_API_BASE_URL=http://localhost:8000
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx         # Fetch + loading/error/success state
│       ├── types.ts        # TopPick, ScanResult interfaces
│       └── components/
│           ├── ScanHeader.tsx   # Cloudscape Header + IST timestamp
│           ├── PicksTable.tsx   # Cloudscape Table with sort state
│           └── Sparkline.tsx    # Recharts 100×40 px sparkline
├── tests/
│   ├── test_indicators.py  # Property-based tests (Hypothesis)
│   └── test_scorer.py      # Property-based tests (Hypothesis)
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Git**

Verify your versions:

```bash
python --version   # Python 3.11+
node --version     # v18+
npm --version      # 9+
```

---

### Clone the Repository

```bash
git clone https://github.com/your-username/StockVision-AI.git
cd StockVision-AI
```

---

### Backend Setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

**2. Install Python dependencies**

```bash
pip install -r requirements.txt
```

**3. (Optional) Create a `.env` file in the project root**

The backend works out-of-the-box with defaults, but you can override settings:

```bash
# .env  (project root)
CONCURRENCY_LIMIT=5       # max parallel yfinance downloads
REQUEST_TIMEOUT_S=10      # per-symbol timeout
CACHE_DIR=.cache          # reserved for future disk-cache use
```

---

### Frontend Setup

**1. Navigate to the frontend directory and install dependencies**

```bash
cd frontend
npm install
```

**2. Verify the `.env` file**

A `frontend/.env` file is already included. It points the React app at the local backend:

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

Change this value if your backend runs on a different host or port.

---

### Running the Application

You need **two terminals** running simultaneously.

**Terminal 1 — Start the backend** (from the project root):

```bash
uvicorn backend.main:app --reload
```

The API is now available at `http://localhost:8000`.
You can test it directly: `curl http://localhost:8000/api/scan`

**Terminal 2 — Start the frontend** (from the `frontend/` directory):

```bash
npm run dev
```

Open `http://localhost:5173` in your browser. The app will immediately trigger a scan — expect a loading spinner for ~30–60 seconds while market data is fetched, then the ranked table appears.

---

## API Reference

### `GET /api/scan`

Triggers a full Nifty 100 scan and returns ranked picks.

**Success — HTTP 200**

```json
{
  "scan_timestamp": "2025-01-15T10:30:00+05:30",
  "total_qualified": 87,
  "picks": [
    {
      "rank": 1,
      "symbol": "RELIANCE.NS",
      "company_name": "Reliance Industries",
      "score": 100,
      "close": 1423.50,
      "sma50": 1380.00,
      "sma200": 1300.00,
      "volume_ratio": 2.35,
      "pct_from_52w_high": 3.20,
      "price_history_30d": [1350.0, 1360.5, "...", 1423.5]
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `scan_timestamp` | `string` | ISO 8601 timestamp in IST (Asia/Kolkata) |
| `total_qualified` | `integer` | Number of stocks that passed all data-quality filters |
| `picks[].rank` | `integer` | 1 = highest score |
| `picks[].score` | `integer` | Bullish Score, 0–100 |
| `picks[].volume_ratio` | `float` | Current volume ÷ 20-session average volume |
| `picks[].pct_from_52w_high` | `float` | % below the 52-week closing high (lower = closer to high) |
| `picks[].price_history_30d` | `float[]` | 30 daily closes, oldest first |

**Failure — HTTP 503**

```json
{ "error": "All symbols failed data retrieval" }
```

---

## Configuration

All backend thresholds are centralised in `backend/config.py` and can be overridden via environment variables or a `.env` file in the project root.

| Variable | Default | Purpose |
|---|---|---|
| `CONCURRENCY_LIMIT` | `5` | Max parallel yfinance downloads |
| `REQUEST_TIMEOUT_S` | `10` | Per-symbol HTTP timeout |
| `CACHE_DIR` | `.cache` | Reserved for future disk-cache use |

Frontend config lives in `frontend/.env`:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend origin URL |

---

## Testing

**Backend tests** (from the project root):

```bash
pytest tests/ -v
```

**Frontend tests** (from the `frontend/` directory):

```bash
npm test
```

**Run everything at once** (from the project root):

```bash
pytest tests/ -v && cd frontend && npm test
```

---

## Property-Based Testing

StockVision AI uses **property-based testing** (PBT) as a first-class correctness strategy, not just as an afterthought. Rather than writing example-based unit tests, formal correctness properties are encoded as executable specifications.

### Backend — Hypothesis

| Property | What it asserts |
|---|---|
| **P1: Minimum bar filter** | `compute_indicators` returns `None` iff rows < 150 — verified across thousands of generated DataFrames |
| **P3: SMA correctness** | `sma50 == mean(closes[-50:])`, `sma200 == mean(closes[-200:])`, `avg_volume_20 == mean(volumes[-20:])` |
| **P4: 52-week high is a maximum** | `high_52w == max(closes[-252:])` and ≥ every close in that window |
| **P5: Score formula and range** | All 8 binary signal combinations yield a score in `{0, 25, 35, 40, 60, 65, 75, 100}` |
| **P6: Signal threshold conditions** | Each signal bit is 1 iff its threshold condition holds, for any generated `Indicators` |
| **P7: Top picks are highest-scoring** | Every pick score ≥ every non-pick score; ties ordered by descending `volume_ratio` |

This approach surface bugs that example tests miss — edge cases at exact threshold boundaries, floating-point ordering issues, and empty-list corner cases are all explored automatically.

---

## Design Decisions

**Why FastAPI?** Async-native, automatic OpenAPI docs at `/docs`, and pydantic validation with zero boilerplate. The entire backend is under 300 lines of application code.

**Why Cloudscape?** AWS's open-source design system ships accessible, production-grade table/sort/alert/spinner components out of the box. No custom CSS needed, which keeps the frontend lean and the visual output professional.

**Why property-based testing over unit tests?** The scoring model has precise mathematical invariants (score formula, tie-breaking order, filter threshold). PBT with Hypothesis generates hundreds of edge-case inputs automatically, providing stronger correctness guarantees than a handful of hand-written examples.

**Why pure functions for indicators?** `compute_indicators()` and `compute_score()` take data in and return results out with zero side effects. This makes them deterministic, composable, and trivially testable in isolation.

**Why in-flight deduplication?** A scan takes 30–60 seconds. Without deduplication, two simultaneous page loads would each trigger 100 yfinance downloads — doubling the load and the latency. The shared `asyncio.Future` pattern ensures both callers share one result at zero additional cost.

---

## Portfolio Notes

This project was built to demonstrate end-to-end GenAI-assisted software engineering across the full stack:

- **Spec-driven development** — requirements, design, and implementation tasks were formalised as structured spec documents before any code was written, enabling systematic, traceable development.
- **Domain-specific AI reasoning** — the scoring model encodes quantitative finance heuristics (Minervini-style stage analysis, volume-surge detection, 52-week-high proximity) as explicit, auditable formulas rather than black-box model weights.
- **Async systems design** — demonstrates practical concurrency patterns (semaphore rate-limiting, future-based deduplication) in a Python async context.
- **Modern frontend architecture** — React 18 with TypeScript strict mode, AWS Cloudscape for enterprise-grade UI, and Recharts for data visualisation — all wired together with zero custom CSS.
- **Formal correctness** — property-based testing with Hypothesis bridges the gap between human-readable specifications and machine-verifiable guarantees, a technique central to building reliable AI-assisted systems.

**Potential extensions:**
- Add a news sentiment signal using an LLM API (OpenAI / Bedrock) as an additional scoring dimension
- Stream scan progress via Server-Sent Events instead of a single long-poll
- Cache scan results to SQLite (`scans.db` path is already in config) to serve repeat requests instantly
- Deploy backend to AWS Lambda + API Gateway; frontend to S3 + CloudFront

---

## License

MIT — see [LICENSE](LICENSE) for details.
