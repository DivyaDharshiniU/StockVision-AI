"""Bullish scorer for StockVision AI.

Computes a composite Bullish Score from three binary signals:
  - SMA-trend signal    (weight 40)
  - Volume-surge signal (weight 35)
  - 52w-high proximity  (weight 25)
"""

from __future__ import annotations

from dataclasses import dataclass

from .indicators import Indicators


@dataclass
class ScoredStock:
    rank: int
    symbol: str
    company_name: str
    score: int              # 0–100
    close: float
    sma50: float
    sma200: float
    volume_ratio: float
    pct_from_52w_high: float
    price_history_30d: list[float]


def compute_score(ind: Indicators) -> tuple[int, float]:
    """Returns (bullish_score, volume_ratio).

    Score formula:
        sma_signal  × 40  (1 iff close > sma50 AND close > sma200)
        vol_signal  × 35  (1 iff volume_last > 1.5 × avg_volume_20)
        prox_signal × 25  (1 iff close >= 0.75 × high_52w)
    """
    sma_signal = int(ind.close > ind.sma50 and ind.close > ind.sma200)
    vol_ratio = ind.volume_last / ind.avg_volume_20 if ind.avg_volume_20 > 0 else 0.0
    vol_signal = int(vol_ratio > 1.5)
    prox_signal = int(ind.close >= 0.75 * ind.high_52w)
    score = sma_signal * 40 + vol_signal * 35 + prox_signal * 25
    return score, vol_ratio


def rank_stocks(
    indicators: list[Indicators],
    company_names: dict[str, str],
    top_n: int = 10,
) -> tuple[list[ScoredStock], int]:
    """Return (top_picks, total_qualified). Ties broken by descending volume_ratio."""
    scored = []
    for ind in indicators:
        score, vol_ratio = compute_score(ind)
        pct_from_high = (
            round((ind.high_52w - ind.close) / ind.high_52w * 100, 2)
            if ind.high_52w > 0
            else 0.0
        )
        scored.append((score, vol_ratio, ind, pct_from_high))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    total_qualified = len(scored)
    top = scored[:top_n]

    picks = [
        ScoredStock(
            rank=i + 1,
            symbol=item[2].symbol,
            company_name=company_names.get(item[2].symbol, item[2].symbol),
            score=item[0],
            close=round(item[2].close, 2),
            sma50=round(item[2].sma50, 2),
            sma200=round(item[2].sma200, 2),
            volume_ratio=round(item[1], 2),
            pct_from_52w_high=item[3],
            price_history_30d=item[2].price_history_30d,
        )
        for i, item in enumerate(top)
    ]
    return picks, total_qualified
