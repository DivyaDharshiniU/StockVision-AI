"""OHLCV data fetching via yfinance with async concurrency control.

Uses a module-level ThreadPoolExecutor to run yf.download in a thread,
and an asyncio.Semaphore (passed by the caller) to cap parallel requests
to Settings.concurrency_limit (default 5).
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from .config import get_settings

logger = logging.getLogger(__name__)

# Module-level thread pool; 10 workers is plenty since we also use a semaphore.
_executor = ThreadPoolExecutor(max_workers=10)


async def fetch_ohlcv(symbol: str, sem: asyncio.Semaphore) -> pd.DataFrame | None:
    """Download ~252 calendar days of daily OHLCV for *symbol*.

    The caller is responsible for creating the semaphore with a limit of
    ``Settings.concurrency_limit`` (default 5).  This function acquires the
    semaphore before issuing the network request and releases it on exit,
    ensuring at most *concurrency_limit* downloads run simultaneously.

    Returns:
        A ``pd.DataFrame`` with OHLCV columns on success, or ``None`` if the
        symbol has no data or the download raises an exception (Req 1.3).
    """
    # Validate settings are accessible (also ensures concurrency_limit is respected
    # by the semaphore the caller built with get_settings().concurrency_limit).
    get_settings()  # side-effect: warm the singleton; caller uses concurrency_limit

    async with sem:
        loop = asyncio.get_running_loop()
        try:
            df: pd.DataFrame = await loop.run_in_executor(
                _executor,
                lambda: yf.Ticker(symbol).history(
                    period="1y",       # ≥252 calendar days — satisfies Req 2.1
                    interval="1d",
                    auto_adjust=True,
                ),
            )
            if df is None or df.empty:
                logger.warning("No data returned for %s", symbol)
                return None
            # Keep only the OHLCV columns we need; drop Dividends / Stock Splits
            ohlcv_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            return df[ohlcv_cols]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch %s: %s", symbol, exc)
            return None


async def fetch_ohlcv_range(
    symbol: str,
    start: date,
    end: date,
    sem: asyncio.Semaphore,
) -> pd.DataFrame | None:
    """Download daily OHLCV for *symbol* from *start* to *end* (inclusive).

    Uses ``yf.Ticker(symbol).history(start=..., end=...)`` instead of
    ``period="1y"``.  The *end* parameter for yfinance is exclusive, so we
    add one calendar day to make the range inclusive on both sides.

    The caller is responsible for creating the semaphore with a limit of
    ``Settings.concurrency_limit``.  This function acquires the semaphore
    before issuing the network request and releases it on exit, ensuring at
    most *concurrency_limit* downloads run simultaneously.

    Returns:
        A ``pd.DataFrame`` with DatetimeIndex and columns
        [Open, High, Low, Close, Volume] on success, or ``None`` if the
        symbol has no data or the download raises an exception.
    """
    get_settings()  # warm the singleton

    async with sem:
        loop = asyncio.get_running_loop()
        try:
            df: pd.DataFrame = await loop.run_in_executor(
                _executor,
                lambda: yf.Ticker(symbol).history(
                    start=str(start),
                    end=str(end + timedelta(days=1)),
                    interval="1d",
                    auto_adjust=True,
                ),
            )
            if df is None or df.empty:
                logger.warning("No data returned for %s (range %s to %s)", symbol, start, end)
                return None
            # Keep only the OHLCV columns we need; drop Dividends / Stock Splits
            ohlcv_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            return df[ohlcv_cols]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch %s (range %s to %s): %s", symbol, start, end, exc)
            return None
