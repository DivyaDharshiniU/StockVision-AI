"""Scan orchestrator for StockVision AI.

Gathers OHLCV data for all NIFTY_100 symbols concurrently, computes
technical indicators, and returns the top-ranked picks.
"""

from __future__ import annotations

import asyncio

from .config import get_settings
from .data_fetcher import fetch_ohlcv
from .indicators import compute_indicators
from .scorer import rank_stocks
from .universe import COMPANY_NAMES, NIFTY_100


async def run_scan() -> dict:
    """Run a full Nifty 100 scan.

    Fetches OHLCV data for all symbols concurrently (bounded by
    ``Settings.concurrency_limit``), filters out symbols with insufficient
    data, scores the remainder, and returns the top picks.

    Returns:
        A dict with keys ``"picks"`` (list of :class:`~backend.scorer.ScoredStock`)
        and ``"total_qualified"`` (int).

    Raises:
        RuntimeError: If every symbol fails data retrieval (no valid indicators
            could be computed).
    """
    settings = get_settings()
    sem = asyncio.Semaphore(settings.concurrency_limit)

    tasks = [fetch_ohlcv(sym, sem) for sym in NIFTY_100]
    results = await asyncio.gather(*tasks)

    indicators = []
    for symbol, df in zip(NIFTY_100, results):
        if df is None:
            continue
        ind = compute_indicators(symbol, df)
        if ind is not None:
            indicators.append(ind)

    if not indicators:
        raise RuntimeError("All symbols failed data retrieval")

    picks, total_qualified = rank_stocks(indicators, COMPANY_NAMES)
    return {"picks": picks, "total_qualified": total_qualified}
