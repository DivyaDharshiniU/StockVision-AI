# Implementation Plan: Backtest Evaluation

## Overview

Implements a backtest evaluation pipeline that reuses the existing scoring model against historical data, computes forward returns for all qualified Nifty 100 symbols, calculates precision/recall metrics, and displays results in a dedicated frontend tab. The plan is structured bottom-up: pure functions first, then orchestration, API layer, and finally frontend components.

## Tasks

- [x] 1. Implement pure computation modules
  - [x] 1.1 Create `backend/forward_returns.py` with ForwardReturns dataclass and pure computation functions
    - Define `ForwardReturns` dataclass with `return_5d`, `return_10d`, `return_20d` (all `float | None`)
    - Implement `compute_forward_return(close_base, close_future) -> float` using formula `round(((future - base) / base) * 100, 2)`
    - Implement `compute_forward_returns_for_symbol(backtest_date, price_series, windows=(5,10,20)) -> ForwardReturns` that counts trading days forward using `is_trading_day` and returns None for insufficient data
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 1.2 Create `backend/precision_recall.py` with PrecisionRecall dataclass and pure metric functions
    - Define `PrecisionRecall` dataclass with `precision_5d`, `precision_10d`, `precision_20d`, `recall_5d`, `recall_10d`, `recall_20d` (all `float | None`)
    - Implement `classify_true_bullish(forward_return: float | None) -> bool | None` — returns True if > 0%, False if <= 0%, None if None
    - Implement `compute_precision(true_bullish_picks: int) -> float` — denominator fixed at 10
    - Implement `compute_recall(true_bullish_picks: int, total_true_bullish: int) -> float | None` — returns None if denominator is 0
    - Implement `compute_precision_recall(pick_forward_returns, all_forward_returns) -> PrecisionRecall` — computes independently per window
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 1.3 Add `fetch_ohlcv_range` function to `backend/data_fetcher.py`
    - Add `async def fetch_ohlcv_range(symbol, start, end, sem) -> pd.DataFrame | None`
    - Use `yf.Ticker(symbol).history(start=..., end=...)` with end + 1 calendar day (yfinance exclusive end)
    - Reuse existing ThreadPoolExecutor and semaphore pattern
    - Return DataFrame with DatetimeIndex and [Open, High, Low, Close, Volume] columns, or None on failure
    - _Requirements: 1.1, 1.4_

- [ ] 2. Property tests for pure functions
  - [ ]* 2.1 Write property test for forward return formula correctness
    - **Property 2: Forward return formula correctness**
    - Use Hypothesis to generate pairs of positive floats, verify `compute_forward_return` matches `round(((future - base) / base) * 100, 2)`
    - **Validates: Requirements 3.2, 4.2**

  - [ ]* 2.2 Write property test for data truncation excluding future data
    - **Property 1: Data truncation excludes future data**
    - Generate DataFrames with DatetimeIndex and a backtest date, verify no row after truncation has index > backtest_date
    - **Validates: Requirements 1.2**

  - [ ]* 2.3 Write property test for null forward returns with insufficient data
    - **Property 4: Null forward returns for insufficient data**
    - Generate price series shorter than N trading days, verify N-day return is None
    - **Validates: Requirements 3.3, 4.3**

  - [ ]* 2.4 Write property test for precision/recall bounds and formula correctness
    - **Property 7: Precision and recall bounds and formula correctness**
    - Generate lists of ForwardReturns (10 picks + variable all-symbols), verify precision in [0,100], recall in [0,100] or None, and correct formulas
    - **Validates: Requirements 10.2, 10.3, 10.4, 10.5, 10.6**

  - [ ]* 2.5 Write property test for True_Bullish classification correctness
    - **Property 8: True_Bullish classification correctness**
    - Generate float | None values, verify classify_true_bullish returns True iff > 0, False iff <= 0, None iff None
    - **Validates: Requirements 10.2**

  - [ ]* 2.6 Write property test for precision/recall independence across windows
    - **Property 9: Precision/recall independence across windows**
    - Generate two sets of ForwardReturns differing only in one window, verify other windows' metrics are unchanged
    - **Validates: Requirements 10.7**

- [x] 3. Checkpoint — Ensure all backend pure function tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement backtest engine orchestrator
  - [x] 4.1 Create `backend/backtest_engine.py` with BacktestPick, BacktestResult dataclasses and `run_backtest` function
    - Define `BacktestPick` dataclass (rank, symbol, company_name, score, close, sma50, sma200, volume_ratio, pct_from_52w_high, forward_returns)
    - Define `BacktestResult` dataclass (backtest_date, picks, benchmark_returns, total_qualified, precision_recall)
    - Implement `run_backtest(target_date: date) -> BacktestResult`:
      1. Validate target_date is in the past
      2. Compute fetch range: start = target_date - 252 trading days, end = today
      3. Fetch OHLCV for all Nifty 100 symbols using `fetch_ohlcv_range`
      4. Truncate each DataFrame to backtest_date for scoring
      5. Compute indicators and rank → top 10 picks
      6. Compute forward returns for ALL qualified symbols (not just top 10)
      7. Compute forward returns for benchmark ^NSEI
      8. Compute precision/recall using `compute_precision_recall`
      9. Assemble and return BacktestResult
    - Raise RuntimeError if all symbols fail, ValueError if date is today/future
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.4, 4.1, 4.2, 4.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 5. Implement API endpoint and mount router
  - [x] 5.1 Create `backend/backtest_router.py` with GET /api/backtest endpoint
    - Accept `date` query parameter in YYYY-MM-DD format
    - Validate date format (422 if invalid)
    - Validate date is in the past (400 if today or future)
    - Call `run_backtest(target_date)` and serialize BacktestResult to JSON
    - Return 503 on engine RuntimeError
    - Include `precision_recall` object in response body
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 5.2 Mount backtest router in `backend/main.py`
    - Import `backtest_router` and call `app.include_router(backtest_router.router)`
    - _Requirements: 5.1_

  - [ ]* 5.3 Write property test for date validation
    - **Property 5: Date validation rejects invalid inputs**
    - Generate invalid date strings and future dates, verify correct HTTP status codes
    - **Validates: Requirements 5.3, 5.4**

- [x] 6. Checkpoint — Ensure backend integration is complete and tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement frontend types and tab navigation
  - [x] 7.1 Extend `frontend/src/types.ts` with backtest interfaces
    - Add `BacktestPick` interface (rank, symbol, company_name, score, close, forward_return_5d, forward_return_10d, forward_return_20d)
    - Add `BenchmarkReturns` interface (return_5d, return_10d, return_20d — all `number | null`)
    - Add `PrecisionRecall` interface (precision_5d, precision_10d, precision_20d, recall_5d, recall_10d, recall_20d — all `number | null`)
    - Add `BacktestResult` interface (backtest_date, picks, benchmark_returns, total_qualified, precision_recall)
    - _Requirements: 5.2, 10.3, 10.4, 11.1_

  - [x] 7.2 Refactor `frontend/src/App.tsx` to use Cloudscape Tabs navigation
    - Wrap existing scan UI in a `ScanView` component (inline or extracted)
    - Add Cloudscape `Tabs` with "Live Scan" and "Backtest" tabs
    - Import and render `BacktestPage` in the Backtest tab
    - Preserve component state when switching tabs
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 8. Implement frontend components
  - [x] 8.1 Create `frontend/src/components/BacktestPage.tsx`
    - Cloudscape DatePicker for selecting backtest date (restrict to past dates)
    - "Run Backtest" Button triggers API call to GET /api/backtest?date=YYYY-MM-DD
    - Loading state with Spinner, error state with Alert
    - Render PrecisionRecallPanel (prominent, above table), BacktestTable, and BacktestChart when results available
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 8.2 Create `frontend/src/components/BacktestTable.tsx`
    - Cloudscape Table with columns: Rank, Symbol, Company, Score, Close, 5d Return, 10d Return, 20d Return
    - Format returns as percentages with sign indicator (+/-) and two decimal places
    - Display "N/A" for null forward return values
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 8.3 Create `frontend/src/components/BacktestChart.tsx`
    - Recharts BarChart with grouped bars: "Avg Pick Return" (blue) vs "Benchmark" (orange)
    - X-axis: 5-day, 10-day, 20-day windows
    - Y-axis: Return percentage
    - Legend at top; Tooltip on hover
    - Handle null values gracefully
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 8.4 Create `frontend/src/components/PrecisionRecallPanel.tsx`
    - Cloudscape Container with Header "Model Accuracy"
    - ColumnLayout (3 columns) for 5d, 10d, 20d windows
    - Display precision and recall for each window using Box + StatusIndicator
    - Color coding: green (>=70%), yellow (>=40%), red (<40%), info for N/A
    - Format as percentages with two decimal places; show "N/A" for null
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 9. Frontend tests
  - [ ]* 9.1 Write property test for return formatting with sign indicator
    - **Property 6: Return formatting with sign indicator**
    - Use fast-check to generate numeric values, verify formatted string matches `[+-]X.XX%` pattern
    - **Validates: Requirements 7.4**

  - [ ]* 9.2 Write unit tests for PrecisionRecallPanel rendering
    - Test that all six metrics render correctly with valid values
    - Test N/A display when values are null
    - Test color coding thresholds (green/yellow/red)
    - _Requirements: 11.1, 11.3, 11.4_

- [x] 10. Final checkpoint — Ensure all tests pass end-to-end
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The backtest engine computes forward returns for ALL qualified symbols (not just top 10) — this is required for the recall denominator
- Pure functions (`forward_returns.py`, `precision_recall.py`) have no I/O and are trivially testable
- Frontend uses Cloudscape components exclusively (no custom CSS)
- Backend uses Python 3.11+ with Hypothesis for property-based testing; Frontend uses Vitest with fast-check

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"] },
    { "id": 2, "tasks": ["4.1"] },
    { "id": 3, "tasks": ["5.1", "7.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "7.2"] },
    { "id": 5, "tasks": ["8.1", "8.2", "8.3", "8.4"] },
    { "id": 6, "tasks": ["9.1", "9.2"] }
  ]
}
```
