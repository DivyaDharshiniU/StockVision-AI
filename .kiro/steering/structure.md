# Project Structure & Conventions

## Directory Layout

```
StockVision-AI/
├── backend/             # Python FastAPI backend (importable package)
│   ├── __init__.py
│   ├── config.py        # Central config via pydantic-settings, never hardcode thresholds
│   ├── market_calendar.py  # NSE/BSE trading day utilities
│   ├── universe.py      # NIFTY_100 symbol list + company name map
│   ├── indicators.py    # Pure function: compute_indicators(symbol, df) → Indicators | None
│   ├── scorer.py        # Pure function: compute_score(ind), rank_stocks(indicators, ...)
│   ├── data_fetcher.py  # Async: fetch_ohlcv(symbol, sem) via yfinance
│   ├── scanner.py       # Orchestrator: run_scan() — full pipeline
│   ├── router.py        # API routes + in-flight deduplication
│   └── main.py          # FastAPI app setup, CORS, router mount
├── frontend/
│   ├── src/
│   │   ├── App.tsx      # Root component: fetch + loading/error/success state
│   │   ├── main.tsx     # React entry point
│   │   ├── types.ts     # TypeScript interfaces (TopPick, ScanResult)
│   │   └── components/
│   │       ├── ScanHeader.tsx   # Cloudscape Header + IST timestamp
│   │       ├── PicksTable.tsx   # Cloudscape Table with sort state
│   │       └── Sparkline.tsx    # Recharts 100×40 px sparkline
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── tests/               # Backend property-based tests (Hypothesis)
│   ├── test_indicators.py
│   ├── test_scorer.py
│   └── test_ranking_properties.py
└── requirements.txt
```

## Code Conventions

### Backend (Python)

- Use `from __future__ import annotations` at the top of every module
- Use `@dataclass` for data containers (Indicators, ScoredStock, etc.)
- Keep indicator and scoring functions **pure** — no side effects, no I/O
- Type hints on all function signatures; return types use `X | None` union syntax
- Module docstrings describe purpose; function docstrings describe behavior and edge cases
- Config thresholds live in `backend/config.py`, never hardcoded in logic modules
- Async patterns use `asyncio.Semaphore` for concurrency limiting

### Frontend (TypeScript)

- Functional components with hooks (no class components)
- Default exports for components
- AWS Cloudscape components for all UI elements (no custom CSS)
- Types in a dedicated `types.ts` file
- Environment variables accessed via `import.meta.env.VITE_*`

### Testing

- Property-based testing (Hypothesis) is the primary backend testing strategy
- Tests are in `tests/` directory at project root
- Each test function documents which properties/requirements it validates
- Use `@given` + `@settings(max_examples=N)` decorators
- Frontend tests use Vitest
