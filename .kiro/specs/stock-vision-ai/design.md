# Design Document

## Overview

The Bullish Stock Scanner is an MVP system that identifies potentially bullish stocks through technical analysis. The architecture consists of a Python FastAPI backend that orchestrates data fetching, indicator calculation, scoring, and ranking, paired with a React frontend for visualization. The system is designed for rapid development (2-hour timeline) with a focus on core functionality: fetching stock data via REST API, computing five essential technical indicators (SMA, EMA, MACD, Volume, Relative Strength), scoring tickers based on bullish signals, and presenting ranked results through both API and web interface.

## Architecture

### System Architecture

The system follows a three-tier architecture:

1. **Presentation Layer**: React frontend with Cloudscape Design System (`@cloudscape-design/components`)
2. **Application Layer**: FastAPI backend with RESTful endpoints
3. **Data Layer**: External REST API for market data + in-memory cache

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Scan Button │  │Loading State │  │ Results Table│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                   HTTP POST /api/v1/scan
                            │
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Scan Orchestrator                       │  │
│  └──────────────────────────────────────────────────────┘  │
│         │              │              │              │      │
│    ┌────▼───┐    ┌────▼────┐    ┌────▼────┐    ┌────▼──┐ │
│    │Universe│    │Market   │    │Indicator│    │Scoring│ │
│    │Builder │    │Regime   │    │Calc     │    │Engine │ │
│    └────┬───┘    │Analyzer │    └────┬────┘    └───┬───┘ │
│         │        └────┬────┘         │             │      │
│         │             │              │             │      │
│    ┌────▼─────────────▼──────────────▼─────────────▼───┐ │
│    │           REST API Client + Cache                 │ │
│    └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                   HTTP Requests (5 concurrent)
                            │
┌─────────────────────────────────────────────────────────────┐
│              External Market Data REST API                  │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

**Backend Components:**

1. **REST API Client**: Manages communication with external market data API
   - Connection pooling for concurrent requests (max 5)
   - Retry logic with exponential backoff
   - In-memory caching per scan session
   - Error handling and logging

2. **Universe Builder**: Constructs the list of tickers to analyze
   - Input validation (alphanumeric, non-empty)
   - Ticker filtering

3. **Market Regime Analyzer**: Determines market conditions
   - Fetches broad market index data (SPY)
   - Computes 50-day and 200-day SMA
   - Classifies regime (bullish/bearish/neutral)

4. **Indicator Calculator**: Computes technical indicators per ticker
   - 50-day Simple Moving Average (SMA)
   - 20-day Exponential Moving Average (EMA)
   - MACD (12, 26, 9) with signal line and histogram
   - 20-day average volume
   - Relative Strength vs market index

5. **Scoring Engine**: Assigns bullish scores based on indicator signals
   - Rule-based scoring system (0-100 points)
   - Handles missing indicators gracefully
   - Returns score breakdown

6. **Ranking Service**: Sorts and ranks tickers
   - Stable sort by bullish score (descending)
   - Preserves all tickers in output

7. **Scan Orchestrator**: Coordinates the complete scan pipeline
   - Endpoint handler for `/api/v1/scan`
   - Sequential execution of components
   - Response formatting

**Frontend Components:**

1. **Scan Control**: Button and loading state management
2. **Results Display**: Table component for ranked tickers
3. **Market Regime Display**: Prominent regime classification
4. **Error Handler**: Error message display

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **Web Framework**: FastAPI 0.104+
- **HTTP Client**: httpx (async support)
- **Data Processing**: pandas 2.0+, numpy 1.24+
- **Technical Indicators**: pandas-ta or custom implementations
- **CORS**: fastapi.middleware.cors
- **Environment**: python-dotenv

### Frontend
- **Language**: JavaScript/TypeScript
- **Framework**: React 18+
- **UI Library**: Cloudscape Design System (`@cloudscape-design/components`)
- **HTTP Client**: fetch API or axios
- **Build Tool**: Vite or Create React App

### Development Tools
- **Package Management**: pip, requirements.txt
- **Testing**: pytest, hypothesis (property-based testing)
- **Linting**: ruff
- **Type Checking**: mypy

## Data Models

### API Request Models

```python
from pydantic import BaseModel, Field
from typing import List

class ScanRequest(BaseModel):
    """Request model for initiating a scan."""
    tickers: List[str] = Field(..., min_items=1, description="List of ticker symbols to analyze")
    # Future: add parameters for indicator configurations
```

### API Response Models

```python
from pydantic import BaseModel
from typing import List, Dict
from enum import Enum
from datetime import datetime

class MarketRegime(str, Enum):
    """Market regime classification."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class IndicatorSignals(BaseModel):
    """Individual indicator signals contributing to score."""
    price_above_sma50: bool
    price_above_ema20: bool
    macd_above_signal: bool
    macd_histogram_positive: bool
    volume_above_average: bool
    relative_strength_positive: bool

class TickerScore(BaseModel):
    """Scored ticker with details."""
    ticker: str
    bullish_score: int  # 0-100
    signals: IndicatorSignals
    current_price: float
    indicators: Dict[str, float]  # Raw indicator values

class ScanMetadata(BaseModel):
    """Metadata about the scan execution."""
    timestamp: datetime
    ticker_count: int
    duration_seconds: float

class ScanResponse(BaseModel):
    """Complete scan results."""
    scan_id: str  # UUID for retrieval via GET /api/v1/scan/{scan_id}
    market_regime: MarketRegime
    ranked_tickers: List[TickerScore]
    metadata: ScanMetadata
```

### Internal Data Models

```python
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class StockData:
    """Raw stock data from API."""
    ticker: str
    prices: np.ndarray  # Close prices
    volumes: np.ndarray
    timestamps: np.ndarray

@dataclass
class TechnicalIndicators:
    """Calculated technical indicators."""
    sma_50: Optional[float] = None
    ema_20: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    avg_volume_20: Optional[float] = None
    relative_strength: Optional[float] = None
```

## Component Specifications

### 1. REST API Client

**Responsibilities:**
- Authenticate with external API
- Fetch stock price and volume data
- Manage connection pooling (max 5 concurrent)
- Implement retry logic with exponential backoff
- Cache data in-memory per scan session

**Interface:**

```python
class RestApiClient:
    """Client for external market data API."""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        """Initialize with credentials and configure connection pool."""
        pass
    
    async def fetch_stock_data(self, ticker: str, days: int = 250) -> StockData:
        """
        Fetch historical price and volume data for a ticker.
        
        Args:
            ticker: Stock symbol
            days: Number of historical days to fetch
            
        Returns:
            StockData with prices, volumes, timestamps
            
        Raises:
            ApiError: After 3 failed retry attempts
        """
        pass
    
    def clear_cache(self):
        """Clear in-memory cache. Called at start of new scan session."""
        pass
```

**Implementation Details:**
- Use `httpx.AsyncClient` with connection limits
- Implement exponential backoff: 1s, 2s, 4s delays between retries
- Cache keyed by (ticker, days) tuple
- Log all API errors with ticker context

### 2. Universe Builder

**Responsibilities:**
- Accept and validate ticker list input
- Filter invalid tickers

**Interface:**

```python
class UniverseBuilder:
    """Constructs the universe of tickers to analyze."""
    
    def build_universe(self, tickers: List[str]) -> List[str]:
        """
        Build and validate universe of tickers.
        
        Args:
            tickers: List of ticker symbols (required)
            
        Returns:
            List of valid ticker symbols
            
        Raises:
            ValueError: If tickers list is empty or all tickers are invalid
        """
        pass
    
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """Validate ticker is non-empty and alphanumeric."""
        pass
```

**Implementation Details:**
- Ticker validation: `^[A-Z0-9]+$` regex pattern
- Log warnings for invalid tickers
- Raise ValueError if no valid tickers remain after filtering

### 3. Market Regime Analyzer

**Responsibilities:**
- Fetch broad market index data (SPY)
- Calculate 50-day and 200-day SMA
- Classify market regime

**Interface:**

```python
class MarketRegimeAnalyzer:
    """Analyzes current market conditions."""
    
    def __init__(self, api_client: RestApiClient):
        """Initialize with API client."""
        pass
    
    async def analyze_regime(self) -> MarketRegime:
        """
        Determine current market regime.
        
        Returns:
            MarketRegime enum (BULLISH, BEARISH, or NEUTRAL)
        """
        pass
```

**Implementation Details:**
- Use SPY as market proxy
- Calculate SMA_50 and SMA_200 from closing prices
- Classification logic:
  - Bullish: SMA_50 > SMA_200
  - Bearish: SMA_50 < SMA_200 * 0.98
  - Neutral: SMA_50 within 2% of SMA_200 (0.98 to 1.0 ratio)

### 4. Indicator Calculator

**Responsibilities:**
- Compute all technical indicators for a ticker
- Handle insufficient data gracefully
- Return structured indicator results

**Interface:**

```python
class IndicatorCalculator:
    """Computes technical indicators from price/volume data."""
    
    @staticmethod
    def calculate_sma(prices: np.ndarray, period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        pass
    
    @staticmethod
    def calculate_ema(prices: np.ndarray, period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        pass
    
    @staticmethod
    def calculate_macd(prices: np.ndarray) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD indicator.
        
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        pass
    
    @staticmethod
    def calculate_avg_volume(volumes: np.ndarray, period: int) -> Optional[float]:
        """Calculate average volume."""
        pass
    
    @staticmethod
    def calculate_relative_strength(
        ticker_prices: np.ndarray, 
        market_prices: np.ndarray, 
        period: int
    ) -> Optional[float]:
        """
        Calculate relative strength vs market.
        
        Returns:
            Percentage outperformance vs market over period
        """
        pass
    
    def calculate_all(
        self, 
        stock_data: StockData, 
        market_data: StockData
    ) -> TechnicalIndicators:
        """
        Calculate all indicators for a ticker.
        
        Args:
            stock_data: Historical data for the ticker
            market_data: Historical data for market index (SPY)
            
        Returns:
            TechnicalIndicators with all computed values (None for unavailable)
        """
        pass
```

**Implementation Details:**

- **SMA Calculation**: `sum(prices[-period:]) / period`
- **EMA Calculation**: 
  - Multiplier = 2 / (period + 1)
  - EMA = (price * multiplier) + (previous_EMA * (1 - multiplier))
- **MACD Calculation**:
  - MACD Line = EMA(12) - EMA(26)
  - Signal Line = EMA(9) of MACD Line
  - Histogram = MACD Line - Signal Line
- **Avg Volume**: Simple average of last N volumes
- **Relative Strength**: 
  - Ticker return = (current_price - price_N_days_ago) / price_N_days_ago
  - Market return = same calculation for market index
  - RS = ticker_return - market_return (percentage point difference)
- Handle insufficient data by returning None for that indicator
- Log warnings when indicators cannot be calculated

### 5. Scoring Engine

**Responsibilities:**
- Assign points based on bullish signals
- Handle missing indicators
- Return score breakdown

**Interface:**

```python
class ScoringEngine:
    """Assigns bullish scores based on technical indicators."""
    
    def calculate_score(
        self,
        current_price: float,
        current_volume: float,
        indicators: TechnicalIndicators
    ) -> tuple[int, IndicatorSignals]:
        """
        Calculate bullish score and signal breakdown.
        
        Args:
            current_price: Latest price
            current_volume: Latest volume
            indicators: Calculated technical indicators
            
        Returns:
            Tuple of (bullish_score, signals)
        """
        pass
```

**Scoring Rules:**

| Signal | Condition | Points |
|--------|-----------|--------|
| Price above SMA(50) | current_price > sma_50 | 20 |
| Price above EMA(20) | current_price > ema_20 | 15 |
| MACD bullish | macd_line > macd_signal | 20 |
| MACD histogram positive | macd_histogram > 0 | 10 |
| Volume surge | current_volume > avg_volume_20 * 1.2 | 15 |
| Relative strength positive | relative_strength > 0 | 20 |
| **Maximum Total** | | **100** |

**Implementation Details:**
- Check each condition; if indicator is None, skip that signal (0 points)
- Sum all earned points
- Cap total at 100 (though max possible is 100)
- Return both total score and boolean signals for each condition

### 6. Ranking Service

**Responsibilities:**
- Sort tickers by bullish score
- Maintain stable sort for ties
- Format results

**Interface:**

```python
class RankingService:
    """Ranks tickers by bullish score."""
    
    def rank_tickers(self, scored_tickers: List[TickerScore]) -> List[TickerScore]:
        """
        Sort tickers by score in descending order.
        
        Args:
            scored_tickers: List of tickers with scores
            
        Returns:
            Sorted list (descending by score, stable for ties)
        """
        pass
```

**Implementation Details:**
- Use Python's stable sort: `sorted(tickers, key=lambda t: t.bullish_score, reverse=True)`
- Preserves original order for equal scores
- Returns complete list (no filtering)

### 7. Scan Orchestrator

**Responsibilities:**
- Handle `/api/v1/scan` endpoint
- Coordinate all components
- Format responses
- Handle errors

**Interface:**

```python
class ScanOrchestrator:
    """Orchestrates the complete scan pipeline."""
    
    def __init__(
        self,
        api_client: RestApiClient,
        universe_builder: UniverseBuilder,
        regime_analyzer: MarketRegimeAnalyzer,
        indicator_calc: IndicatorCalculator,
        scoring_engine: ScoringEngine,
        ranking_service: RankingService
    ):
        """Initialize with all component dependencies."""
        pass
    
    async def execute_scan(self, request: ScanRequest) -> ScanResponse:
        """
        Execute complete scan pipeline.
        
        Args:
            request: Scan request with optional ticker list
            
        Returns:
            Complete scan results
            
        Raises:
            ScanError: If scan fails
        """
        pass
```

**Pipeline Flow:**

1. Clear API client cache
2. Build universe from required ticker list (validate and filter)
3. Analyze market regime (parallel with ticker processing)
4. For each ticker in universe:
   - Fetch stock data (with caching)
   - Calculate indicators
   - Calculate score
   - Handle errors (mark unavailable, continue)
5. Rank all scored tickers
6. Build response with metadata
7. Return results

**Error Handling:**
- Catch API errors per ticker, log, continue with remaining tickers
- If market regime analysis fails, default to NEUTRAL
- Return HTTP 400 if no tickers provided or all tickers invalid after validation
- Return HTTP 500 if critical failure (e.g., all tickers fail to fetch data)

## API Endpoints

### POST /api/v1/scan

**Purpose**: Initiate a stock scan

**Request:**
```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL"]  // Required - at least 1 ticker
}
```

**Response (200 OK):**
```json
{
  "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "market_regime": "bullish",
  "ranked_tickers": [
    {
      "ticker": "AAPL",
      "bullish_score": 85,
      "signals": {
        "price_above_sma50": true,
        "price_above_ema20": true,
        "macd_above_signal": true,
        "macd_histogram_positive": true,
        "volume_above_average": false,
        "relative_strength_positive": true
      },
      "current_price": 178.50,
      "indicators": {
        "sma_50": 175.20,
        "ema_20": 177.80,
        "macd_line": 1.25,
        "macd_signal": 0.95,
        "macd_histogram": 0.30,
        "avg_volume_20": 52000000.0,
        "relative_strength": 2.5
      }
    }
  ],
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "ticker_count": 3,
    "duration_seconds": 2.5
  }
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Tickers list is required and must contain at least one valid ticker symbol"
}
```

**Response (500 Internal Server Error):**
```json
{
  "detail": "Scan failed: Unable to connect to market data API"
}
```

### GET /api/v1/scan/{scan_id}

**Purpose**: Retrieve a previously completed scan result by UUID

**Response (200 OK):**
```json
{
  "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "market_regime": "bullish",
  "ranked_tickers": [...],
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "ticker_count": 3,
    "duration_seconds": 2.5
  }
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Scan result not found"
}
```

### GET /api/v1/health

**Purpose**: Health check endpoint

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

### GET /docs

**Purpose**: Swagger UI for interactive API documentation

**Response**: HTML page with Swagger UI

## Persistence Layer

### SQLite Storage

Completed scan results are persisted to a SQLite database for retrieval via `GET /api/v1/scan/{scan_id}`.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS scan_results (
    scan_id TEXT PRIMARY KEY,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

**Design Decisions:**
- Single table with the full `ScanResponse` serialized as JSON — simple, no ORM, minimal schema
- UUID generated server-side via `uuid4()` at scan completion
- `scan_id` is returned in the POST response and used for GET retrieval
- SQLite file stored at `backend/scanner.db` (gitignored)
- No migration framework needed — table auto-created on startup
- `aiosqlite` used for async-compatible SQLite access

**Interface:**

```python
class ScanStore:
    """Persists and retrieves completed scan results."""

    def __init__(self, db_path: str = "scanner.db"):
        """Initialize with SQLite database path."""
        pass

    async def initialize(self):
        """Create table if not exists. Called on app startup."""
        pass

    async def save(self, scan_id: str, result: ScanResponse) -> None:
        """Persist a completed scan result."""
        pass

    async def get(self, scan_id: str) -> Optional[ScanResponse]:
        """Retrieve a scan result by ID. Returns None if not found."""
        pass
```

## Frontend Design

### Component Structure

```
src/
├── App.tsx                 # Main application component
├── components/
│   ├── ScanButton.tsx      # Button to trigger scan
│   ├── LoadingIndicator.tsx
│   ├── MarketRegimeBadge.tsx
│   ├── ResultsTable.tsx    # Table of ranked tickers
│   └── ErrorMessage.tsx
├── services/
│   └── scanApi.ts          # API client
├── types/
│   └── scan.ts             # TypeScript types
└── styles/
    └── App.css
```

### Key Components

**App.tsx**: Main container

```typescript
import AppLayout from "@cloudscape-design/components/app-layout";
import ContentLayout from "@cloudscape-design/components/content-layout";
import Header from "@cloudscape-design/components/header";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Input from "@cloudscape-design/components/input";
import Button from "@cloudscape-design/components/button";
import Alert from "@cloudscape-design/components/alert";
import Spinner from "@cloudscape-design/components/spinner";
import "@cloudscape-design/global-styles/index.css";

function App() {
  const [tickers, setTickers] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    if (!tickers.trim()) {
      setError("Please enter at least one ticker symbol");
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const tickerList = tickers.split(/[,\s]+/).filter(t => t.trim());
      const data = await executeScan(tickerList);
      setResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout
      content={
        <ContentLayout header={<Header variant="h1">Bullish Stock Scanner</Header>}>
          <SpaceBetween size="l">
            <Input
              value={tickers}
              onChange={({ detail }) => setTickers(detail.value)}
              placeholder="Enter ticker symbols (e.g., AAPL, MSFT, GOOGL)"
            />
            <Button variant="primary" onClick={handleScan} loading={loading}>
              Run Scan
            </Button>
            {error && <Alert type="error">{error}</Alert>}
            {loading && <Spinner size="large" />}
            {results && (
              <SpaceBetween size="m">
                <MarketRegimeBadge regime={results.market_regime} />
                <ResultsTable tickers={results.ranked_tickers} />
              </SpaceBetween>
            )}
          </SpaceBetween>
        </ContentLayout>
      }
      navigationHide
      toolsHide
    />
  );
}
```

**ResultsTable.tsx**: Display ranked tickers

```typescript
import Table from "@cloudscape-design/components/table";
import Badge from "@cloudscape-design/components/badge";
import Header from "@cloudscape-design/components/header";

interface ResultsTableProps {
  tickers: TickerScore[];
}

function ResultsTable({ tickers }: ResultsTableProps) {
  return (
    <Table
      header={<Header counter={`(${tickers.length})`}>Ranked Results</Header>}
      columnDefinitions={[
        { id: "rank", header: "Rank", cell: (_, index) => index + 1 },
        { id: "ticker", header: "Ticker", cell: (item) => item.ticker },
        { id: "score", header: "Score", cell: (item) => <Badge color={item.bullish_score >= 70 ? "green" : item.bullish_score >= 40 ? "blue" : "grey"}>{item.bullish_score}</Badge> },
        { id: "price", header: "Price", cell: (item) => `$${item.current_price.toFixed(2)}` },
        { id: "signals", header: "Signals", cell: (item) => <SignalBadges signals={item.signals} /> },
      ]}
      items={tickers}
      sortingColumn={{ sortingField: "score" }}
      sortingDescending
      variant="container"
    />
  );
}
```

**scanApi.ts**: API client service

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function executeScan(tickers: string[]): Promise<ScanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/scan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tickers }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Scan failed');
  }
  
  return response.json();
}
```

## Configuration

### Backend Environment Variables

```bash
# Required — already set globally in shell (no .env file needed)
# POLYGON_TOKEN=<your token is set in ~/.zshrc or ~/.zshenv>

# Optional (with defaults)
API_BASE_URL=https://api.massive.com/v2
SERVER_PORT=8000
LOG_LEVEL=INFO
```

### Frontend Environment Variables

```bash
# Optional (with default)
VITE_API_URL=http://localhost:8000
```

## Error Handling

### Backend Error Scenarios

1. **API Authentication Failure**
   - Log error with details
   - Return HTTP 500 with message
   
2. **Individual Ticker Fetch Failure**
   - Log warning with ticker symbol
   - Continue processing remaining tickers
   - Exclude failed ticker from results

3. **Market Regime Analysis Failure**
   - Log warning
   - Default to NEUTRAL regime
   - Continue with scan

4. **All Tickers Fail**
   - Log critical error
   - Return HTTP 500 with message

4. **Invalid Request**
   - Validate request body
   - Return HTTP 400 if tickers list is missing or empty
   - Return HTTP 422 for other validation errors

### Frontend Error Scenarios

1. **Network Error**
   - Display: "Unable to connect to server. Please try again."

2. **No Tickers Provided**
   - Display: "Please enter at least one ticker symbol"
   
3. **Server Error (400)**
   - Display: "Invalid ticker list. Please check your ticker symbols."
   
4. **Server Error (500)**
   - Display error message from server response
   
5. **Timeout**
   - Display: "Scan is taking longer than expected. Please try again."

## Testing Strategy

### Test-Driven Development Approach

This project follows a **strict test-driven development (TDD) workflow**. Testing is not optional or deferred—it is an integral part of completing each task.

**Core TDD Principles:**

1. **Immediate Testing**: Each component implementation MUST be followed immediately by unit tests
2. **Coverage Gate**: Tests MUST pass with >80% coverage before proceeding to the next task
3. **Integration Checkpoints**: Integration tests run when 2+ related components are complete
4. **No Skipping**: No dependent tasks start until prerequisite components are fully tested and passing

**Workflow Per Component:**
```
1. Implement component
2. Write unit tests (target >80% coverage)
3. Run tests and verify they pass
4. Write property-based tests (where applicable)
5. Run all tests and verify coverage
6. Mark task as complete ONLY when tests pass
```

### Backend Testing

#### Unit Tests (pytest) - Run Immediately After Each Component

Unit tests MUST be written and passing before a task is considered complete. Each component has specific testing requirements:

**REST API Client** (`test_api_client.py`):
- Connection pool configuration and limits
- Retry logic with exponential backoff timing
- Cache hits and misses per session
- Error handling for API failures
- Timeout behavior

**Universe Builder** (`test_universe_builder.py`):
- Ticker validation with valid/invalid inputs
- Empty list handling
- Alphanumeric pattern matching
- ValueError raising for all-invalid inputs

**Market Regime Analyzer** (`test_regime_analyzer.py`):
- SMA calculation for SPY
- Regime classification (bullish/bearish/neutral)
- Boundary conditions (2% threshold)
- Default to NEUTRAL on failure

**Indicator Calculator** (`test_indicator_calculator.py`):
- SMA calculation with known inputs
- EMA calculation with known inputs
- MACD line, signal, histogram computation
- Average volume calculation
- Relative strength computation
- Handling of insufficient data (None returns)

**Scoring Engine** (`test_scoring_engine.py`):
- Each scoring rule individually (6 rules)
- Score aggregation and capping at 100
- Handling of missing indicators (None values)
- Signal breakdown accuracy

**Ranking Service** (`test_ranking_service.py`):
- Descending sort by score
- Stable sort for ties
- Complete list preservation (no filtering)

**Scan Orchestrator** (`test_orchestrator.py`):
- Pipeline execution flow
- Error handling per ticker
- Response formatting
- Metadata accuracy

**Scan Store** (`test_scan_store.py`):
- Save operation with UUID
- Retrieve by scan_id
- Not found handling (None return)
- JSON serialization roundtrip

#### Property-Based Tests (hypothesis)

Property tests validate mathematical correctness across random inputs. Each property test MUST:
- Run minimum 100 iterations
- Reference the design document property number
- Use tag format: `Feature: bullish-stock-scanner, Property {N}: {text}`

**Indicator Properties** (`test_indicators_properties.py`):
- Property 6: SMA calculation correctness
- Property 7: EMA calculation correctness
- Property 8: MACD calculation correctness
- Property 9: Average volume correctness
- Property 10: Relative strength correctness

**Scoring Properties** (`test_scoring_properties.py`):
- Property 11: Price above SMA scoring (20 points)
- Property 12: Price above EMA scoring (15 points)
- Property 13: MACD above signal scoring (20 points)
- Property 14: MACD histogram positive scoring (10 points)
- Property 15: Volume surge scoring (15 points)
- Property 16: Relative strength positive scoring (20 points)
- Property 17: Score aggregation and capping

**Ranking Properties** (`test_ranking_properties.py`):
- Property 18: Descending score sort with complete preservation

**API Client Properties** (`test_api_client_properties.py`):
- Property 1: Concurrent request limit enforcement
- Property 2: Retry logic with exponential backoff
- Property 3: Session-based caching

**Universe Builder Properties** (`test_universe_builder_properties.py`):
- Property 4: Ticker validation and filtering

**Market Regime Properties** (`test_regime_analyzer_properties.py`):
- Property 5: Market regime classification

#### Integration Testing Checkpoints

Integration tests run at specific checkpoints when related components are complete:

**Checkpoint 1: After API Client + Universe Builder**
- Test: Universe creation with real API client (mocked responses)
- Verify: Ticker validation integrates with data fetching

**Checkpoint 2: After All Indicator Components**
- Test: Market Regime Analyzer + Indicator Calculator integration
- Verify: Full indicator suite calculation with market context

**Checkpoint 3: After Scoring + Ranking**
- Test: Complete scoring pipeline from indicators to ranked results
- Verify: Score calculation and ranking work end-to-end

**Checkpoint 4: After Full API Endpoints**
- Test: Complete scan endpoint (`test_scan_endpoint.py`)
- Verify: Full pipeline from HTTP request to HTTP response
- Test: Scan retrieval endpoint with persistence
- Verify: Save and retrieve flow with SQLite

### Frontend Testing

#### Component Tests (React Testing Library)

**ScanButton.tsx**:
- Button click triggers scan
- Loading state displays during scan
- Button disabled while loading

**LoadingIndicator.tsx**:
- Shows during loading state
- Hides when not loading

**MarketRegimeBadge.tsx**:
- Displays correct regime text
- Uses correct color for each regime (bullish/bearish/neutral)

**ResultsTable.tsx**:
- Renders all ticker rows
- Displays correct rank numbers
- Shows score badges with correct colors
- Formats price correctly

**SignalBadges.tsx**:
- Renders all signal indicators
- Shows correct state (active/inactive)

**ErrorMessage.tsx**:
- Displays error text
- Shows correct alert type

#### Integration Tests

**API Integration**:
- Scan button click triggers API call
- Loading state during request
- Results display on success
- Error message on failure
- Proper request body formatting

**User Flow**:
- Enter tickers → click scan → see loading → see results
- Enter tickers → click scan → see loading → see error

#### End-to-End (E2E) Functional Testing with Playwright

**Overview:**
End-to-end tests verify complete user workflows by automating browser interactions with the full application stack (backend + frontend). These tests ensure the entire system works together correctly from a user's perspective.

**Tool:** Playwright (supports multiple browsers: Chromium, Firefox, WebKit)

**Setup:**
```bash
# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install

# Configure Playwright in playwright.config.ts
```

**Configuration (playwright.config.ts):**
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html'],
    ['list']
  ],
  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'on',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'cd ../backend && uvicorn main:app --port 8000',
      port: 8000,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      port: 5173,
      timeout: 120000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

**Test Structure:**
```
frontend/
├── tests/
│   └── e2e/
│       ├── happy-path.spec.ts
│       ├── error-scenarios.spec.ts
│       ├── loading-states.spec.ts
│       └── results-display.spec.ts
├── test-results/
│   └── screenshots/
│       ├── 01-initial-page.png
│       ├── 02-tickers-entered.png
│       ├── 03-loading-state.png
│       ├── 04-results-displayed.png
│       ├── 05-error-no-tickers.png
│       └── ... (more screenshots)
└── playwright.config.ts
```

**Test Scenarios:**

**1. Happy Path Test (`happy-path.spec.ts`)**
```typescript
import { test, expect } from '@playwright/test';

test('complete scan workflow - enter tickers, run scan, view results', async ({ page }) => {
  // Navigate to app
  await page.goto('/');
  await page.screenshot({ path: 'test-results/screenshots/01-initial-page.png' });
  
  // Enter tickers
  const input = page.locator('input[placeholder*="ticker"]');
  await input.fill('AAPL, MSFT, GOOGL');
  await page.screenshot({ path: 'test-results/screenshots/02-tickers-entered.png' });
  
  // Click scan button
  const scanButton = page.locator('button:has-text("Run Scan")');
  await scanButton.click();
  
  // Verify loading state
  await expect(page.locator('.awsui-spinner')).toBeVisible();
  await page.screenshot({ path: 'test-results/screenshots/03-loading-state.png' });
  
  // Wait for results
  await expect(page.locator('table')).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: 'test-results/screenshots/04-results-displayed.png' });
  
  // Verify market regime badge is present
  await expect(page.locator('[class*="badge"]')).toBeVisible();
  
  // Verify table has rows
  const rows = page.locator('table tbody tr');
  await expect(rows).toHaveCount(3);
  
  // Verify rank column shows 1, 2, 3
  const firstRank = page.locator('table tbody tr').first().locator('td').first();
  await expect(firstRank).toContainText('1');
});
```

**2. Error Scenarios Test (`error-scenarios.spec.ts`)**
```typescript
import { test, expect } from '@playwright/test';

test('error when no tickers entered', async ({ page }) => {
  await page.goto('/');
  
  // Click scan without entering tickers
  const scanButton = page.locator('button:has-text("Run Scan")');
  await scanButton.click();
  
  // Verify error message appears
  await expect(page.locator('[class*="alert"]')).toBeVisible();
  await expect(page.locator('[class*="alert"]')).toContainText('Please enter at least one ticker');
  
  await page.screenshot({ path: 'test-results/screenshots/05-error-no-tickers.png' });
});

test('error when invalid tickers entered', async ({ page }) => {
  await page.goto('/');
  
  const input = page.locator('input[placeholder*="ticker"]');
  await input.fill('!!!INVALID@@@');
  
  const scanButton = page.locator('button:has-text("Run Scan")');
  await scanButton.click();
  
  // Verify error handling (either validation or API error)
  await expect(page.locator('[class*="alert"]')).toBeVisible({ timeout: 30000 });
  
  await page.screenshot({ path: 'test-results/screenshots/06-error-invalid-tickers.png' });
});
```

**3. Loading States Test (`loading-states.spec.ts`)**
```typescript
import { test, expect } from '@playwright/test';

test('loading indicator appears during scan', async ({ page }) => {
  await page.goto('/');
  
  const input = page.locator('input[placeholder*="ticker"]');
  await input.fill('AAPL, MSFT');
  
  const scanButton = page.locator('button:has-text("Run Scan")');
  await scanButton.click();
  
  // Verify spinner appears immediately
  await expect(page.locator('.awsui-spinner')).toBeVisible({ timeout: 1000 });
  await page.screenshot({ path: 'test-results/screenshots/07-loading-spinner.png' });
  
  // Verify button is disabled during loading
  await expect(scanButton).toBeDisabled();
  
  // Wait for loading to complete
  await expect(page.locator('.awsui-spinner')).not.toBeVisible({ timeout: 30000 });
  
  // Verify button is enabled again
  await expect(scanButton).toBeEnabled();
});
```

**4. Results Display Test (`results-display.spec.ts`)**
```typescript
import { test, expect } from '@playwright/test';

test('market regime badge displays correctly', async ({ page }) => {
  await page.goto('/');
  
  const input = page.locator('input[placeholder*="ticker"]');
  await input.fill('AAPL, MSFT');
  
  const scanButton = page.locator('button:has-text("Run Scan")');
  await scanButton.click();
  
  // Wait for results
  await expect(page.locator('table')).toBeVisible({ timeout: 30000 });
  
  // Verify market regime badge
  const regimeBadge = page.locator('[class*="status-indicator"]');
  await expect(regimeBadge).toBeVisible();
  await expect(regimeBadge).toContainText(/(bullish|bearish|neutral)/i);
  
  await page.screenshot({ path: 'test-results/screenshots/08-market-regime-badge.png' });
});

test('results table displays ranked tickers', async ({ page }) => {
  await page.goto('/');
  
  const input = page.locator('input[placeholder*="ticker"]');
  await input.fill('AAPL, MSFT, GOOGL');
  
  const scanButton = page.locator('button:has-text("Run Scan")');
  await scanButton.click();
  
  await expect(page.locator('table')).toBeVisible({ timeout: 30000 });
  
  // Verify table header
  await expect(page.locator('th:has-text("Rank")')).toBeVisible();
  await expect(page.locator('th:has-text("Ticker")')).toBeVisible();
  await expect(page.locator('th:has-text("Score")')).toBeVisible();
  
  // Verify rows exist
  const rows = page.locator('table tbody tr');
  await expect(rows).toHaveCount(3);
  
  // Verify scores are present
  const scoreBadges = page.locator('[class*="badge"]');
  await expect(scoreBadges.first()).toBeVisible();
  
  await page.screenshot({ path: 'test-results/screenshots/09-results-table.png' });
});
```

**Running E2E Tests:**
```bash
# Run all E2E tests
npx playwright test

# Run specific test file
npx playwright test tests/e2e/happy-path.spec.ts

# Run with UI mode (interactive)
npx playwright test --ui

# Run in headed mode (see browser)
npx playwright test --headed

# View test report
npx playwright show-report
```

**Screenshot Management:**
- All screenshots saved to `frontend/test-results/screenshots/`
- Naming convention: `##-descriptive-name.png`
- Screenshots captured at key interaction points for visual verification
- Committed to workspace for documentation and regression testing

**Best Practices:**
1. **Start servers automatically**: Playwright config starts both backend and frontend
2. **Wait for elements**: Use `expect(...).toBeVisible()` with timeouts
3. **Capture on failure**: Playwright automatically captures screenshots on test failure
4. **Use descriptive selectors**: Prefer text content and ARIA labels over CSS classes
5. **Isolate tests**: Each test should be independent and not rely on previous test state


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Concurrent Request Limit Enforcement

*For any* batch of API requests, the REST_API_Client SHALL never execute more than 5 requests concurrently, regardless of the total number of requests in the batch.

**Validates: Requirements 1.2**

### Property 2: Retry Logic with Exponential Backoff

*For any* sequence of API failures, the REST_API_Client SHALL retry exactly 3 times with exponential backoff delays (1s, 2s, 4s), and the timing between retries SHALL follow the exponential pattern within acceptable tolerance.

**Validates: Requirements 1.4**

### Property 3: Session-Based Caching

*For any* scan session and any ticker, if the same ticker is requested multiple times within the session, the REST_API_Client SHALL return cached data on subsequent requests without making additional API calls.

**Validates: Requirements 1.6**

### Property 4: Ticker Validation and Filtering

*For any* input list of ticker strings, the Universe_Builder SHALL return only those tickers that are non-empty and contain exclusively alphanumeric characters, and SHALL raise a ValueError if the input list is empty or all tickers are invalid after filtering.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 5: Market Regime Classification

*For any* market index price history, the Market_Regime_Analyzer SHALL classify the regime as bullish when SMA_50 > SMA_200, bearish when SMA_50 < SMA_200 * 0.98, and neutral when SMA_50 is within 2% of SMA_200.

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 6: SMA Calculation Correctness

*For any* price sequence with sufficient data, the calculated 50-day Simple Moving Average SHALL equal the arithmetic mean of the last 50 prices.

**Validates: Requirements 4.1**


### Property 7: EMA Calculation Correctness

*For any* price sequence with sufficient data, the calculated 20-day Exponential Moving Average SHALL correctly apply the EMA formula with multiplier 2/(period+1) at each step.

**Validates: Requirements 4.2**

### Property 8: MACD Calculation Correctness

*For any* price sequence with sufficient data, the MACD indicator SHALL correctly compute the MACD line as EMA(12) - EMA(26), the signal line as EMA(9) of the MACD line, and the histogram as MACD line minus signal line.

**Validates: Requirements 4.3**

### Property 9: Average Volume Calculation Correctness

*For any* volume sequence with sufficient data, the calculated 20-day average volume SHALL equal the arithmetic mean of the last 20 volume values.

**Validates: Requirements 4.4**

### Property 10: Relative Strength Calculation Correctness

*For any* pair of ticker and market price sequences over a 20-day period, the Relative Strength SHALL equal the ticker's percentage return minus the market's percentage return over that period.

**Validates: Requirements 4.5**

### Property 11: Price Above SMA Scoring

*For any* ticker where the current price is greater than the 50-day SMA, the Scoring_Engine SHALL add exactly 20 points to the bullish score.

**Validates: Requirements 5.2**

### Property 12: Price Above EMA Scoring

*For any* ticker where the current price is greater than the 20-day EMA, the Scoring_Engine SHALL add exactly 15 points to the bullish score.

**Validates: Requirements 5.3**

### Property 13: MACD Above Signal Scoring

*For any* ticker where the MACD line is greater than the signal line, the Scoring_Engine SHALL add exactly 20 points to the bullish score.

**Validates: Requirements 5.4**

### Property 14: MACD Histogram Positive Scoring

*For any* ticker where the MACD histogram is positive, the Scoring_Engine SHALL add exactly 10 points to the bullish score.

**Validates: Requirements 5.5**


### Property 15: Volume Surge Scoring

*For any* ticker where the current volume is at least 120% of the 20-day average volume, the Scoring_Engine SHALL add exactly 15 points to the bullish score.

**Validates: Requirements 5.6**

### Property 16: Relative Strength Positive Scoring

*For any* ticker where the Relative Strength is positive, the Scoring_Engine SHALL add exactly 20 points to the bullish score.

**Validates: Requirements 5.7**

### Property 17: Score Aggregation and Capping

*For any* ticker with calculated indicator signals, the total bullish score SHALL equal the sum of all earned points from individual scoring rules, and the score SHALL never exceed 100.

**Validates: Requirements 5.8**

### Property 18: Descending Score Sort with Complete Preservation

*For any* list of scored tickers, the Ranking_Service SHALL return all tickers sorted in descending order by bullish score, using stable sort to preserve original order for equal scores.

**Validates: Requirements 6.1, 6.2, 6.4**

## Deployment Architecture

### Backend Deployment

**Development:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEY=your_key
export API_SECRET=your_secret

# Run server
uvicorn main:app --reload --port 8000
```

**Production Considerations** (Future):
- Use gunicorn with uvicorn workers
- Configure proper logging
- Add rate limiting
- Implement API key authentication
- Add monitoring and metrics
- Use external cache (Redis)

### Frontend Deployment

**Development:**
```bash
# Install dependencies
npm install

# Run dev server
npm run dev
```

**Production:**
```bash
# Build for production
npm run build

# Serve with static file server or CDN
```


## Project Structure

### Backend Structure

```
backend/
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration and environment variables
├── requirements.txt                 # Python dependencies
├── api/
│   ├── __init__.py
│   ├── endpoints.py                 # API route handlers
│   └── models.py                    # Pydantic request/response models
├── core/
│   ├── __init__.py
│   ├── api_client.py                # REST API Client
│   ├── universe_builder.py          # Universe Builder
│   ├── regime_analyzer.py           # Market Regime Analyzer
│   ├── indicator_calculator.py      # Indicator Calculator
│   ├── scoring_engine.py            # Scoring Engine
│   ├── ranking_service.py           # Ranking Service
│   ├── orchestrator.py              # Scan Orchestrator
│   └── scan_store.py               # SQLite persistence for scan results
├── utils/
│   ├── __init__.py
│   └── logging.py                   # Logging configuration
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── test_api_client.py
    │   ├── test_universe_builder.py
    │   ├── test_regime_analyzer.py
    │   ├── test_indicator_calculator.py
    │   ├── test_scoring_engine.py
    │   └── test_ranking_service.py
    ├── property/
    │   ├── test_indicators_properties.py
    │   ├── test_scoring_properties.py
    │   ├── test_ranking_properties.py
    │   └── test_api_client_properties.py
    └── integration/
        └── test_scan_endpoint.py
```

### Frontend Structure

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── ScanButton.tsx
│   │   ├── LoadingIndicator.tsx
│   │   ├── MarketRegimeBadge.tsx
│   │   ├── ResultsTable.tsx
│   │   ├── SignalBadges.tsx
│   │   └── ErrorMessage.tsx
│   ├── services/
│   │   └── scanApi.ts
│   ├── types/
│   │   └── scan.ts
│   └── styles/
│       └── App.css
└── tests/
    └── App.test.tsx
```


## Dependencies

### Backend Dependencies

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.0
pydantic==2.4.2
python-dotenv==1.0.0
pandas==2.1.1
numpy==1.26.0
python-dateutil==2.8.2
aiosqlite==0.19.0

# Development and Testing
pytest==7.4.2
hypothesis==6.88.1
pytest-asyncio==0.21.1
pytest-cov==4.1.0
ruff==0.1.3
mypy==1.6.1
```

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@cloudscape-design/components": "^3.0.0",
    "@cloudscape-design/global-styles": "^1.0.0",
    "@cloudscape-design/collection-hooks": "^1.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^4.4.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0"
  }
}
```

## Performance Considerations

### Backend Performance

1. **Concurrent API Requests**: Limit to 5 concurrent requests to respect API tier
2. **Caching**: In-memory cache reduces redundant API calls within a scan session
3. **Async Processing**: Use async/await for all I/O operations
4. **Batch Processing**: Process tickers concurrently where possible

**Expected Performance**:
- Single ticker analysis: ~500ms (including API call)
- 50 tickers with 5 concurrent: ~5-6 seconds
- 100 tickers with 5 concurrent: ~10-12 seconds

### Frontend Performance

1. **Lazy Loading**: Load results progressively if needed
2. **Debouncing**: Prevent multiple simultaneous scan requests
3. **Optimistic UI**: Show loading state immediately on button click

## Security Considerations

### Backend Security

1. **API Credentials**: Store in environment variables, never commit to git
2. **CORS**: Configure allowed origins (restrict in production)
3. **Input Validation**: Validate all request inputs with Pydantic
4. **Rate Limiting**: Add rate limiting for production (future)
5. **Error Messages**: Don't expose internal details in error responses

### Frontend Security

1. **API URL Configuration**: Use environment variables
2. **XSS Prevention**: React's built-in escaping handles this
3. **HTTPS**: Use HTTPS in production
4. **CSP Headers**: Configure Content Security Policy (future)

## Future Enhancements

### Phase 2 Features

1. **Advanced Indicators**: RSI, Bollinger Bands, Stochastic Oscillator
2. **Chart Pattern Recognition**: Head and shoulders, cup and handle, triangles
3. **Machine Learning Scoring**: Train ML model on historical data
4. **Historical Backtesting**: Test scoring accuracy against historical performance
5. **Persistent Storage**: Database for scan history and user watchlists
6. **User Authentication**: User accounts and saved preferences
7. **Real-time Updates**: WebSocket support for live price updates
8. **Custom Scoring Weights**: Allow users to adjust indicator weights
9. **Multi-timeframe Analysis**: Analyze multiple timeframes (daily, weekly, monthly)
10. **Alerts and Notifications**: Email/SMS alerts for high-scoring tickers

### Technical Improvements

1. **Distributed Caching**: Redis for shared cache across instances
2. **Job Queue**: Celery for async background processing
3. **Database**: PostgreSQL for persistent storage
4. **Monitoring**: Prometheus + Grafana for metrics
5. **Logging**: Centralized logging with ELK stack
6. **CI/CD**: Automated testing and deployment pipeline
7. **Containerization**: Docker for deployment
8. **Load Balancing**: Multiple backend instances with load balancer

## Conclusion

This design provides a complete blueprint for building a functional Bullish Stock Scanner MVP within a 2-hour development timeline. The architecture prioritizes simplicity and core functionality while maintaining extensibility for future enhancements. The modular component design ensures testability and maintainability, with clear separation of concerns between data fetching, analysis, scoring, and presentation layers.