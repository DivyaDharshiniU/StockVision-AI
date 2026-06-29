"""Forward return computation for backtest evaluation.

Pure module — no side effects, no I/O.
Computes percentage returns at fixed trading-day windows
(5, 10, 20 days) after a given backtest date.
"""

from __future__ import annotations

from datetime import date, timedelta
from dataclasses import dataclass

import pandas as pd

from .market_calendar import is_trading_day


@dataclass
class ForwardReturns:
    """Forward percentage returns at each window.

    Values are percentages rounded to 2 decimal places, or None
    if insufficient data is available for that window.
    """

    return_5d: float | None
    return_10d: float | None
    return_20d: float | None


def compute_forward_return(close_base: float, close_future: float) -> float:
    """Compute percentage return: ((future - base) / base) * 100, rounded to 2dp.

    Args:
        close_base: Closing price on the backtest date. Must be > 0.
        close_future: Closing price N trading days later.

    Returns:
        Percentage return rounded to two decimal places.
    """
    return round(((close_future - close_base) / close_base) * 100, 2)


def compute_forward_returns_for_symbol(
    backtest_date: date,
    price_series: pd.Series,
    windows: tuple[int, ...] = (5, 10, 20),
) -> ForwardReturns:
    """Compute forward returns at each window (in trading days).

    Args:
        backtest_date: The date from which to measure forward.
        price_series: Series with DatetimeIndex containing closing prices
            from backtest_date onwards.
        windows: Tuple of trading-day offsets (default: 5, 10, 20).

    Returns:
        ForwardReturns with None for any window where data is unavailable.
    """
    # Normalize index to date objects for consistent comparison
    dates = sorted(price_series.index)
    date_to_price: dict[date, float] = {}
    for dt in dates:
        d = dt.date() if hasattr(dt, "date") else dt
        date_to_price[d] = float(price_series[dt])

    # Get base close price (on or closest to backtest_date)
    if backtest_date not in date_to_price:
        # Try to find the backtest_date price in the series
        # If not available, all returns are None
        return ForwardReturns(return_5d=None, return_10d=None, return_20d=None)

    close_base = date_to_price[backtest_date]

    # Count trading days forward for each window
    results: dict[int, float | None] = {}
    for window in windows:
        # Count N trading days forward from backtest_date
        count = 0
        current = backtest_date + timedelta(days=1)
        target_date: date | None = None
        while count < window:
            if is_trading_day(current):
                count += 1
                if count == window:
                    target_date = current
                    break
            current += timedelta(days=1)
            # Safety: don't search more than 60 calendar days per window
            if (current - backtest_date).days > window * 3 + 30:
                break

        if target_date is not None and target_date in date_to_price:
            results[window] = compute_forward_return(
                close_base, date_to_price[target_date]
            )
        else:
            results[window] = None

    return ForwardReturns(
        return_5d=results.get(5),
        return_10d=results.get(10),
        return_20d=results.get(20),
    )
