# Implementation Plan: Bullish Stock Scanner

## Overview

This implementation plan breaks down the Bullish Stock Scanner MVP into discrete coding tasks following strict test-driven development (TDD) principles. **Unit testing is MANDATORY and IMMEDIATE** after each component implementation. No task is considered complete until implementation AND unit tests are both done with >80% coverage and all tests passing.

The tasks follow a bottom-up approach: starting with foundational components (data models, API client, utilities), building core business logic (indicator calculations, scoring), implementing the pipeline orchestration, and finally wiring up the API and frontend. Integration tests are added at key checkpoints when related components are complete.

## Tasks

- [x] 1. Set up project structure, foundational components, and testing framework
  - Create backend directory structure with subdirectories: `api/`, `core/`, `utils/`, `tests/`
  - Create `main.py`, `config.py`, and `requirements.txt` in the backend root
  - Set up configuration management to read `POLYGON_TOKEN` from the system environment (already set globally in zsh — no .env file required), plus optional `API_BASE_URL` (default: `https://api.massive.com/v2`) and `SERVER_PORT` (default: 8000)
  - Create basic logging configuration in `utils/logging.py`
  - Define all Pydantic models in `api/models.py`: ScanRequest, ScanResponse, MarketRegime, IndicatorSignals, TickerScore, ScanMetadata
  - Define internal data classes in appropriate modules: StockData, TechnicalIndicators
  - **Set up testing framework:**
    - Install pytest, pytest-asyncio, hypothesis, and pytest-cov
    - Create `tests/__init__.py` and subdirectories: `unit/`, `property/`, `integration/`
    - Configure pytest with async support
  - _Requirements: 10.1, 10.2, 10.3, 10.5, 9.6, 11.1, 11.2, 11.3, 11.4_

- [x] 2. Create and test REST API Client with connection pooling and caching
  - [x] 2.1 Create and test `core/api_client.py` with RestApiClient class
    - **Implement the component:**
      - Implement `__init__` with httpx.AsyncClient configuration (max 5 concurrent connections)
      - Implement `fetch_stock_data` method to call Polygon.io aggregates endpoint `/v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}`
      - Use authentication via API key from environment variable `POLYGON_TOKEN`
      - Add in-memory cache using dictionary keyed by (ticker, days)
      - Implement `clear_cache` method
      - Implement retry decorator or loop with exponential backoff (1s, 2s, 4s delays)
      - Add error logging for failed requests with ticker context
      - Handle API unavailability after 3 retries by marking ticker as unavailable
    - **Write unit tests** in `tests/unit/test_api_client.py`:
      - Test successful data fetch with mocked httpx responses
      - Test cache hit scenario (second request returns cached data)
      - Test error handling and retry attempts with exponential backoff
      - Test concurrent request limit enforcement
      - Test API unavailability handling after 3 retries
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - **Reference**: See `.kiro/skills/mcp-massive-financial-data-guide.md` for endpoint patterns and data structure reference
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 11.1, 11.2, 11.3, 11.4, 11.6_

  - [x] 2.2 Write property tests for API client
    - **Property 1: Concurrent Request Limit Enforcement**
    - **Validates: Requirements 1.2**
    - **Property 2: Retry Logic with Exponential Backoff**
    - **Validates: Requirements 1.4**
    - **Property 3: Session-Based Caching**
    - **Validates: Requirements 1.6**
    - _Requirements: 1.2, 1.4, 1.6_

- [x] 3. Create and test Universe Builder for ticker validation
  - [x] 3.1 Create and test `core/universe_builder.py` with UniverseBuilder class
    - **Implement the component:**
      - Implement `validate_ticker` static method with regex pattern `^[A-Z0-9]+$`
      - Implement `build_universe` method that requires a ticker list input, validates each ticker, filters invalid ones, and raises ValueError if input is empty or all tickers are invalid
      - Add logging for invalid tickers that are excluded
    - **Write unit tests** in `tests/unit/test_universe_builder.py`:
      - Test that valid tickers are preserved in output
      - Test that invalid tickers are filtered out with warnings logged
      - Test that ValueError is raised when input list is empty
      - Test that ValueError is raised when all tickers are invalid
      - Test alphanumeric validation with edge cases
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.1, 11.2, 11.3, 11.4_

  - [x] 3.2 Write property test for ticker validation
    - **Property 4: Ticker Validation and Filtering**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    - Test that only non-empty alphanumeric strings are included in universe and ValueError is raised for empty/all-invalid inputs
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3.3 Integration test: Universe Builder + API Client
  - **Write integration test** in `tests/integration/test_universe_api.py`:
    - Test building universe and fetching data for each ticker
    - Test that invalid tickers are filtered before API calls
    - Test error handling when API fails for specific tickers
  - _Requirements: 1.5, 2.3, 2.4_

- [x] 4. Create and test Technical Indicator Calculator
  - [x] 4.1 Create and test `core/indicator_calculator.py` with IndicatorCalculator class
    - **Implement the component:**
      - Implement `calculate_sma` static method: `sum(prices[-period:]) / period`
      - Implement `calculate_ema` static method: multiplier = 2/(period+1), EMA = (price * multiplier) + (previous_EMA * (1 - multiplier))
      - Implement `calculate_macd` static method: MACD Line = EMA(12) - EMA(26), Signal = EMA(9) of MACD, Histogram = MACD - Signal
      - Implement `calculate_avg_volume` static method: simple average of last N volumes
      - Implement `calculate_relative_strength` static method: (ticker_return - market_return) as percentage point difference
      - Implement `calculate_all` method that orchestrates all indicator calculations
      - Handle insufficient data by returning None for unavailable indicators
      - Add logging for unavailable indicators
    - **Write unit tests** in `tests/unit/test_indicator_calculator.py`:
      - Test SMA with known price sequences
      - Test EMA with known price sequences
      - Test MACD calculation with known inputs
      - Test average volume calculation
      - Test relative strength calculation
      - Test handling of insufficient data (returns None)
      - Test edge cases (empty arrays, single data point)
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - **Reference**: See technical indicator formulas in design.md section 4 (Indicator Calculator)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 11.1, 11.2, 11.3, 11.4_

  - [x] 4.2 Write property tests for indicator calculations
    - **Property 6: SMA Calculation Correctness**
    - **Validates: Requirements 4.1**
    - **Property 7: EMA Calculation Correctness**
    - **Validates: Requirements 4.2**
    - **Property 8: MACD Calculation Correctness**
    - **Validates: Requirements 4.3**
    - **Property 9: Average Volume Calculation Correctness**
    - **Validates: Requirements 4.4**
    - **Property 10: Relative Strength Calculation Correctness**
    - **Validates: Requirements 4.5**
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 5. Checkpoint - Ensure core calculations are working
  - Verify all unit tests pass with >80% coverage
  - Ensure all indicator calculations are tested and validated
  - Ask the user if questions arise before proceeding to regime and scoring components

- [x] 6. Create and test Market Regime Analyzer
  - [x] 6.1 Create and test `core/regime_analyzer.py` with MarketRegimeAnalyzer class
    - **Implement the component:**
      - Implement `__init__` to accept RestApiClient dependency
      - Implement `analyze_regime` async method to fetch SPY data
      - Calculate SMA_50 and SMA_200 for market index
      - Implement classification logic: bullish (SMA_50 > SMA_200), bearish (SMA_50 < SMA_200 * 0.98), neutral (within 2%)
      - Return MarketRegime enum value
    - **Write unit tests** in `tests/unit/test_regime_analyzer.py`:
      - Test bullish regime classification with mocked data
      - Test bearish regime classification with mocked data
      - Test neutral regime classification with boundary cases
      - Test handling of API failures (default to NEUTRAL)
      - Test SMA calculation accuracy
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.1, 11.2, 11.3, 11.4_

  - [x] 6.2 Write property test for market regime classification
    - **Property 5: Market Regime Classification**
    - **Validates: Requirements 3.2, 3.3, 3.4**
    - Test regime classification correctness across random SMA_50 and SMA_200 values
    - _Requirements: 3.2, 3.3, 3.4_

- [x] 7. Create and test Scoring Engine
  - [x] 7.1 Create and test `core/scoring_engine.py` with ScoringEngine class
    - **Implement the component:**
      - Implement `calculate_score` method accepting current_price, current_volume, and indicators
      - Implement scoring rules: price above SMA50 (+20), price above EMA20 (+15), MACD above signal (+20), MACD histogram positive (+10), volume surge (+15), positive relative strength (+20)
      - Handle None indicators by assigning 0 points
      - Return tuple of (total_score, IndicatorSignals)
    - **Write unit tests** in `tests/unit/test_scoring_engine.py`:
      - Test each individual scoring rule in isolation
      - Test total score calculation with all signals active
      - Test handling of missing indicators (None values)
      - Test score capping at 100
      - Test partial signal combinations
      - Test boundary conditions (e.g., volume exactly 120% of average)
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 11.1, 11.2, 11.3, 11.4_

  - [x] 7.2 Write property tests for scoring rules
    - **Property 11: Price Above SMA Scoring**
    - **Validates: Requirements 5.2**
    - **Property 12: Price Above EMA Scoring**
    - **Validates: Requirements 5.3**
    - **Property 13: MACD Above Signal Scoring**
    - **Validates: Requirements 5.4**
    - **Property 14: MACD Histogram Positive Scoring**
    - **Validates: Requirements 5.5**
    - **Property 15: Volume Surge Scoring**
    - **Validates: Requirements 5.6**
    - **Property 16: Relative Strength Positive Scoring**
    - **Validates: Requirements 5.7**
    - **Property 17: Score Aggregation and Capping**
    - **Validates: Requirements 5.8**
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [x] 8. Create and test Ranking Service
  - [x] 8.1 Create and test `core/ranking_service.py` with RankingService class
    - **Implement the component:**
      - Implement `rank_tickers` method using Python's stable sort
      - Sort by bullish_score in descending order
      - Return complete sorted list
    - **Write unit tests** in `tests/unit/test_ranking_service.py`:
      - Test descending sort by score
      - Test stable sort for equal scores (maintains original order)
      - Test all tickers are included in output (no filtering)
      - Test empty list handling
      - Test single ticker handling
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 11.1, 11.2, 11.3, 11.4_

  - [x] 8.2 Write property test for ranking correctness
    - **Property 18: Descending Score Sort with Complete Preservation**
    - **Validates: Requirements 6.1, 6.2, 6.4**
    - Test descending order and stable sort across random ticker lists
    - _Requirements: 6.1, 6.2, 6.4_

- [x] 8.3 Integration test: Indicator Calculator + Scoring Engine + Ranking Service
  - **Write integration test** in `tests/integration/test_scoring_pipeline.py`:
    - Test complete flow: calculate indicators → score tickers → rank results
    - Test with mixed valid/invalid indicators
    - Test ranking stability with tied scores
    - _Requirements: 4.7, 5.10, 6.4_

- [x] 9. Checkpoint - Ensure all core components are tested and working
  - Verify all unit tests pass with >80% coverage for each component
  - Verify integration tests pass for component interactions
  - Review test coverage report and address any gaps
  - Ask the user if questions arise before proceeding to orchestration layer

- [x] 10. Create and test Scan Orchestrator and API endpoints
  - [x] 10.1 Create and test `core/scan_store.py` with ScanStore class
    - **Implement the component:**
      - Implement `__init__` with configurable db_path (default: `scanner.db`)
      - Implement `initialize` async method to create `scan_results` table if not exists (columns: scan_id TEXT PK, result_json TEXT, created_at TEXT)
      - Implement `save` async method to persist a ScanResponse as JSON with a UUID key
      - Implement `get` async method to retrieve and deserialize a scan result by scan_id (return None if not found)
      - Use `aiosqlite` for async SQLite access
    - **Write unit tests** in `tests/unit/test_scan_store.py`:
      - Test table creation (initialize method)
      - Test save operation with UUID generation
      - Test retrieve by scan_id
      - Test not found handling (returns None)
      - Test JSON serialization roundtrip
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - _Requirements: 9.4, 9.5, 11.1, 11.2, 11.3, 11.4_

  - [x] 10.2 Create and test `core/orchestrator.py` with ScanOrchestrator class
    - **Implement the component:**
      - Implement `__init__` accepting all component dependencies (including ScanStore)
      - Implement `execute_scan` async method coordinating the full pipeline:
        - Validate that tickers list is provided (raise error if missing/empty for HTTP 400 response)
        - Clear API cache
        - Build universe from required ticker list input
        - Analyze market regime (can run in parallel with ticker processing)
        - For each ticker: fetch data, calculate indicators, calculate score
        - Handle per-ticker errors gracefully (log, continue)
        - Rank scored tickers
        - Generate UUID for scan, persist result via ScanStore
        - Build ScanResponse with scan_id and metadata (timestamp, ticker count, duration)
      - Handle critical failures (return HTTP 400 error if no tickers provided, return error if all tickers fail, default to NEUTRAL regime on failure)
    - **Write unit tests** in `tests/unit/test_orchestrator.py`:
      - Test pipeline execution flow with mocked dependencies
      - Test error handling per ticker (continues processing)
      - Test response formatting with metadata
      - Test metadata accuracy (timestamp, ticker count, duration)
      - Test validation error for missing/empty ticker list
      - Test all-ticker-failure handling
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - **Reference**: See pipeline flow and error handling in design.md section 7 (Scan Orchestrator)
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 5.9, 9.4, 11.1, 11.2, 11.3, 11.4_

  - [x] 10.3 Create and test `api/endpoints.py` with FastAPI route handlers
    - **Implement the component:**
      - Implement POST `/api/v1/scan` endpoint calling ScanOrchestrator with request validation
      - Return HTTP 400 error with validation message if tickers list is missing or empty
      - Implement GET `/api/v1/scan/{scan_id}` endpoint to retrieve a persisted scan result by UUID (return 404 if not found)
      - Implement GET `/api/v1/health` endpoint returning status
      - Configure CORS middleware for frontend access
      - Handle HTTP errors and return appropriate status codes (400 for validation, 404 for not found, 500 for server errors)
    - **Write unit tests** in `tests/unit/test_endpoints.py`:
      - Test POST /api/v1/scan with valid request
      - Test POST /api/v1/scan with missing ticker list (400 error)
      - Test POST /api/v1/scan with empty ticker list (400 error)
      - Test GET /api/v1/scan/{scan_id} success case
      - Test GET /api/v1/scan/{scan_id} not found (404 error)
      - Test GET /api/v1/health endpoint
      - Test CORS headers
    - **Run tests and verify >80% coverage**
    - **Task incomplete until all tests pass**
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.9, 9.5, 11.1, 11.2, 11.3, 11.4_

  - [x] 10.4 Set up and test FastAPI application in `main.py`
    - **Implement the component:**
      - Initialize FastAPI app with Swagger UI enabled at `/docs`
      - Instantiate all component dependencies with proper initialization
      - Initialize ScanStore and call `initialize()` on startup (creates table)
      - Include API router from endpoints
      - Configure CORS middleware
      - Add startup logging
    - **Write startup test** in `tests/integration/test_main.py`:
      - Test app initialization
      - Test dependency injection setup
      - Test ScanStore initialization on startup
      - Test Swagger UI availability at /docs
    - **Run tests and verify they pass**
    - **Task incomplete until all tests pass**
    - **Reference**: See API endpoint specifications in design.md section "API Endpoints"
    - _Requirements: 7.6, 7.7, 7.8, 9.4, 11.1, 11.2, 11.3, 11.4_

- [x] 10.5 Integration test: Full scan endpoint (end-to-end)
  - **Write comprehensive integration test** in `tests/integration/test_scan_endpoint.py`:
    - Test POST `/api/v1/scan` with valid ticker list returns valid ScanResponse with scan_id
    - Test POST `/api/v1/scan` with missing ticker list returns HTTP 400 error
    - Test POST `/api/v1/scan` with empty ticker list returns HTTP 400 error
    - Test GET `/api/v1/scan/{scan_id}` returns previously saved result
    - Test GET `/api/v1/scan/{scan_id}` returns 404 for unknown UUID
    - Test health endpoint returns 200
    - Test full pipeline: universe building → regime analysis → indicator calculation → scoring → ranking → persistence
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7, 9.4, 9.5_

- [x] 11. Set up React frontend with Cloudscape Design System
  - [x] 11.1 Initialize React project and install dependencies
    - Create frontend directory structure: `src/`, `src/components/`, `src/services/`, `src/types/`, `src/styles/`
    - Set up Vite with React and TypeScript
    - Install Cloudscape packages: `@cloudscape-design/components`, `@cloudscape-design/global-styles`, `@cloudscape-design/collection-hooks`
    - Create `package.json` with all dependencies
    - Configure environment variables (VITE_API_URL)
    - **Reference**: See frontend structure in design.md section "Frontend Design"
    - _Requirements: 8.9, 10.4, 10.6_

  - [x] 11.2 Define TypeScript types and implement API client service
    - **Implement TypeScript types** in `src/types/scan.ts`:
      - Create interfaces: ScanRequest, ScanResponse, MarketRegime, TickerScore, IndicatorSignals, ScanMetadata
      - Match backend Pydantic models exactly
    - **Implement API client** in `src/services/scanApi.ts`:
      - Create `executeScan` function using fetch API to call POST `/api/v1/scan`
      - Handle response parsing and error handling
      - Read API URL from environment variable
    - **Write tests** in `tests/services/scanApi.test.ts`:
      - Test successful API call
      - Test error handling
      - Test request formatting
    - **Run tests and verify they pass**
    - **Task incomplete until all tests pass**
    - _Requirements: 8.2, 8.5, 8.8, 10.4, 11.7_

  - [x] 11.3 Implement and test React components
    - **Implement components:**
      - Create `src/components/ScanButton.tsx` for triggering scans
      - Create `src/components/LoadingIndicator.tsx` for loading state
      - Create `src/components/MarketRegimeBadge.tsx` for regime display
      - Create `src/components/ResultsTable.tsx` for ranked ticker display with columns: rank, ticker, score, price, signals
      - Create `src/components/SignalBadges.tsx` for individual signal visualization
      - Create `src/components/ErrorMessage.tsx` for error display
      - Use Cloudscape Design System components throughout (AppLayout, Table, Button, Input, Alert, Spinner, Badge, StatusIndicator, SpaceBetween, Container, Header)
    - **Write component tests** in `tests/components/`:
      - Test ScanButton click handling
      - Test loading state display
      - Test results table rendering with data
      - Test error message display
      - Test MarketRegimeBadge for each regime type
    - **Run tests and verify they pass**
    - **Task incomplete until all tests pass**
    - **Reference**: See component structure and examples in design.md section "Frontend Design"
    - _Requirements: 8.1, 8.2, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 11.7_

  - [x] 11.4 Implement and test main App component
    - **Implement App component** in `src/App.tsx`:
      - Add state management for tickers input, loading, results, and errors
      - Add input field for entering comma or space-separated ticker symbols
      - Implement validation to ensure at least one ticker is provided before triggering scan
      - Display validation message if no tickers are entered when "Run Scan" is clicked
      - Implement `handleScan` function to trigger scan with provided ticker list and update state
      - Wire up all child components with proper props
      - Add basic styling in `src/styles/App.css`
    - **Write App tests** in `tests/App.test.tsx`:
      - Test input validation (no tickers entered)
      - Test scan trigger with valid tickers
      - Test loading state during scan
      - Test results display after successful scan
      - Test error display after failed scan
    - **Run tests and verify they pass**
    - **Task incomplete until all tests pass**
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.11, 11.7_

  - [x] 11.5 Create React entry point and verify build
    - Create `src/main.tsx` to render App component
    - Create `index.html` as HTML entry point
    - **Test build process:**
      - Run `npm run build` and verify successful build
      - Run `npm run dev` and verify dev server starts
      - Manually test basic UI functionality
    - _Requirements: 8.1_

  - [x] 11.6 Implement and run Playwright E2E functional tests with screenshots
    - **Set up Playwright:**
      - Install Playwright with `npm install -D @playwright/test`
      - Run `npx playwright install` to install browser binaries
      - Create `playwright.config.ts` configuration file with:
        - Base URL pointing to frontend dev server
        - Screenshot settings for test results
        - Test directory: `tests/e2e/`
        - Output directory: `test-results/`
    - **Implement 4 E2E test files** in `tests/e2e/`:
      - `happy-path.spec.ts`: Complete workflow test (enter tickers → run scan → verify results table, market regime badge, and ranked data display)
      - `error-scenarios.spec.ts`: Error handling tests (no tickers entered → verify validation message, invalid tickers → verify error handling)
      - `loading-states.spec.ts`: Loading state verification (verify spinner appears during scan, verify button disabled state during scan)
      - `results-display.spec.ts`: Results rendering tests (verify market regime badge displays correctly, verify results table shows all columns with correct data)
    - **Screenshot requirements:**
      - Each test must capture screenshots at key interaction points using `await page.screenshot()`
      - Save screenshots to `frontend/test-results/screenshots/` directory
      - Naming convention: `{test-file}-{test-name}-{step}.png`
      - Capture: initial state, after input, loading state, results displayed, error states
    - **Run E2E tests:**
      - Ensure backend server is running: `uvicorn main:app --reload` (in backend directory)
      - Ensure frontend dev server is running: `npm run dev` (in frontend directory)
      - Run tests: `npx playwright test`
      - Run in headed mode for debugging: `npx playwright test --headed`
      - Generate HTML report: `npx playwright show-report`
    - **Verify all tests pass:**
      - All 4 test files execute successfully
      - Screenshots are generated and saved to `test-results/screenshots/`
      - Test report shows 0 failures
    - **Task incomplete until:**
      - All E2E tests pass
      - Screenshots are captured and saved
      - Test report is generated successfully
    - **Commit screenshots to workspace** for documentation purposes
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 11.8, 11.9, 11.10, 11.11, 11.12_

  - [x] 11.7 Verify frontend build and deployment readiness
    - Previously task 11.6, renumbered to 11.7
    - Run final frontend build verification
    - Ensure production build works correctly
    - _Requirements: 8.1_

- [x] 12. Final integration, testing, and documentation
  - [x] 12.1 Create and verify requirements.txt
    - List all Python dependencies with versions
    - Test installation in clean virtual environment
    - **Run verification:**
      - Create fresh virtual environment
      - Install from requirements.txt
      - Run all tests to verify dependencies are correct
    - _Requirements: 10.5_

  - [x] 12.2 Update README with setup and run instructions
    - Add backend setup instructions (venv, dependencies, environment variables)
    - Add frontend setup instructions (npm install, environment variables)
    - Add run instructions for both backend and frontend
    - Document API endpoints
    - Add testing instructions
    - _Requirements: 10.7_

  - [x] 12.3 Final checkpoint - Run complete system end-to-end with all tests
    - **Backend verification:**
      - Run all unit tests: `pytest tests/unit/ --cov=. --cov-report=html`
      - Run all property tests: `pytest tests/property/`
      - Run all integration tests: `pytest tests/integration/`
      - Verify >80% coverage across all components
    - **Frontend verification:**
      - Run all component tests: `npm test`
      - Verify all tests pass
    - **End-to-end verification:**
      - Start backend server: `uvicorn main:app --reload`
      - Start frontend dev server: `npm run dev`
      - Execute scan through UI with test tickers
      - Verify results are displayed correctly
      - Test error scenarios (invalid tickers, empty input)
      - Verify all features work as expected
    - **Ask the user if questions arise or if any issues are found**
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.7_

## Notes

- **TDD is MANDATORY**: Unit tests are NOT optional. Every component implementation task includes unit testing as a required part of completion.
- **Definition of Done**: A task is NOT complete until:
  1. Component is implemented
  2. Unit tests are written
  3. Tests pass with >80% coverage
  4. All tests run successfully
- **Property tests marked with `*` are optional** for faster MVP delivery, but unit tests are REQUIRED
- **Integration tests** are added at checkpoints after related components are complete
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones and verify ALL tests pass
- Property tests validate mathematical correctness of calculations using hypothesis
- Unit tests validate specific functionality and edge cases
- Integration tests validate component interactions and the complete pipeline
- The implementation follows a bottom-up approach: foundations → core logic → orchestration → API → frontend
- All components are designed to be independently testable with clear interfaces
- Error handling is integrated throughout to ensure graceful degradation
- The 2-hour timeline is achievable by focusing on core functionality and deferring advanced features
- **Key requirement change**: Universe Builder now requires user-provided ticker list (no default tickers); API returns HTTP 400 if no tickers provided
- **New skill available**: `.kiro/skills/mcp-massive-financial-data-guide.md` provides patterns for financial API integration (for exploration/prototyping only - use direct API calls in production)
- **Test coverage target**: >80% for each component before proceeding to dependent tasks
- **No skipping tests**: Dependent tasks cannot start until prerequisite components are fully tested and passing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.3"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["4.2", "5"] },
    { "id": 5, "tasks": ["6.1", "7.1"] },
    { "id": 6, "tasks": ["6.2", "7.2", "8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "9"] },
    { "id": 8, "tasks": ["10.1", "10.2"] },
    { "id": 9, "tasks": ["10.3"] },
    { "id": 10, "tasks": ["10.4"] },
    { "id": 11, "tasks": ["10.5", "11.1"] },
    { "id": 12, "tasks": ["11.2"] },
    { "id": 13, "tasks": ["11.3"] },
    { "id": 14, "tasks": ["11.4"] },
    { "id": 15, "tasks": ["11.5", "12.1"] },
    { "id": 16, "tasks": ["11.6"] },
    { "id": 17, "tasks": ["11.7", "12.2"] },
    { "id": 18, "tasks": ["12.3"] }
  ]
}
```