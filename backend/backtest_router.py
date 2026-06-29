"""FastAPI router for the GET /api/backtest endpoint.

Accepts a date query parameter, validates it, runs the backtest engine,
and returns the serialized BacktestResult as JSON including precision/recall metrics.
"""

from __future__ import annotations

import dataclasses
import datetime as dt

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .backtest_engine import run_backtest

router = APIRouter()


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
    # Validate date format
    try:
        parsed_date = dt.datetime.strptime(date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return JSONResponse(
            content={"error": "Invalid date format. Expected YYYY-MM-DD."},
            status_code=422,
        )

    # Validate date is in the past
    today = dt.date.today()
    if parsed_date >= today:
        return JSONResponse(
            content={"error": "date must be in the past"},
            status_code=400,
        )

    # Run the backtest engine
    try:
        result = await run_backtest(parsed_date)
    except ValueError as exc:
        return JSONResponse(
            content={"error": str(exc)},
            status_code=400,
        )
    except (RuntimeError, Exception) as exc:
        return JSONResponse(
            content={"error": str(exc)},
            status_code=503,
        )

    # Serialize BacktestResult to JSON response
    picks_payload = []
    for pick in result.picks:
        pick_dict = {
            "rank": pick.rank,
            "symbol": pick.symbol,
            "company_name": pick.company_name,
            "score": pick.score,
            "close": pick.close,
            "sma50": pick.sma50,
            "sma200": pick.sma200,
            "volume_ratio": pick.volume_ratio,
            "pct_from_52w_high": pick.pct_from_52w_high,
            "forward_return_5d": pick.forward_returns.return_5d,
            "forward_return_10d": pick.forward_returns.return_10d,
            "forward_return_20d": pick.forward_returns.return_20d,
        }
        picks_payload.append(pick_dict)

    benchmark_payload = {
        "return_5d": result.benchmark_returns.return_5d,
        "return_10d": result.benchmark_returns.return_10d,
        "return_20d": result.benchmark_returns.return_20d,
    }

    precision_recall_payload = dataclasses.asdict(result.precision_recall)

    payload = {
        "backtest_date": result.backtest_date,
        "total_qualified": result.total_qualified,
        "picks": picks_payload,
        "benchmark_returns": benchmark_payload,
        "precision_recall": precision_recall_payload,
    }

    return JSONResponse(content=payload, status_code=200)
