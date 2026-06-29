# Design Document: Backtest Evaluation

## Architecture Overview

The backtest feature extends the existing StockVision AI architecture with a parallel evaluation pipeline that reuses pure scoring functions but adds date-bounded data fetching, forward return computation for all qualified symbols, and precision/recall metric computation. The design follows the existing patterns: async orchestration with semaphore-bounded concurrency, pure functions for computations, and a single API endpoint per workflow.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (React + Cloudscape + Recharts)                           │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────────────┐│
│  │ Tabs Nav │→ │ BacktestPage │→ │ PrecisionRecallPanel           ││
│  └──────────┘  └──────┬───────┘  │ BacktestTable + Chart          ││
│                        │          └────────────────────────────────┘│
│                        │ GET /api/backtest?date=YYYY-MM-DD          │
└────────────────────────┼────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                                  │
│  ┌──────────────────┐                                              │
│  │ backtest_router   │ → validates date → calls run_backtest()     │
│  └────────┬─────────┘                                              │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │ backtest_engine   │ → orchestrates historical scan +             │
│  │                   │   forward return computation (ALL symbols) + │
│  │                   │   precision/recall computation               │
│  └────────┬─────────┘                                              │
│           ▼                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐      │
│  │ data_fetcher   │  │ indicators.py  │  │ scorer.py        │      │
│  │ (date-range)   │  │ (reused as-is) │  │ (reused as-is)   │      │
│  └────────────────┘  └────────────────┘  └──────────────────┘      │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ forward_returns.py — pure forward return computation         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│           ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ precision_recall.py — pure precision/recall computation      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### Backend Components

#### 1. `backend/data_fetcher.py` — Extended with date-range fetching

Add a new function alongside the existing `fetch_ohlcv`:

```python
async def fetch_ohlcv_range(
    symbol: str,
    start: date,
    end: date,
    sem: asyncio.Semaphore,
) -> pd.DataFrame | None:
    """Download daily OHLCV for symbol from start to end (inclusive).

    Uses yf.Ticker(symbol).history(start=..., end=...) instead of period="1y".
    The end parameter for yfinance is exclusive, so we add one calendar day.
    """
```

This function keeps the same semaphore pattern and ThreadPoolExecutor as `fetch_ohlcv`.

#### 2. `backend/forward_returns.py` — New pure module

```python
from __future__ import annotations

from datetime import date
from dataclasses import dataclass

import pandas as pd

from .market_calendar import is_trading_day


@dataclass
class ForwardReturns:
    return_5d: float | None   # percentage, 2 decimal places
    return_10d: float | None
    return_20d: float | None


def compute_forward_return(
    close_base: float,
    close_future: float,
) -> float:
    """Compute percentage return: ((future - base) / base) * 100, rounded to 2dp."""
    return round(((close_future - close_base) / close_base) * 100, 2)


def compute_forward_returns_for_symbol(
    backtest_date: date,
    price_series: pd.Series,  # DatetimeIndex → Close prices
    windows: tuple[int, ...] = (5, 10, 20),
) -> ForwardReturns:
    """Compute forward returns at each window (in trading days).

    Args:
        backtest_date: The date from which to measure forward.
        price_series: Series with DatetimeIndex containing closing prices
            from backtest_date onwards.
        windows: Tuple of trading-day offsets (default: 5, 10, 20).

    Returns:
        ForwardReturns with null for any window where data is unavailable.
    """
```

#### 3. `backend/precision_recall.py` — New pure module

```python
from __future__ import annotations

from dataclasses import dataclass

from .forward_returns import ForwardReturns


@dataclass
class PrecisionRecall:
    """Precision and recall metrics for each forward return window.

    Precision = (true_bullish_picks / 10) * 100
    Recall = (true_bullish_picks / total_true_bullish_all_stocks) * 100

    Where True_Bullish means forward_return > 0%.
    """
    precision_5d: float | None   # percentage, 2 decimal places
    precision_10d: float | None
    precision_20d: float | None
    recall_5d: float | None      # percentage, 2 decimal places
    recall_10d: float | None
    recall_20d: float | None


def classify_true_bullish(forward_return: float | None) -> bool | None:
    """Classify a stock as True_Bullish.

    Returns True if forward_return > 0%, False if <= 0%, None if data unavailable.
    """
    if forward_return is None:
        return None
    return forward_return > 0.0


def compute_precision(true_bullish_picks: int) -> float:
    """Compute precision as percentage: (true_bullish_picks / 10) * 100, rounded to 2dp.

    Denominator is always 10 (the fixed number of top picks).
    """
    return round((true_bullish_picks / 10) * 100, 2)


def compute_recall(true_bullish_picks: int, total_true_bullish: int) -> float | None:
    """Compute recall as percentage: (true_bullish_picks / total_true_bullish) * 100, rounded to 2dp.

    Returns None if total_true_bullish is 0 (no stocks were bullish, recall undefined).
    """
    if total_true_bullish == 0:
        return None
    return round((true_bullish_picks / total_true_bullish) * 100, 2)


def compute_precision_recall(
    pick_forward_returns: list[ForwardReturns],
    all_forward_returns: list[ForwardReturns],
) -> PrecisionRecall:
    """Compute precision and recall for each window (5d, 10d, 20d).

    Args:
        pick_forward_returns: ForwardReturns for the top 10 picks.
        all_forward_returns: ForwardReturns for ALL qualified Nifty 100 symbols.

    Returns:
        PrecisionRecall with values for each window.
        Returns None for a window if forward data is unavailable.
    """
```

#### 4. `backend/backtest_engine.py` — New orchestrator (updated for precision/recall)

```python
from __future__ import annotations

import asyncio
from datetime import date
from dataclasses import dataclass

from .config import get_settings
from .data_fetcher import fetch_ohlcv_range
from .forward_returns import ForwardReturns, compute_forward_returns_for_symbol
from .indicators import compute_indicators
from .market_calendar import subtract_trading_days, calendar_days_for_n_trading
from .precision_recall import PrecisionRecall, compute_precision_recall
from .scorer import rank_stocks, ScoredStock
from .universe import COMPANY_NAMES, NIFTY_100


@dataclass
class BacktestPick:
    rank: int
    symbol: str
    company_name: str
    score: int
    close: float
    sma50: float
    sma200: float
    volume_ratio: float
    pct_from_52w_high: float
    forward_returns: ForwardReturns


@dataclass
class BacktestResult:
    backtest_date: str          # ISO format YYYY-MM-DD
    picks: list[BacktestPick]
    benchmark_returns: ForwardReturns
    total_qualified: int
    precision_recall: PrecisionRecall


async def run_backtest(target_date: date) -> BacktestResult:
    """Run a historical scan as of target_date and compute forward returns.

    Steps:
    1. Compute fetch range: start = target_date - 252 trading days, end = today
    2. Fetch OHLCV for all Nifty 100 symbols (full range including forward data)
    3. Truncate to target_date for scoring
    4. Score and rank → top 10 picks
    5. Compute forward returns for ALL qualified symbols at 5, 10, 20 trading days
    6. Compute forward returns for benchmark ^NSEI
    7. Compute precision/recall using picks vs all qualified symbols
    """
```

**Key change**: Step 5 now computes forward returns for ALL qualified Nifty 100 symbols, not just the top 10 picks. This is necessary because the recall denominator requires knowing how many stocks in the entire universe were True_Bullish.

#### 5. `backend/backtest_router.py` — New API router

```python
from __future__ import annotations

from datetime import date, datetime

import pytz
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .backtest_engine import run_backtest

router = APIRouter()
_IST = pytz.timezone("Asia/Kolkata")


@router.get("/api/backtest")
async def backtest_endpoint(
    date: str = Query(..., description="Backtest date in YYYY-MM-DD format"),
) -> JSONResponse:
    """Run a backtest for the given date.

    Validates:
    - date format is YYYY-MM-DD (422 if not)
    - date is in the past (400 if today or future)
    - engine doesn't fail fatally (503 if it does)

    Response includes precision_recall object with per-window metrics.
    """
```

#### 6. `backend/main.py` — Mount new router

```python
from .backtest_router import router as backtest_router
app.include_router(backtest_router)
```

### Frontend Components

#### 7. `frontend/src/App.tsx` — Tab-based navigation

Use Cloudscape `Tabs` component (no external router needed since there are only two views). Tabs preserve component state when switching.

```tsx
import Tabs from "@cloudscape-design/components/tabs";

export default function App() {
  return (
    <Tabs
      tabs={[
        { id: "scan", label: "Live Scan", content: <ScanView /> },
        { id: "backtest", label: "Backtest", content: <BacktestPage /> },
      ]}
    />
  );
}
```

#### 8. `frontend/src/components/BacktestPage.tsx` — New page component

```tsx
import { useState } from "react";
import DatePicker from "@cloudscape-design/components/date-picker";
import Button from "@cloudscape-design/components/button";
import Spinner from "@cloudscape-design/components/spinner";
import Alert from "@cloudscape-design/components/alert";
import { BacktestResult } from "../types";
import BacktestTable from "./BacktestTable";
import BacktestChart from "./BacktestChart";
import PrecisionRecallPanel from "./PrecisionRecallPanel";

export default function BacktestPage() {
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
    try {
      const r = await fetch(`${base}/api/backtest?date=${selectedDate}`);
      if (!r.ok) {
        const body = await r.json();
        throw new Error(body.error || `HTTP ${r.status}`);
      }
      setResult(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Render layout:
  // 1. DatePicker + Run button
  // 2. Loading indicator / error alert
  // 3. PrecisionRecallPanel (prominent, above table)
  // 4. BacktestTable
  // 5. BacktestChart
}
```

#### 9. `frontend/src/components/PrecisionRecallPanel.tsx` — New metrics display

Displays precision and recall metrics prominently using Cloudscape Container with key-value pairs.

```tsx
import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Box from "@cloudscape-design/components/box";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import { PrecisionRecall } from "../types";

interface Props {
  precisionRecall: PrecisionRecall;
}

export default function PrecisionRecallPanel({ precisionRecall }: Props) {
  const formatMetric = (value: number | null): string => {
    if (value === null) return "N/A";
    return `${value.toFixed(2)}%`;
  };

  const getStatus = (value: number | null): "success" | "warning" | "error" | "info" => {
    if (value === null) return "info";
    if (value >= 70) return "success";
    if (value >= 40) return "warning";
    return "error";
  };

  return (
    <Container header={<Header variant="h2">Model Accuracy</Header>}>
      <ColumnLayout columns={3}>
        {/* 5-day window */}
        <div>
          <Box variant="awsui-key-label">5d Precision</Box>
          <StatusIndicator type={getStatus(precisionRecall.precision_5d)}>
            {formatMetric(precisionRecall.precision_5d)}
          </StatusIndicator>
          <Box variant="awsui-key-label">5d Recall</Box>
          <StatusIndicator type={getStatus(precisionRecall.recall_5d)}>
            {formatMetric(precisionRecall.recall_5d)}
          </StatusIndicator>
        </div>
        {/* 10-day window */}
        <div>
          <Box variant="awsui-key-label">10d Precision</Box>
          <StatusIndicator type={getStatus(precisionRecall.precision_10d)}>
            {formatMetric(precisionRecall.precision_10d)}
          </StatusIndicator>
          <Box variant="awsui-key-label">10d Recall</Box>
          <StatusIndicator type={getStatus(precisionRecall.recall_10d)}>
            {formatMetric(precisionRecall.recall_10d)}
          </StatusIndicator>
        </div>
        {/* 20-day window */}
        <div>
          <Box variant="awsui-key-label">20d Precision</Box>
          <StatusIndicator type={getStatus(precisionRecall.precision_20d)}>
            {formatMetric(precisionRecall.precision_20d)}
          </StatusIndicator>
          <Box variant="awsui-key-label">20d Recall</Box>
          <StatusIndicator type={getStatus(precisionRecall.recall_20d)}>
            {formatMetric(precisionRecall.recall_20d)}
          </StatusIndicator>
        </div>
      </ColumnLayout>
    </Container>
  );
}
```

#### 10. `frontend/src/components/BacktestTable.tsx` — Results table

Cloudscape Table with columns: Rank, Symbol, Company, Score, Close, 5d Return, 10d Return, 20d Return. Null forward returns display "N/A". Positive returns prefixed with "+", negative with "-".

#### 11. `frontend/src/components/BacktestChart.tsx` — Comparison chart

Recharts `BarChart` with grouped bars:
- X-axis: 5-day, 10-day, 20-day
- Y-axis: Return %
- Two bar series: "Avg Pick Return" (blue) and "Benchmark" (orange)
- Legend at top

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

interface ChartData {
  window: string;
  avgPickReturn: number | null;
  benchmarkReturn: number | null;
}
```

#### 12. `frontend/src/types.ts` — Extended types

```typescript
export interface BacktestPick {
  rank: number;
  symbol: string;
  company_name: string;
  score: number;
  close: number;
  forward_return_5d: number | null;
  forward_return_10d: number | null;
  forward_return_20d: number | null;
}

export interface BenchmarkReturns {
  return_5d: number | null;
  return_10d: number | null;
  return_20d: number | null;
}

export interface PrecisionRecall {
  precision_5d: number | null;
  precision_10d: number | null;
  precision_20d: number | null;
  recall_5d: number | null;
  recall_10d: number | null;
  recall_20d: number | null;
}

export interface BacktestResult {
  backtest_date: string;
  picks: BacktestPick[];
  benchmark_returns: BenchmarkReturns;
  total_qualified: number;
  precision_recall: PrecisionRecall;
}
```

## Data Models

### API Response Schema

```json
{
  "backtest_date": "2025-01-15",
  "total_qualified": 42,
  "picks": [
    {
      "rank": 1,
      "symbol": "RELIANCE.NS",
      "company_name": "Reliance Industries",
      "score": 100,
      "close": 2450.50,
      "sma50": 2380.25,
      "sma200": 2250.10,
      "volume_ratio": 2.35,
      "pct_from_52w_high": 5.20,
      "forward_return_5d": 2.45,
      "forward_return_10d": 4.12,
      "forward_return_20d": -1.30
    }
  ],
  "benchmark_returns": {
    "return_5d": 1.20,
    "return_10d": 2.05,
    "return_20d": 0.85
  },
  "precision_recall": {
    "precision_5d": 70.00,
    "precision_10d": 60.00,
    "precision_20d": 80.00,
    "recall_5d": 23.33,
    "recall_10d": 18.75,
    "recall_20d": 25.00
  }
}
```

### Internal Data Flow

```
target_date (date)
    │
    ▼
fetch_ohlcv_range(symbol, start, end=today, sem) — for ALL Nifty 100 symbols
    │ returns full DataFrame (start..today)
    ▼
truncate: df[df.index <= target_date]
    │ → scoring_df (used for indicators/scoring)
    ▼
compute_indicators(symbol, scoring_df) → Indicators | None
    │
    ▼
rank_stocks(indicators, company_names, top_n=10)
    │ → top 10 ScoredStock + all qualified indicators
    ▼
For ALL qualified symbols (not just top 10):
    forward_df = df[df.index > target_date]
    compute_forward_returns_for_symbol(target_date, forward_df["Close"], (5,10,20))
    │ → ForwardReturns per symbol
    ▼
For benchmark (^NSEI):
    compute_forward_returns_for_symbol(target_date, benchmark_df["Close"], (5,10,20))
    │ → ForwardReturns
    ▼
compute_precision_recall(pick_forward_returns, all_forward_returns)
    │ → PrecisionRecall
    ▼
BacktestResult (includes picks, benchmark, precision_recall)
```

## Interfaces

### `fetch_ohlcv_range`

```python
async def fetch_ohlcv_range(
    symbol: str,
    start: date,
    end: date,
    sem: asyncio.Semaphore,
) -> pd.DataFrame | None:
```

- `start`: First calendar date to fetch (inclusive)
- `end`: Last calendar date to fetch (inclusive). Translated to `end + 1 day` for yfinance exclusive end.
- Returns DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume], or None on failure.

### `compute_forward_return`

```python
def compute_forward_return(close_base: float, close_future: float) -> float:
```

- Pure function, no side effects.
- `close_base` must be > 0 (caller validates).
- Returns percentage rounded to 2 decimal places.

### `compute_forward_returns_for_symbol`

```python
def compute_forward_returns_for_symbol(
    backtest_date: date,
    forward_prices: pd.Series,
    windows: tuple[int, ...] = (5, 10, 20),
) -> ForwardReturns:
```

- `forward_prices`: Series indexed by date, containing closing prices from backtest_date onward.
- Counts trading days from backtest_date using `is_trading_day`.
- Returns `ForwardReturns` with `None` for any window without sufficient data.

### `classify_true_bullish`

```python
def classify_true_bullish(forward_return: float | None) -> bool | None:
```

- Pure function. Returns `True` if return > 0%, `False` if <= 0%, `None` if data unavailable.

### `compute_precision`

```python
def compute_precision(true_bullish_picks: int) -> float:
```

- Pure function. Denominator is always 10 (fixed top-pick count).
- Returns percentage rounded to 2 decimal places.
- Result is always in [0, 100].

### `compute_recall`

```python
def compute_recall(true_bullish_picks: int, total_true_bullish: int) -> float | None:
```

- Pure function. Returns `None` if `total_true_bullish` is 0.
- Returns percentage rounded to 2 decimal places.
- Result is in [0, 100] when not None.

### `compute_precision_recall`

```python
def compute_precision_recall(
    pick_forward_returns: list[ForwardReturns],
    all_forward_returns: list[ForwardReturns],
) -> PrecisionRecall:
```

- `pick_forward_returns`: exactly 10 entries (the top picks).
- `all_forward_returns`: forward returns for ALL qualified symbols (includes picks).
- Computes independently for each window.
- Returns `None` for a window if forward return data is unavailable for that window.

### `run_backtest`

```python
async def run_backtest(target_date: date) -> BacktestResult:
```

- Raises `RuntimeError` if all symbols fail.
- Raises `ValueError` if target_date is today or in the future.
- Returns `BacktestResult` including `precision_recall` field.

### `backtest_endpoint`

```python
@router.get("/api/backtest")
async def backtest_endpoint(date: str = Query(...)) -> JSONResponse:
```

- HTTP 200: successful result (includes `precision_recall` in response body)
- HTTP 400: date is today or future
- HTTP 422: invalid date format
- HTTP 503: engine fatal error

## Error Handling

| Scenario | Backend Behavior | HTTP Status | Frontend Display |
|----------|-----------------|-------------|------------------|
| Invalid date format | FastAPI validation rejects | 422 | Alert with format error |
| Date is today or future | Router validates and rejects | 400 | Alert with "date must be in the past" |
| Single symbol fails fetch | Skip symbol, continue scan | — (internal) | — |
| All symbols fail fetch | Engine raises RuntimeError | 503 | Alert with "scan failed" |
| Forward data unavailable | Return null for that window | 200 (null fields) | "N/A" in table cell |
| Benchmark data unavailable | Return null for benchmark | 200 (null fields) | "N/A" in chart tooltip |
| No True_Bullish stocks (recall denominator=0) | Return null for recall | 200 (null recall) | "N/A" for recall metric |
| Forward data unavailable for precision/recall | Return null for both metrics | 200 (null fields) | "N/A" in metrics panel |
| Network timeout to yfinance | Per-symbol timeout, skip | — (internal) | — |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Data truncation excludes future data

*For any* OHLCV DataFrame with a DatetimeIndex and *for any* backtest date, after truncation to that date, no row in the resulting DataFrame shall have an index date strictly greater than the backtest date.

**Validates: Requirements 1.2**

### Property 2: Forward return formula correctness

*For any* pair of positive floats (close_base, close_future) where close_base > 0, `compute_forward_return(close_base, close_future)` shall equal `round(((close_future - close_base) / close_base) * 100, 2)`.

**Validates: Requirements 3.2, 4.2**

### Property 3: Trading day forward counting skips non-trading days

*For any* valid date and positive integer N, counting N trading days forward from that date shall produce a date that is itself a trading day, and the number of trading days in the range (start_date, result_date] shall equal exactly N.

**Validates: Requirements 3.4**

### Property 4: Null forward returns for insufficient data

*For any* backtest date and price series where the number of trading days after the backtest date is less than N, the N-day forward return shall be `None`.

**Validates: Requirements 3.3, 4.3**

### Property 5: Date validation rejects invalid inputs

*For any* string that does not match the pattern `YYYY-MM-DD` (where Y, M, D are valid date components), the backtest API shall return HTTP 422. *For any* date that is today or in the future, the backtest API shall return HTTP 400.

**Validates: Requirements 5.3, 5.4**

### Property 6: Return formatting with sign indicator

*For any* numeric forward return value, the formatted display string shall match the pattern `[+-]X.XX%` — a sign character followed by the absolute value with exactly two decimal places and a percent sign.

**Validates: Requirements 7.4**

### Property 7: Precision and recall bounds and formula correctness

*For any* list of 10 pick forward returns and *for any* list of all-symbol forward returns:

1. When precision is not null, it shall be in the range [0, 100] with denominator fixed at 10 (i.e., `precision = count(pick_returns > 0) / 10 * 100`).
2. When recall is not null, it shall be in the range [0, 100] with denominator equal to the count of all symbols with forward return > 0% (i.e., `recall = count(pick_returns > 0) / count(all_returns > 0) * 100`).
3. When no symbol in the full universe has forward return > 0%, recall shall be `None`.
4. When forward return data is unavailable (null) for a given window, both precision and recall shall be `None` for that window.

**Validates: Requirements 10.2, 10.3, 10.4, 10.5, 10.6**

### Property 8: True_Bullish classification correctness

*For any* forward return value, the stock shall be classified as True_Bullish if and only if the return is strictly greater than 0%. A return of exactly 0% is not True_Bullish. A null return results in null classification.

**Validates: Requirements 10.2**

### Property 9: Precision/recall independence across windows

*For any* set of forward returns, the precision and recall computed for the 5-day window shall depend only on 5-day returns, the 10-day metrics only on 10-day returns, and the 20-day metrics only on 20-day returns. Changing one window's data shall not affect another window's metrics.

**Validates: Requirements 10.7**
