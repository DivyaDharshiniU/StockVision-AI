# Requirements Document

## Introduction

The Bullish Stock Scanner is an MVP system designed to identify potentially bullish stocks through technical analysis. The system fetches stock data from a REST API, calculates core technical indicators, scores tickers based on bullish signals, and presents ranked results through both a backend API and a React frontend. The MVP focuses on essential indicators (SMA, EMA, MACD, Volume, Relative Strength) with a streamlined scoring methodology to deliver actionable insights within a 2-hour development timeline.

## Glossary

- **Scanner_Backend**: The FastAPI-based server that orchestrates data fetching, indicator calculation, scoring, and ranking
- **Scanner_Frontend**: The React-based user interface built with Cloudscape Design System (`@cloudscape-design/components`) for visualizing scan results
- **REST_API_Client**: The HTTP client component responsible for fetching stock data from the external market data API
- **Universe_Builder**: The component that constructs the list of tickers to analyze
- **Market_Regime_Analyzer**: The component that determines current market conditions (bullish, bearish, neutral)
- **Indicator_Calculator**: The component that computes technical indicators (SMA, EMA, MACD, Volume, RS)
- **Scoring_Engine**: The component that assigns bullish scores to tickers based on indicator signals
- **Ranking_Service**: The component that sorts and ranks tickers by their bullish scores
- **Scan_Session**: A single execution of the scanner from start to completion
- **Ticker**: A stock symbol representing a publicly traded company
- **Technical_Indicator**: A mathematical calculation based on price and volume data used to identify trading signals
- **Bullish_Score**: A numerical value (0-100) representing the strength of bullish signals for a ticker
- **API_Tier**: The paid subscription level allowing 5 concurrent API requests
- **Swagger_UI**: The automatically generated API documentation interface provided by FastAPI

## Requirements

### Requirement 1: API Data Integration

**User Story:** As a scanner operator, I want the system to fetch stock data from the REST API efficiently, so that I can analyze current market data without manual intervention.

#### Acceptance Criteria

1. THE REST_API_Client SHALL authenticate with the external REST API using provided credentials
2. WHERE API_Tier is paid tier, THE REST_API_Client SHALL maintain up to 5 concurrent requests to the external API
3. WHEN a data fetch request is initiated, THE REST_API_Client SHALL retrieve price and volume data for the specified ticker
4. WHEN the external API returns an error response, THE REST_API_Client SHALL log the error and retry the request up to 3 times with exponential backoff
5. IF the external API is unavailable after 3 retry attempts, THEN THE REST_API_Client SHALL mark the ticker as unavailable and continue processing remaining tickers
6. THE REST_API_Client SHALL cache fetched data in memory for the duration of the Scan_Session
7. WHEN a Scan_Session is initiated, THE REST_API_Client SHALL fetch data on-demand for each ticker as it is processed

### Requirement 2: Universe Building

**User Story:** As a scanner operator, I want to provide a specific list of tickers to analyze, so that the system processes only the stocks I'm interested in.

#### Acceptance Criteria

1. THE Universe_Builder SHALL require a list of ticker symbols as input
2. THE Universe_Builder SHALL validate that each ticker symbol is non-empty and contains only alphanumeric characters
3. IF a ticker symbol fails validation, THEN THE Universe_Builder SHALL log a warning and exclude the ticker from the universe
4. THE Universe_Builder SHALL return a list of valid ticker symbols for analysis

### Requirement 3: Market Regime Analysis

**User Story:** As a scanner operator, I want the system to determine current market conditions, so that scoring can be contextualized.

#### Acceptance Criteria

1. THE Market_Regime_Analyzer SHALL calculate a market-wide trend indicator using a broad market index (e.g., SPY)
2. WHEN the market index 50-day SMA is above the 200-day SMA, THE Market_Regime_Analyzer SHALL classify the regime as bullish
3. WHEN the market index 50-day SMA is below the 200-day SMA, THE Market_Regime_Analyzer SHALL classify the regime as bearish
4. WHEN the market index 50-day SMA is within 2% of the 200-day SMA, THE Market_Regime_Analyzer SHALL classify the regime as neutral
5. THE Market_Regime_Analyzer SHALL return the market regime classification (bullish, bearish, or neutral)

### Requirement 4: Technical Indicator Calculation

**User Story:** As a scanner operator, I want the system to compute core technical indicators for each ticker, so that bullish signals can be identified.

#### Acceptance Criteria

1. THE Indicator_Calculator SHALL compute the 50-day Simple Moving Average (SMA) for each ticker
2. THE Indicator_Calculator SHALL compute the 20-day Exponential Moving Average (EMA) for each ticker
3. THE Indicator_Calculator SHALL compute the MACD (12, 26, 9) indicator including MACD line, signal line, and histogram for each ticker
4. THE Indicator_Calculator SHALL compute the 20-day average volume for each ticker
5. THE Indicator_Calculator SHALL compute the Relative Strength (RS) by comparing the ticker's price performance to the market index over a 20-day period
6. WHEN insufficient historical data is available for a calculation, THE Indicator_Calculator SHALL mark the indicator as unavailable and log a warning
7. THE Indicator_Calculator SHALL return all calculated indicators for each ticker

### Requirement 5: Simplified Scoring

**User Story:** As a scanner operator, I want the system to assign bullish scores based on core indicators, so that I can quickly identify promising stocks.

#### Acceptance Criteria

1. THE Scoring_Engine SHALL assign points to each ticker based on bullish signals from technical indicators
2. WHEN the current price is above the 50-day SMA, THE Scoring_Engine SHALL add 20 points to the Bullish_Score
3. WHEN the current price is above the 20-day EMA, THE Scoring_Engine SHALL add 15 points to the Bullish_Score
4. WHEN the MACD line is above the signal line, THE Scoring_Engine SHALL add 20 points to the Bullish_Score
5. WHEN the MACD histogram is positive, THE Scoring_Engine SHALL add 10 points to the Bullish_Score
6. WHEN the current volume is above the 20-day average volume by at least 20%, THE Scoring_Engine SHALL add 15 points to the Bullish_Score
7. WHEN the Relative Strength is positive (ticker outperforming the market), THE Scoring_Engine SHALL add 20 points to the Bullish_Score
8. THE Scoring_Engine SHALL calculate the total Bullish_Score as the sum of all earned points with a maximum of 100
9. IF any indicator is unavailable, THEN THE Scoring_Engine SHALL assign 0 points for that indicator and continue scoring with available indicators
10. THE Scoring_Engine SHALL return the Bullish_Score and contributing indicator signals for each ticker

### Requirement 6: Ranking and Results

**User Story:** As a scanner operator, I want the system to rank tickers by their bullish scores, so that I can prioritize the most promising opportunities.

#### Acceptance Criteria

1. THE Ranking_Service SHALL sort all scored tickers in descending order by Bullish_Score
2. WHEN multiple tickers have identical Bullish_Score values, THE Ranking_Service SHALL maintain their relative order from the original universe
3. THE Ranking_Service SHALL include the ticker symbol, Bullish_Score, and indicator breakdown in the ranked results
4. THE Ranking_Service SHALL return the complete ranked list of tickers

### Requirement 7: FastAPI Backend

**User Story:** As a frontend developer or API consumer, I want a RESTful API to trigger scans and retrieve results, so that I can integrate the scanner into applications.

#### Acceptance Criteria

1. THE Scanner_Backend SHALL expose a POST endpoint at `/api/v1/scan` to initiate a Scan_Session
2. WHEN a POST request is received at `/api/v1/scan`, THE Scanner_Backend SHALL require a list of ticker symbols in the request body
3. IF no ticker list is provided in the request, THEN THE Scanner_Backend SHALL return an HTTP 400 error with a validation message
4. WHEN a scan is initiated, THE Scanner_Backend SHALL execute the complete pipeline: universe building, market regime analysis, indicator calculation, scoring, and ranking
5. WHEN the scan completes successfully, THE Scanner_Backend SHALL return a JSON response containing the market regime, ranked tickers with scores and indicator breakdowns, and scan metadata (timestamp, ticker count)
6. IF an error occurs during the scan, THEN THE Scanner_Backend SHALL return an HTTP 500 error with an error message
7. THE Scanner_Backend SHALL expose a GET endpoint at `/api/v1/health` that returns HTTP 200 when the service is running
8. THE Scanner_Backend SHALL serve Swagger_UI at `/docs` for interactive API documentation
9. THE Scanner_Backend SHALL enable CORS to allow requests from the React frontend

### Requirement 8: React Frontend with Cloudscape Design System

**User Story:** As a scanner operator, I want a web interface to provide tickers and view scan results, so that I can analyze bullish stocks visually.

#### Acceptance Criteria

1. THE Scanner_Frontend SHALL display an input field for entering ticker symbols
2. THE Scanner_Frontend SHALL display a "Run Scan" button to initiate a scan
3. WHEN the "Run Scan" button is clicked, THE Scanner_Frontend SHALL validate that at least one ticker symbol has been provided
4. IF no tickers are provided, THEN THE Scanner_Frontend SHALL display a validation message prompting the user to enter ticker symbols
5. WHEN the "Run Scan" button is clicked with valid tickers, THE Scanner_Frontend SHALL send a POST request to the Scanner_Backend `/api/v1/scan` endpoint with the provided ticker list
6. WHILE a scan is in progress, THE Scanner_Frontend SHALL display a loading indicator (Cloudscape `Spinner` component)
7. WHEN scan results are received, THE Scanner_Frontend SHALL display the market regime classification prominently (Cloudscape `StatusIndicator` component)
8. WHEN scan results are received, THE Scanner_Frontend SHALL display a table of ranked tickers with columns for rank, ticker symbol, Bullish_Score, and indicator signals (Cloudscape `Table` component)
9. THE Scanner_Frontend SHALL use Cloudscape Design System (`@cloudscape-design/components`) for all UI elements including `Button`, `Table`, `Input`, `SpaceBetween`, `Container`, `Header`, `AppLayout`, `StatusIndicator`, `Spinner`, `Alert`, and `Badge`
10. THE Scanner_Frontend SHALL sort the results table by rank in descending order by default
11. WHEN a scan fails, THE Scanner_Frontend SHALL display an error message using the Cloudscape `Alert` component with type "error"
12. THE Scanner_Frontend SHALL provide a professional and lightweight visual design using Cloudscape's `AppLayout` for page structure and `ContentLayout` for content areas

### Requirement 9: MVP Scope and Timeline

**User Story:** As a product manager, I want the MVP delivered within a 2-hour timeline with core functionality only, so that we can validate the concept quickly.

#### Acceptance Criteria

1. THE Scanner_Backend SHALL implement only the core indicators: SMA, EMA, MACD, Volume, and Relative Strength
2. THE Scanner_Backend SHALL defer advanced pattern recognition (head and shoulders, cup and handle, etc.) to future versions
3. THE Scanner_Frontend SHALL provide basic result visualization without advanced charting capabilities
4. THE Scanner_Backend SHALL use in-memory caching for active scan sessions and SQLite for persisting completed scan results with a UUID
5. THE Scanner_Backend SHALL expose a GET endpoint at `/api/v1/scan/{scan_id}` to retrieve a previously completed scan result by its UUID
5. THE Scanner_Backend SHALL implement minimal error handling sufficient for MVP demonstration
6. THE Scoring_Engine SHALL use the simplified scoring model defined in Requirement 5 without machine learning or complex weighting

### Requirement 10: Configuration and Deployment

**User Story:** As a developer, I want clear configuration for API credentials and service settings, so that I can deploy the scanner easily.

#### Acceptance Criteria

1. THE Scanner_Backend SHALL read the Massive API token from the environment variable `POLYGON_TOKEN` (already set globally in the system shell — no .env file required)
2. THE Scanner_Backend SHALL read the API base URL from an environment variable (API_BASE_URL) with a default of `https://api.massive.com`
3. THE Scanner_Backend SHALL read the server port from an environment variable with a default of 8000
4. THE Scanner_Frontend SHALL read the backend API URL from an environment variable with a default of http://localhost:8000
5. THE Scanner_Backend SHALL provide a requirements.txt file listing all Python dependencies
6. THE Scanner_Frontend SHALL provide a package.json file listing all Node.js dependencies
7. THE project SHALL include a README with setup and run instructions for both backend and frontend

### Requirement 11: Test-Driven Development and Quality Assurance

**User Story:** As a developer, I want comprehensive unit testing to be completed immediately after implementing each component, so that I can ensure correctness before proceeding to dependent tasks.

#### Acceptance Criteria

1. THE Scanner_Backend SHALL implement unit tests for each component immediately after the component is implemented
2. WHEN a component implementation is complete, THE Developer SHALL write and run unit tests before marking the task as complete
3. THE unit tests SHALL achieve greater than 80% code coverage for the tested component
4. IF unit tests fail, THEN THE component SHALL be fixed until all tests pass before proceeding
5. WHEN multiple related components are implemented and tested, THE Developer SHALL implement integration tests to verify component interactions
6. THE Scanner_Backend SHALL NOT proceed to dependent tasks until all unit tests for prerequisite components pass
7. THE integration tests SHALL be run whenever 2 or more related components are available and tested
8. THE Scanner_Frontend SHALL implement end-to-end (E2E) functional tests using Playwright to verify complete user workflows
9. THE E2E tests SHALL capture screenshots at key interaction points and save them to the workspace for visual verification
10. THE E2E tests SHALL verify the following user workflows:
    - Happy path: Enter tickers → Run scan → View results
    - Error path: Enter no tickers → See validation error
    - Loading state: Verify loading indicator appears during scan
    - Results display: Verify market regime badge and ranked table display correctly
11. THE E2E tests SHALL run against both backend and frontend servers in test mode
12. THE screenshots SHALL be saved to `frontend/test-results/screenshots/` directory for documentation purposes