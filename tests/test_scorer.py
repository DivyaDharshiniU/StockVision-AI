"""Property-based tests for backend/scorer.py.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.indicators import Indicators
from backend.scorer import compute_score

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SCORES = {0, 25, 35, 40, 60, 65, 75, 100}


def _make_indicators(sma_signal: int, vol_signal: int, prox_signal: int) -> Indicators:
    """Construct an Indicators instance that produces the requested signal bits.

    Signal encoding:
      sma_signal  = 1  iff  close > sma50  AND  close > sma200
      vol_signal  = 1  iff  volume_last > 1.5 × avg_volume_20
      prox_signal = 1  iff  close >= 0.75 × high_52w

    We use concrete anchor values and adjust the thresholds so each signal
    evaluates deterministically to 0 or 1.
    """
    close = 100.0

    # ---- SMA signal -------------------------------------------------------
    # sma_signal == 1  → close > sma50 and close > sma200
    # sma_signal == 0  → close <= sma50  (which implies the AND fails)
    if sma_signal == 1:
        sma50 = 90.0    # close(100) > 90 ✓
        sma200 = 80.0   # close(100) > 80 ✓
    else:
        sma50 = 110.0   # close(100) <= 110 ✗
        sma200 = 80.0

    # ---- Volume signal ----------------------------------------------------
    # vol_signal == 1  → volume_last > 1.5 × avg_volume_20
    # vol_signal == 0  → volume_last <= 1.5 × avg_volume_20
    avg_volume_20 = 1_000_000.0
    if vol_signal == 1:
        volume_last = 2_000_000.0   # 2.0 × avg > 1.5 ✓
    else:
        volume_last = 1_000_000.0   # 1.0 × avg, not > 1.5 ✗

    # ---- Proximity signal -------------------------------------------------
    # prox_signal == 1  → close >= 0.75 × high_52w
    # prox_signal == 0  → close < 0.75 × high_52w
    if prox_signal == 1:
        high_52w = 100.0   # 0.75 × 100 = 75 ≤ close(100) ✓
    else:
        high_52w = 200.0   # 0.75 × 200 = 150 > close(100) ✗

    return Indicators(
        symbol="TEST.NS",
        close=close,
        sma50=sma50,
        sma200=sma200,
        avg_volume_20=avg_volume_20,
        volume_last=volume_last,
        high_52w=high_52w,
        price_history_30d=[close] * 30,
    )


# ---------------------------------------------------------------------------
# Property 5: Bullish score formula and range invariant
# Validates: Requirements 4.1, 4.2, 4.3, 4.4
# ---------------------------------------------------------------------------

@given(
    sma_signal=st.integers(min_value=0, max_value=1),
    vol_signal=st.integers(min_value=0, max_value=1),
    prox_signal=st.integers(min_value=0, max_value=1),
)
@settings(max_examples=8)   # exactly covers all 8 binary combinations
def test_score_formula_and_range(
    sma_signal: int, vol_signal: int, prox_signal: int
) -> None:
    """Property 5: score == sma×40 + vol×35 + prox×25 and score ∈ {0,25,35,40,60,65,75,100}.

    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """
    ind = _make_indicators(sma_signal, vol_signal, prox_signal)
    score, vol_ratio = compute_score(ind)

    expected_score = sma_signal * 40 + vol_signal * 35 + prox_signal * 25

    assert score == expected_score, (
        f"Score mismatch for signals (sma={sma_signal}, vol={vol_signal}, prox={prox_signal}): "
        f"got {score}, expected {expected_score}"
    )
    assert score in _VALID_SCORES, (
        f"Score {score} is not in the expected set {_VALID_SCORES}"
    )


# ---------------------------------------------------------------------------
# Property 6: Signal conditions match thresholds
# Validates: Requirements 4.1, 4.2, 4.3
# ---------------------------------------------------------------------------

_positive_float = st.floats(min_value=1e-3, max_value=1e9, allow_nan=False, allow_infinity=False)
_price_history = st.lists(_positive_float, min_size=30, max_size=30)


@given(
    close=_positive_float,
    sma50=_positive_float,
    sma200=_positive_float,
    avg_volume_20=_positive_float,
    volume_last=_positive_float,
    high_52w=_positive_float,
    price_history_30d=_price_history,
    symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("Lu",))),
)
@settings(max_examples=500)
def test_signal_threshold_conditions(
    close: float,
    sma50: float,
    sma200: float,
    avg_volume_20: float,
    volume_last: float,
    high_52w: float,
    price_history_30d: list,
    symbol: str,
) -> None:
    """Property 6: each signal bit is 1 iff its threshold condition holds.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    ind = Indicators(
        symbol=symbol,
        close=close,
        sma50=sma50,
        sma200=sma200,
        avg_volume_20=avg_volume_20,
        volume_last=volume_last,
        high_52w=high_52w,
        price_history_30d=price_history_30d,
    )

    score, vol_ratio = compute_score(ind)

    # Derive expected signal bits directly from threshold conditions
    expected_sma_signal = int(close > sma50 and close > sma200)
    expected_vol_ratio = volume_last / avg_volume_20  # avg_volume_20 is always > 0 here
    expected_vol_signal = int(expected_vol_ratio > 1.5)
    expected_prox_signal = int(close >= 0.75 * high_52w)

    # Requirement 4.1: SMA-trend signal
    assert expected_sma_signal == int(close > sma50 and close > sma200), (
        f"SMA signal condition failed: close={close}, sma50={sma50}, sma200={sma200}"
    )

    # Requirement 4.2: Volume-surge signal
    assert expected_vol_signal == int(vol_ratio > 1.5), (
        f"Volume signal condition failed: vol_ratio={vol_ratio}, volume_last={volume_last}, avg_volume_20={avg_volume_20}"
    )

    # Requirement 4.3: 52-week-high proximity signal
    assert expected_prox_signal == int(close >= 0.75 * high_52w), (
        f"Proximity signal condition failed: close={close}, high_52w={high_52w}"
    )

    # Score is consistent with individual signals
    expected_score = expected_sma_signal * 40 + expected_vol_signal * 35 + expected_prox_signal * 25
    assert score == expected_score, (
        f"Score {score} != expected {expected_score} "
        f"(sma={expected_sma_signal}, vol={expected_vol_signal}, prox={expected_prox_signal})"
    )


# ---------------------------------------------------------------------------
# Property 7: Top picks are always the highest-scoring stocks
# Validates: Requirements 5.1, 5.3, 4.5
# ---------------------------------------------------------------------------

from hypothesis import assume
from backend.scorer import rank_stocks

_pos_float = st.floats(min_value=1e-3, max_value=1e9, allow_nan=False, allow_infinity=False)
_price_hist = st.lists(_pos_float, min_size=30, max_size=30)


def _make_indicators_strategy(symbol: str):
    """Build a strategy that produces an Indicators instance with a fixed symbol."""
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


# Generate a list of Indicators with unique symbols by using a fixed alphabet of
# symbol names and drawing a unique subset of them.
_SYMBOL_POOL = [f"SYM{i:03d}" for i in range(50)]


@st.composite
def _indicators_list(draw):
    """Draw a list of Indicators with distinct symbols."""
    n = draw(st.integers(min_value=0, max_value=30))
    symbols = draw(st.permutations(_SYMBOL_POOL).map(lambda s: s[:n]))
    result = []
    for sym in symbols:
        ind = draw(_make_indicators_strategy(sym))
        # Ensure avg_volume_20 > 0 so compute_score won't divide by zero
        assume(ind.avg_volume_20 > 0)
        result.append(ind)
    return result


@given(indicators=_indicators_list())
@settings(max_examples=300)
def test_top_picks_are_highest_scoring(indicators: list) -> None:
    """Property 7: top picks are always the highest-scoring stocks, ties broken by volume_ratio.

    **Validates: Requirements 5.1, 5.3, 4.5**

    Asserts:
    1. Every pick score >= every non-pick score (no outside stock beats an insider).
    2. For any two picks with equal score, the one with higher volume_ratio has a lower rank index.
    3. For any pick vs non-pick with equal score, the pick has higher (or equal) volume_ratio.
    """
    company_names = {ind.symbol: f"Company {ind.symbol}" for ind in indicators}
    picks, total_qualified = rank_stocks(indicators, company_names, top_n=10)

    assert total_qualified == len(indicators), (
        f"total_qualified {total_qualified} != len(indicators) {len(indicators)}"
    )
    assert len(picks) == min(10, len(indicators)), (
        f"Expected {min(10, len(indicators))} picks, got {len(picks)}"
    )

    if not picks:
        return  # empty input — nothing more to check

    # Collect (score, vol_ratio) for picks and non-picks.
    # vol_ratio in ScoredStock is rounded to 2 dp; recompute raw for comparison.
    from backend.scorer import compute_score

    pick_symbols = {p.symbol for p in picks}
    non_picks = [ind for ind in indicators if ind.symbol not in pick_symbols]

    # Build mapping from symbol -> (raw_score, raw_vol_ratio)
    raw = {}
    for ind in indicators:
        score, vol_ratio = compute_score(ind)
        raw[ind.symbol] = (score, vol_ratio)

    # --- Assertion 1: every pick score >= every non-pick score ---------------
    pick_min_score = min(raw[p.symbol][0] for p in picks)
    for ind in non_picks:
        np_score, _ = raw[ind.symbol]
        assert np_score <= pick_min_score, (
            f"Non-pick {ind.symbol} has score {np_score} > min pick score {pick_min_score}"
        )

    # --- Assertion 2: picks with equal score ordered by descending vol_ratio -
    for i in range(len(picks)):
        for j in range(i + 1, len(picks)):
            si, vi = raw[picks[i].symbol]
            sj, vj = raw[picks[j].symbol]
            if si == sj:
                # picks[i] has lower rank index (appears earlier) → must have vol_ratio >= picks[j]
                assert vi >= vj, (
                    f"Picks at indices {i} and {j} have same score {si}, "
                    f"but index {i} has lower vol_ratio ({vi:.6f}) than index {j} ({vj:.6f})"
                )

    # --- Assertion 3: for equal-score pick vs non-pick, pick vol_ratio >= non-pick ----
    for ind in non_picks:
        np_score, np_vol = raw[ind.symbol]
        for p in picks:
            p_score, p_vol = raw[p.symbol]
            if np_score == p_score:
                assert p_vol >= np_vol, (
                    f"Non-pick {ind.symbol} (score={np_score}, vol_ratio={np_vol:.6f}) "
                    f"has higher vol_ratio than pick {p.symbol} (score={p_score}, vol_ratio={p_vol:.6f})"
                )
