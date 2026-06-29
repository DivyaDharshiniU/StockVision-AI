# Product: StockVision AI

StockVision AI is a full-stack stock scanner that identifies the top 10 bullish picks from India's Nifty 100 universe (Nifty 50 + Nifty Next 50) in real time.

## What It Does

- Fetches 252 calendar days of OHLCV data for 100 large-cap NSE stocks via yfinance
- Computes technical indicators: SMA50, SMA200, 20-session average volume, 52-week high
- Scores each stock on a 0–100 bullish scale using three binary signals (SMA trend, volume surge, 52W high proximity)
- Returns the top 10 ranked picks ordered by score, with ties broken by volume ratio
- Renders results in a sortable table with 30-day sparklines

## Scoring Model

| Signal | Condition | Weight |
|---|---|---|
| SMA Trend | close > SMA50 AND close > SMA200 | 40 pts |
| Volume Surge | volume_last > 1.5 × avg_volume_20 | 35 pts |
| 52W High Proximity | close >= 0.75 × high_52w | 25 pts |

Possible scores: {0, 25, 35, 40, 60, 65, 75, 100}

## Key Design Principles

- Single endpoint architecture: one GET /api/scan serves the entire workflow
- Pure functions for indicators and scoring (no side effects, trivially testable)
- In-flight deduplication prevents redundant scans from concurrent requests
- Async with semaphore rate-limiting (5 concurrent yfinance downloads)
- Property-based testing as primary correctness strategy
