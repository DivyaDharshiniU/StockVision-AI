# Requirements Document

## Introduction

The Backtesting / Evaluation feature allows users to validate the StockVision AI bullish scoring model by comparing predicted bullish scores against actual forward market performance. A user selects a single past trading date, and the system runs the existing scoring pipeline against OHLCV data available as of that date—producing the top 10 ranked picks based on the model's bullish score predicted for that historical date. The system then measures actual performance by computing real forward returns at 5, 10, and 20 trading days after the backtest date for each pick, the benchmark, and all Nifty 100 stocks. This enables a direct comparison: "what the model predicted as bullish" versus "what actually happened in the market." The system also computes precision and recall metrics to quantify how well the model's top picks aligned with stocks that actually delivered positive returns. Results are displayed on a dedicated frontend page with a date picker, results table, precision/recall metrics, and a chart comparing pick returns versus benchmark returns.

## Glossary

- **Backtest_Engine**: The backend module responsible for orchestrating a historical scan—truncating OHLCV data to a target date, scoring stocks, computing forward returns, and computing precision/recall metrics.
- **Backtest_API**: The FastAPI endpoint (`GET /api/backtest`) that accepts a date parameter and returns backtest results including precision/recall metrics.
- **Backtest_Page**: The dedicated frontend page/tab that provides the date picker, results table, precision/recall display, and comparison chart for backtesting.
- **Forward_Return**: The percentage price change of a stock from the backtest date closing price to the closing price N trading days later, representing actual market performance after the prediction date.
- **Benchmark_Return**: The percentage price change of the Nifty 100 index (^NSEI) from the backtest date closing price to the closing price N trading days later.
- **Trading_Day**: A day on which the NSE is open for trading, excluding weekends and market holidays.
- **Backtest_Date**: The user-selected past trading date as of which the scoring model is evaluated. The model scores stocks using data available up to this date, then actual performance is measured forward from this date.
- **Pick**: A stock that appears in the top 10 ranked results after scoring as of the Backtest_Date.
- **True_Bullish**: A stock whose actual Forward_Return is strictly greater than 0% (positive return) for a given window.
- **Precision**: The fraction of top-10 picks that were True_Bullish, calculated as (number of picks with Forward_Return > 0%) / 10.
- **Recall**: The fraction of all True_Bullish stocks in the Nifty 100 universe that were captured by the top-10 picks, calculated as (number of picks with Forward_Return > 0%) / (total Nifty 100 stocks with Forward_Return > 0%).

## Requirements

### Requirement 1: Historical Data Fetching

**User Story:** As a user, I want the system to fetch OHLCV data up to a specified past date, so that the scoring model can be evaluated using only information available at that point in time.

#### Acceptance Criteria

1. WHEN a backtest is requested for a Backtest_Date, THE Backtest_Engine SHALL fetch OHLCV data for each Nifty 100 symbol covering at least 252 trading days ending on or before the Backtest_Date.
2. THE Backtest_Engine SHALL truncate fetched OHLCV data to exclude any rows dated after the Backtest_Date.
3. IF a symbol has fewer than 150 bars of data after truncation, THEN THE Backtest_Engine SHALL exclude that symbol from scoring.
4. THE Backtest_Engine SHALL use the same concurrency-limiting semaphore pattern as the live scan to cap parallel yfinance downloads.

### Requirement 2: Historical Scoring

**User Story:** As a user, I want the system to score stocks using the existing bullish model against historical data, so that I can see what the model would have predicted as bullish on a past date.

#### Acceptance Criteria

1. WHEN historical OHLCV data is available for a symbol as of the Backtest_Date, THE Backtest_Engine SHALL compute indicators using the same `compute_indicators` function used by the live scan.
2. THE Backtest_Engine SHALL score and rank all qualified symbols using the same `rank_stocks` function, returning the top 10 picks ordered by score with ties broken by volume ratio.
3. THE Backtest_Engine SHALL include the same fields per pick as the live scan: rank, symbol, company_name, score, close, sma50, sma200, volume_ratio, and pct_from_52w_high.

### Requirement 3: Forward Return Computation

**User Story:** As a user, I want to see actual forward returns for each pick at 5, 10, and 20 trading days after the prediction date, so that I can evaluate how the model's predicted bullish picks actually performed.

#### Acceptance Criteria

1. WHEN the top 10 picks are determined, THE Backtest_Engine SHALL compute the Forward_Return for each pick at 5, 10, and 20 trading days after the Backtest_Date.
2. THE Backtest_Engine SHALL calculate Forward_Return as `((close_at_N - close_at_backtest_date) / close_at_backtest_date) * 100`, expressed as a percentage rounded to two decimal places.
3. IF forward price data is not available for a given window (the Backtest_Date is too recent), THEN THE Backtest_Engine SHALL return `null` for that Forward_Return window.
4. THE Backtest_Engine SHALL use actual trading day closing prices, skipping non-trading days when counting forward days.

### Requirement 4: Benchmark Comparison

**User Story:** As a user, I want to compare pick returns against the Nifty 100 benchmark, so that I can assess whether the model adds value over a passive index strategy.

#### Acceptance Criteria

1. WHEN forward returns are computed for picks, THE Backtest_Engine SHALL also compute Benchmark_Return for the ^NSEI index at 5, 10, and 20 trading days after the Backtest_Date.
2. THE Backtest_Engine SHALL calculate Benchmark_Return using the same formula as Forward_Return.
3. IF benchmark price data is not available for a given window, THEN THE Backtest_Engine SHALL return `null` for that Benchmark_Return window.

### Requirement 5: Backtest API Endpoint

**User Story:** As a frontend developer, I want a single API endpoint that accepts a date and returns backtest results, so that the frontend can display historical evaluation data.

#### Acceptance Criteria

1. THE Backtest_API SHALL expose a `GET /api/backtest` endpoint accepting a `date` query parameter in `YYYY-MM-DD` format.
2. WHEN a valid Backtest_Date is provided, THE Backtest_API SHALL return a JSON response containing: the backtest date, the list of top 10 picks with forward returns at 5, 10, and 20 days, the benchmark returns at 5, 10, and 20 days, the total number of qualified symbols, and precision/recall metrics for each window.
3. IF the `date` parameter is missing or not in `YYYY-MM-DD` format, THEN THE Backtest_API SHALL return HTTP 422 with a descriptive error message.
4. IF the `date` parameter is a future date or today, THEN THE Backtest_API SHALL return HTTP 400 with an error message indicating the date must be in the past.
5. IF the Backtest_Engine encounters a fatal error where all symbols fail data retrieval, THEN THE Backtest_API SHALL return HTTP 503 with an error message.
6. THE Backtest_API SHALL return the response within 60 seconds for a single-date backtest request.

### Requirement 6: Date Selection Interface

**User Story:** As a user, I want to select a past trading date using a date picker, so that I can choose which historical date to evaluate.

#### Acceptance Criteria

1. THE Backtest_Page SHALL display a Cloudscape DatePicker component for selecting the Backtest_Date.
2. THE Backtest_Page SHALL restrict date selection to dates in the past (before today).
3. WHEN the user selects a date and triggers the backtest, THE Backtest_Page SHALL send a request to the Backtest_API with the selected date.
4. WHILE the backtest request is in progress, THE Backtest_Page SHALL display a loading indicator.
5. IF the Backtest_API returns an error, THEN THE Backtest_Page SHALL display the error message in a Cloudscape Alert component.

### Requirement 7: Results Table Display

**User Story:** As a user, I want to see backtest results in a structured table showing picks with their forward returns, so that I can quickly scan model performance.

#### Acceptance Criteria

1. WHEN backtest results are returned successfully, THE Backtest_Page SHALL display a Cloudscape Table containing all 10 picks.
2. THE Backtest_Page SHALL display the following columns for each pick: rank, symbol, company name, score, close price at backtest date, forward return at 5 days, forward return at 10 days, and forward return at 20 days.
3. WHEN a forward return value is `null`, THE Backtest_Page SHALL display "N/A" in the corresponding cell.
4. THE Backtest_Page SHALL format forward return values as percentages with two decimal places and a sign indicator (+ or -).

### Requirement 8: Performance Comparison Chart

**User Story:** As a user, I want a visual chart comparing pick returns against the benchmark, so that I can quickly assess relative model performance.

#### Acceptance Criteria

1. WHEN backtest results are returned successfully, THE Backtest_Page SHALL display a Recharts bar chart or line chart comparing average pick returns versus benchmark returns.
2. THE Backtest_Page SHALL show three grouped data points on the chart corresponding to the 5-day, 10-day, and 20-day return windows.
3. THE Backtest_Page SHALL visually distinguish pick returns from benchmark returns using different colors or bar groupings.
4. THE Backtest_Page SHALL display a chart legend identifying the pick series and benchmark series.

### Requirement 9: Navigation to Backtest Page

**User Story:** As a user, I want to navigate between the live scan view and the backtest view, so that I can switch contexts without losing state.

#### Acceptance Criteria

1. THE Backtest_Page SHALL be accessible via a dedicated tab or navigation element in the application.
2. WHEN the user navigates to the Backtest_Page, THE application SHALL render the date picker and an empty results area.
3. WHEN the user navigates back to the live scan view, THE application SHALL display the existing scan interface without re-fetching data unnecessarily.

### Requirement 10: Precision and Recall Computation

**User Story:** As a user, I want precision and recall metrics computed for the model's top-10 picks, so that I can quantify how accurately the predicted bullish scores identified stocks that actually delivered positive returns.

#### Acceptance Criteria

1. WHEN forward returns are computed for picks, THE Backtest_Engine SHALL also compute Forward_Return at 5, 10, and 20 trading days for all qualified Nifty 100 symbols (not only the top 10 picks).
2. WHEN forward returns are available for a given window, THE Backtest_Engine SHALL classify each stock as True_Bullish if its Forward_Return for that window is strictly greater than 0%.
3. WHEN True_Bullish classification is complete for a given window, THE Backtest_Engine SHALL compute Precision as (number of top-10 picks that are True_Bullish) divided by 10, expressed as a percentage rounded to two decimal places.
4. WHEN True_Bullish classification is complete for a given window, THE Backtest_Engine SHALL compute Recall as (number of top-10 picks that are True_Bullish) divided by (total number of qualified Nifty 100 symbols that are True_Bullish for that window), expressed as a percentage rounded to two decimal places.
5. IF no qualified Nifty 100 symbols are True_Bullish for a given window, THEN THE Backtest_Engine SHALL return `null` for Recall for that window.
6. IF forward return data is unavailable for a given window, THEN THE Backtest_Engine SHALL return `null` for both Precision and Recall for that window.
7. THE Backtest_Engine SHALL compute Precision and Recall independently for each of the three windows: 5-day, 10-day, and 20-day.

### Requirement 11: Precision and Recall Display

**User Story:** As a user, I want precision and recall percentages displayed prominently on the backtest page, so that I can immediately assess the model's prediction quality for each time horizon.

#### Acceptance Criteria

1. WHEN backtest results are returned successfully, THE Backtest_Page SHALL display Precision and Recall percentages for each of the three windows (5-day, 10-day, 20-day).
2. THE Backtest_Page SHALL display Precision and Recall values prominently above or adjacent to the results table, using a visually distinct section.
3. THE Backtest_Page SHALL format Precision and Recall as percentages with two decimal places (e.g., "70.00%").
4. WHEN Precision or Recall is `null` for a given window, THE Backtest_Page SHALL display "N/A" for that metric.
5. THE Backtest_Page SHALL label each metric clearly, including the window it corresponds to (e.g., "5d Precision", "10d Recall").
