"""Precision and recall computation for backtest evaluation.

Pure module — no side effects, no I/O.
Computes precision and recall metrics for the model's top-10 picks
against all qualified Nifty 100 symbols, independently per window.
"""

from __future__ import annotations

from dataclasses import dataclass

from .forward_returns import ForwardReturns


@dataclass
class PrecisionRecall:
    """Precision and recall metrics for each forward return window.

    Precision = (true_bullish_picks / 10) * 100
    Recall = (true_bullish_picks / total_true_bullish_all_stocks) * 100

    Where True_Bullish means forward_return > 0%.
    Values are percentages rounded to 2 decimal places, or None
    if data is unavailable for that window.
    """

    precision_5d: float | None
    precision_10d: float | None
    precision_20d: float | None
    recall_5d: float | None
    recall_10d: float | None
    recall_20d: float | None


def classify_true_bullish(forward_return: float | None) -> bool | None:
    """Classify a stock as True_Bullish.

    Returns True if forward_return > 0%, False if <= 0%, None if data unavailable.
    """
    if forward_return is None:
        return None
    return forward_return > 0.0


def compute_precision(true_bullish_picks: int) -> float:
    """Compute precision as percentage: (true_bullish_picks / 10) * 100, rounded to 2dp.

    Denominator is always 10 (the fixed number of top picks).
    """
    return round((true_bullish_picks / 10) * 100, 2)


def compute_recall(true_bullish_picks: int, total_true_bullish: int) -> float | None:
    """Compute recall as percentage: (true_bullish_picks / total_true_bullish) * 100, rounded to 2dp.

    Returns None if total_true_bullish is 0 (no stocks were bullish, recall undefined).
    """
    if total_true_bullish == 0:
        return None
    return round((true_bullish_picks / total_true_bullish) * 100, 2)


def compute_precision_recall(
    pick_forward_returns: list[ForwardReturns],
    all_forward_returns: list[ForwardReturns],
) -> PrecisionRecall:
    """Compute precision and recall for each window (5d, 10d, 20d).

    Args:
        pick_forward_returns: ForwardReturns for the top 10 picks.
        all_forward_returns: ForwardReturns for ALL qualified Nifty 100 symbols
            (includes the picks themselves).

    Returns:
        PrecisionRecall with values for each window.
        Returns None for a window if forward data is unavailable (null) for that window.
    """
    windows = ("5d", "10d", "20d")
    return_attrs = ("return_5d", "return_10d", "return_20d")
    precision_attrs = ("precision_5d", "precision_10d", "precision_20d")
    recall_attrs = ("recall_5d", "recall_10d", "recall_20d")

    results: dict[str, float | None] = {}

    for window, ret_attr, prec_attr, rec_attr in zip(
        windows, return_attrs, precision_attrs, recall_attrs
    ):
        # Get forward returns for this window from picks
        pick_returns = [getattr(fr, ret_attr) for fr in pick_forward_returns]
        # Get forward returns for this window from all symbols
        all_returns = [getattr(fr, ret_attr) for fr in all_forward_returns]

        # Check if forward data is available for this window
        # If all pick returns are None, data is unavailable
        pick_classifications = [classify_true_bullish(r) for r in pick_returns]
        all_classifications = [classify_true_bullish(r) for r in all_returns]

        # If all classifications are None (no data available), return None for both
        if all(c is None for c in pick_classifications):
            results[prec_attr] = None
            results[rec_attr] = None
            continue

        # Count true bullish picks (only non-None classifications)
        true_bullish_picks = sum(1 for c in pick_classifications if c is True)

        # Count total true bullish in all symbols (only non-None classifications)
        total_true_bullish = sum(1 for c in all_classifications if c is True)

        # Compute precision (denominator always 10)
        results[prec_attr] = compute_precision(true_bullish_picks)

        # Compute recall (None if no true bullish stocks in universe)
        results[rec_attr] = compute_recall(true_bullish_picks, total_true_bullish)

    return PrecisionRecall(
        precision_5d=results.get("precision_5d"),
        precision_10d=results.get("precision_10d"),
        precision_20d=results.get("precision_20d"),
        recall_5d=results.get("recall_5d"),
        recall_10d=results.get("recall_10d"),
        recall_20d=results.get("recall_20d"),
    )
