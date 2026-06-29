"""Indian market calendar utilities.

Trading day = a session where NSE/BSE is open.
Weekends and Indian public holidays do not count.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytz

# Known NSE/BSE holidays for 2025-2026 (non-exhaustive; extend as needed).
_NSE_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 26),  # Republic Day
    date(2025, 3, 14),  # Holi
    date(2025, 4, 14),  # Dr. Ambedkar Jayanti / Good Friday overlap
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),   # Maharashtra Day
    date(2025, 8, 15),  # Independence Day
    date(2025, 10, 2),  # Gandhi Jayanti
    date(2025, 10, 24), # Dussehra
    date(2025, 11, 5),  # Diwali Laxmi Puja (Muhurat)
    date(2025, 12, 25), # Christmas
    # 2026
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Holi
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Gandhi Jayanti
}

_IST = pytz.timezone("Asia/Kolkata")


def is_trading_day(d: date) -> bool:
    """Return True if d is a weekday and not a known holiday."""
    return d.weekday() < 5 and d not in _NSE_HOLIDAYS


def prev_trading_day(d: date | None = None) -> date:
    """Return the most recent trading day ≤ d (default: today IST)."""
    if d is None:
        from datetime import datetime
        d = datetime.now(_IST).date()
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def trading_days_between(start: date, end: date) -> list[date]:
    """Return all trading days in [start, end] inclusive."""
    days: list[date] = []
    current = start
    while current <= end:
        if is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


def subtract_trading_days(d: date, n: int) -> date:
    """Return the date that is n trading days before d."""
    count = 0
    current = d - timedelta(days=1)
    while count < n:
        if is_trading_day(current):
            count += 1
        if count < n:
            current -= timedelta(days=1)
    return current


def calendar_days_for_n_trading(n: int) -> int:
    """Rough calendar-day buffer to cover n trading days (1.5× + 20 holiday pad)."""
    return int(n * 1.5) + 20
