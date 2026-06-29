"""Backtest engine — orchestrates historical scoring + forward return computation.

Runs the scoring pipeline against data truncated to a past date,
then computes actual forward returns to evaluate model accuracy.
Also computes precision/recall metrics for all qualified symbols.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from dataclasses import dataclass

from .config import get_settings
from .data_fetcher import fetch_ohlcv_range
from .forward_returns import ForwardReturns, compute_forward_returns_for_symbol
from .indicators import compute_indicators, Indicators
from .market_calendar import subtract_trading_days
from .precision_recall import PrecisionRecall, compute_precision_recall
from .scorer import rank_stocks
from .universe import COMPANY_NAMES, NIFTY_100

logger = logging.getLogger(__name__)


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
    backtest_date: str  # ISO format YYYY-MM-DD
    picks: list[BacktestPick]
    benchmark_returns: ForwardReturns
    total_qualified: int
    precision_recall: PrecisionRecall


async def run_backtest(target_date: date) -> BacktestResult:
    """Run a historical scan as of target_date and compute forward returns.

    Steps:
    1. Validate target_date is in the past (raise ValueError if today or future)
    2. Compute fetch range: start = target_date - 252 trading days, end = today
    3. Fetch OHLCV for all Nifty 100 symbols concurrently
    4. Truncate each DataFrame to backtest_date for scoring
    5. Compute indicators — skip symbols with None
    6. Rank using rank_stocks → top 10 picks + total_qualified
    7. Compute forward returns for ALL qualified symbols
    8. Compute forward returns for benchmark (^NSEI)
    9. Compute precision/recall
    10. Assemble and return BacktestResult

    Raises:
        ValueError: If target_date is today or in the future.
        RuntimeError: If all symbols fail (total_qualified == 0).
    """
    # Step 1: Validate target_date
    today = date.today()
    if target_date >= today:
        raise ValueError("target_date must be in the past")

    # Step 2: Compute fetch range
    start = subtract_trading_days(target_date, 252)
    end = today

    # Step 3: Fetch OHLCV for all Nifty 100 symbols concurrently
    settings = get_settings()
    sem = asyncio.Semaphore(settings.concurrency_limit)

    tasks = [fetch_ohlcv_range(symbol, start, end, sem) for symbol in NIFTY_100]
    results = await asyncio.gather(*tasks)

    # Map symbol → full DataFrame
    symbol_dfs: dict[str, object] = {}
    for symbol, df in zip(NIFTY_100, results):
        if df is not None and not df.empty:
            symbol_dfs[symbol] = df

    # Step 4: Truncate each DataFrame to backtest_date for scoring
    # Step 5: Compute indicators
    indicators_list: list[Indicators] = []
    # Track which symbols have valid indicators (for forward returns later)
    qualified_symbols: list[str] = []

    for symbol, df in symbol_dfs.items():
        # Truncate: keep only rows on or before target_date
        df_trunc = df[df.index.normalize().date <= target_date]
        if df_trunc.empty:
            continue

        ind = compute_indicators(symbol, df_trunc)
        if ind is not None:
            indicators_list.append(ind)
            qualified_symbols.append(symbol)

    # Step 6: Rank stocks
    if not indicators_list:
        raise RuntimeError("All symbols failed — no qualified stocks for backtest")

    top_picks, total_qualified = rank_stocks(indicators_list, COMPANY_NAMES, top_n=10)

    # Step 7: Compute forward returns for ALL qualified symbols
    # We need forward returns for all qualified symbols for precision/recall
    all_forward_returns: list[ForwardReturns] = []
    # Also track pick forward returns separately (for the top 10)
    pick_symbols = {pick.symbol for pick in top_picks}
    pick_forward_returns_map: dict[str, ForwardReturns] = {}

    for symbol in qualified_symbols:
        df = symbol_dfs[symbol]
        # Get prices after backtest_date for forward computation
        # Include backtest_date's close as the base price
        forward_mask = df.index.normalize().date >= target_date
        forward_df = df[forward_mask]

        if forward_df.empty:
            fr = ForwardReturns(return_5d=None, return_10d=None, return_20d=None)
        else:
            price_series = forward_df["Close"]
            fr = compute_forward_returns_for_symbol(target_date, price_series)

        all_forward_returns.append(fr)

        if symbol in pick_symbols:
            pick_forward_returns_map[symbol] = fr

    # Build pick_forward_returns list in rank order
    pick_forward_returns: list[ForwardReturns] = []
    for pick in top_picks:
        fr = pick_forward_returns_map.get(
            pick.symbol,
            ForwardReturns(return_5d=None, return_10d=None, return_20d=None),
        )
        pick_forward_returns.append(fr)

    # Step 8: Compute forward returns for benchmark (^NSEI)
    benchmark_symbol = settings.regime_symbol_yf
    benchmark_df = await fetch_ohlcv_range(benchmark_symbol, start, end, sem)

    if benchmark_df is not None and not benchmark_df.empty:
        forward_mask = benchmark_df.index.normalize().date >= target_date
        benchmark_forward = benchmark_df[forward_mask]
        if not benchmark_forward.empty:
            benchmark_returns = compute_forward_returns_for_symbol(
                target_date, benchmark_forward["Close"]
            )
        else:
            benchmark_returns = ForwardReturns(
                return_5d=None, return_10d=None, return_20d=None
            )
    else:
        benchmark_returns = ForwardReturns(
            return_5d=None, return_10d=None, return_20d=None
        )

    # Step 9: Compute precision/recall
    precision_recall = compute_precision_recall(pick_forward_returns, all_forward_returns)

    # Step 10: Assemble BacktestResult
    backtest_picks: list[BacktestPick] = []
    for pick, fr in zip(top_picks, pick_forward_returns):
        backtest_picks.append(
            BacktestPick(
                rank=pick.rank,
                symbol=pick.symbol,
                company_name=pick.company_name,
                score=pick.score,
                close=pick.close,
                sma50=pick.sma50,
                sma200=pick.sma200,
                volume_ratio=pick.volume_ratio,
                pct_from_52w_high=pick.pct_from_52w_high,
                forward_returns=fr,
            )
        )

    return BacktestResult(
        backtest_date=target_date.isoformat(),
        picks=backtest_picks,
        benchmark_returns=benchmark_returns,
        total_qualified=total_qualified,
        precision_recall=precision_recall,
    )
