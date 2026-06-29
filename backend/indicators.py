"""Pure indicator computation for StockVision AI.

Computes SMA50, SMA200, 20-session average volume, 52-week high, and
30-day price history from a pandas OHLCV DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Indicators:
    symbol: str
    close: float
    sma50: float
    sma200: float
    avg_volume_20: float
    volume_last: float
    high_52w: float
    price_history_30d: list[float]  # oldest first


def compute_indicators(symbol: str, df: pd.DataFrame) -> Indicators | None:
    """Compute technical indicators from an OHLCV DataFrame.

    Returns None if df has fewer than 150 bars or any required
    indicator cannot be computed (closes < 200 or volumes < 20).
    """
    if len(df) < 150:
        return None

    closes = df["Close"].dropna()
    volumes = df["Volume"].dropna()

    if len(closes) < 200 or len(volumes) < 20:
        return None

    return Indicators(
        symbol=symbol,
        close=float(closes.iloc[-1]),
        sma50=float(closes.iloc[-50:].mean()),
        sma200=float(closes.iloc[-200:].mean()),
        avg_volume_20=float(volumes.iloc[-20:].mean()),
        volume_last=float(volumes.iloc[-1]),
        high_52w=float(
            closes.iloc[-252:].max() if len(closes) >= 252 else closes.max()
        ),
        price_history_30d=[float(x) for x in closes.iloc[-30:]],
    )
