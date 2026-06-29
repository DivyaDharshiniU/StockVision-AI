"""Property-based tests for ranking correctness in backend/scorer.py.

**Validates: Requirements 6.1, 6.2, 6.4**

Property 18: Descending Score Sort with Complete Preservation
  - 6.1: ranked output is sorted in descending order by bullish_score
  - 6.2: tickers with identical (score, volume_ratio) maintain their relative
         input order (Python's stable sort guarantee)
  - 6.4: all input tickers appear in the output (complete preservation)
"""

from __future__ import annotations

from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from backend.indicators import Indicators
from backend.scorer import compute_score, rank_stocks

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_pos_float = st.floats(min_value=1e-3, max_value=1e9, allow_nan=False, allow_infinity=False)
# Fixed-size list of 30 floats for price history (required by ScoredStock)
_price_hist = st.lists(_pos_float, min_size=30, max_size=30).filter(lambda x: len(x) == 30)

# Fixed symbol pool to ensure uniqueness
_SYMBOL_POOL = [f"TICK{i:03d}" for i in range(60)]


def _indicators_strategy(symbol: str):
    """Build an Indicators instance with a fixed symbol."""
    return st.builds(
        Indicators,
        symbol=st.just(symbol),
        close=_pos_float,
        sma50=_pos_float,
        sma200=_pos_float,
        avg_volume_20=_pos_float,
        volume_last=_pos_float,
        high_52w=_pos_float,
        price_history_30d=_price_hist,
    )


@st.composite
def _indicators_list(draw):
    """Draw a list of Indicators with distinct symbols (0–20 items)."""
    n = draw(st.integers(min_value=0, max_value=20))
    symbols = _SYMBOL_POOL[:n]
    result = []
    for sym in symbols:
        ind = draw(_indicators_strategy(sym))
        assume(ind.avg_volume_20 > 0)
        result.append(ind)
    return result


# ---------------------------------------------------------------------------
# Property 18: Descending Score Sort with Complete Preservation
# Validates: Requirements 6.1, 6.2, 6.4
# ---------------------------------------------------------------------------

@given(indicators=_indicators_list())
@settings(
    max_examples=100,
    suppress_health_check=[
        HealthCheck.large_base_example,
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
)
def test_property18_descending_score_sort_with_complete_preservation(
    indicators: list[Indicators],
) -> None:
    """Property 18: Descending Score Sort with Complete Preservation.

    **Validates: Requirements 6.1, 6.2, 6.4**

    For any list of scored tickers passed to rank_stocks:

    6.1 — The output (picks + non-picks together, reconstructed) is ordered by
          descending (bullish_score, volume_ratio). Specifically, picks are
          ordered descending and no non-pick has a higher (score, vol_ratio)
          than the worst pick.

    6.2 — Among tickers that share both the same score AND the same rounded
          volume_ratio, their relative input order is preserved (stable sort).

    6.4 — total_qualified equals len(indicators): no ticker is filtered out.

    Feature: bullish-stock-scanner, Property 18: Descending Score Sort with Complete Preservation
    """
    top_n = len(indicators)  # request all tickers so we can inspect the full ranking
    company_names = {ind.symbol: f"Company {ind.symbol}" for ind in indicators}

    picks, total_qualified = rank_stocks(indicators, company_names, top_n=top_n)

    # ------------------------------------------------------------------ 6.4
    # Complete preservation: total_qualified must equal total input count.
    assert total_qualified == len(indicators), (
        f"Requirement 6.4 violated: total_qualified={total_qualified} "
        f"but len(indicators)={len(indicators)}"
    )

    # Also: when top_n == len(indicators), every ticker must appear in picks.
    assert len(picks) == len(indicators), (
        f"Requirement 6.4 violated: expected {len(indicators)} picks "
        f"(top_n=len), got {len(picks)}"
    )

    if len(picks) == 0:
        return  # empty input — nothing further to check

    # Compute raw (score, vol_ratio) for each indicator for comparison.
    raw: dict[str, tuple[int, float]] = {}
    for ind in indicators:
        score, vol_ratio = compute_score(ind)
        raw[ind.symbol] = (score, vol_ratio)

    # ------------------------------------------------------------------ 6.1
    # Output must be sorted in descending order by (score, volume_ratio).
    for i in range(len(picks) - 1):
        sym_i = picks[i].symbol
        sym_j = picks[i + 1].symbol
        score_i, vol_i = raw[sym_i]
        score_j, vol_j = raw[sym_j]
        assert (score_i, vol_i) >= (score_j, vol_j), (
            f"Requirement 6.1 violated: picks[{i}] ({sym_i}: score={score_i}, "
            f"vol_ratio={vol_i:.4f}) < picks[{i + 1}] ({sym_j}: score={score_j}, "
            f"vol_ratio={vol_j:.4f})"
        )

    # ------------------------------------------------------------------ 6.2
    # Stable sort: tickers with identical (score, vol_ratio) must keep their
    # relative order from the input list.
    #
    # Build: input_order[symbol] = position in original indicators list.
    input_order: dict[str, int] = {ind.symbol: idx for idx, ind in enumerate(indicators)}

    # Among consecutive pairs of picks that share the same (score, vol_ratio),
    # the one that appeared earlier in the input must appear earlier in output.
    for i in range(len(picks) - 1):
        sym_i = picks[i].symbol
        sym_j = picks[i + 1].symbol
        key_i = raw[sym_i]
        key_j = raw[sym_j]
        if key_i == key_j:
            pos_i = input_order[sym_i]
            pos_j = input_order[sym_j]
            assert pos_i < pos_j, (
                f"Requirement 6.2 violated (stable sort): tickers {sym_i} (input pos {pos_i}) "
                f"and {sym_j} (input pos {pos_j}) share the same sort key {key_i}, "
                f"but their relative order in the output is reversed."
            )
