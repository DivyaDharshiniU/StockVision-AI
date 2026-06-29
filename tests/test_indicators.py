"""Property-based tests for backend/indicators.py.

**Validates: Requirements 2.3, 3.1, 3.2, 3.3, 3.5**
"""

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from backend.indicators import Indicators, compute_indicators


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(n_rows: int, close_val: float = 100.0, volume_val: float = 1_000_000.0) -> pd.DataFrame:
    """Create a minimal OHLCV DataFrame with *n_rows* rows, all non-NaN."""
    return pd.DataFrame(
        {
            "Close": [close_val] * n_rows,
            "Volume": [volume_val] * n_rows,
        }
    )


# ---------------------------------------------------------------------------
# Property 1: Minimum bar filter
# Validates: Requirements 2.3, 3.5
# ---------------------------------------------------------------------------

# Strategy: row counts strictly below 150 (insufficient data)
_too_few_rows = st.integers(min_value=0, max_value=149)

# Strategy: row counts large enough for all indicators (>=200 closes, >=20 volumes)
_enough_rows = st.integers(min_value=200, max_value=300)


@given(n=_too_few_rows)
@settings(max_examples=200)
def test_property1_returns_none_when_rows_below_150(n: int) -> None:
    """Property 1 (part a): compute_indicators returns None for any df with < 150 rows.

    **Validates: Requirements 2.3, 3.5**
    """
    df = _make_df(n)
    result = compute_indicators("TEST.NS", df)
    assert result is None, (
        f"Expected None for {n} rows (< 150), got {result!r}"
    )


@given(n=_enough_rows)
@settings(max_examples=100)
def test_property1_returns_indicators_when_rows_sufficient(n: int) -> None:
    """Property 1 (part b): compute_indicators returns an Indicators instance for df with >= 200 rows.

    **Validates: Requirements 2.3, 3.5**
    """
    df = _make_df(n)
    result = compute_indicators("TEST.NS", df)
    assert isinstance(result, Indicators), (
        f"Expected Indicators instance for {n} rows (>= 200), got {result!r}"
    )


@given(
    n=st.integers(min_value=0, max_value=149),
    close=st.floats(min_value=1.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    volume=st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=150)
def test_property1_none_iff_rows_below_150_varied_values(
    n: int, close: float, volume: float
) -> None:
    """Property 1 (part c): None condition is independent of actual Close/Volume magnitudes.

    **Validates: Requirements 2.3, 3.5**
    """
    df = _make_df(n, close_val=close, volume_val=volume)
    result = compute_indicators("TEST.NS", df)
    assert result is None, (
        f"Expected None for {n} rows regardless of values, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Property 3: SMA correctness
# Validates: Requirements 3.1, 3.2, 3.3
# ---------------------------------------------------------------------------

# Single value strategies (reused per row)
_positive_close = st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False)
_positive_volume = st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False)


@given(
    n_rows=st.integers(min_value=200, max_value=260),
    closes=st.lists(_positive_close, min_size=260, max_size=260),
    volumes=st.lists(_positive_volume, min_size=260, max_size=260),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example])
def test_property3_sma_correctness(n_rows: int, closes: list[float], volumes: list[float]) -> None:
    """Property 3: SMA50, SMA200, and avg_volume_20 equal their respective window means.

    For any DataFrame with ≥ 200 rows of valid Close and Volume data:
    - sma50   == arithmetic mean of the 50 most-recent closing prices
    - sma200  == arithmetic mean of the 200 most-recent closing prices
    - avg_volume_20 == arithmetic mean of the 20 most-recent daily volumes

    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    df = pd.DataFrame(
        {
            "Close": closes[:n_rows],
            "Volume": volumes[:n_rows],
        }
    )

    result = compute_indicators("TEST.NS", df)

    # With n_rows >= 200 the function must return a valid Indicators instance
    assert isinstance(result, Indicators), (
        f"Expected Indicators for {n_rows} rows, got {result!r}"
    )

    close_arr = np.array(closes[:n_rows], dtype=float)
    volume_arr = np.array(volumes[:n_rows], dtype=float)

    expected_sma50 = float(np.mean(close_arr[-50:]))
    expected_sma200 = float(np.mean(close_arr[-200:]))
    expected_avg_vol20 = float(np.mean(volume_arr[-20:]))

    assert math.isclose(result.sma50, expected_sma50, rel_tol=1e-9), (
        f"sma50 mismatch: got {result.sma50}, expected {expected_sma50}"
    )
    assert math.isclose(result.sma200, expected_sma200, rel_tol=1e-9), (
        f"sma200 mismatch: got {result.sma200}, expected {expected_sma200}"
    )
    assert math.isclose(result.avg_volume_20, expected_avg_vol20, rel_tol=1e-9), (
        f"avg_volume_20 mismatch: got {result.avg_volume_20}, expected {expected_avg_vol20}"
    )


# ---------------------------------------------------------------------------
# Property 4: 52-week high is a maximum
# Validates: Requirements 3.4
# ---------------------------------------------------------------------------

@given(
    closes=st.lists(
        st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
        min_size=252,
        max_size=400,
    ),
    volumes=st.lists(
        st.floats(min_value=1.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        min_size=252,
        max_size=400,
    ),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large, HealthCheck.too_slow])
def test_property4_52w_high_is_maximum(closes: list[float], volumes: list[float]) -> None:
    """Property 4: high_52w equals the maximum of the last 252 closes and is >= every close in that window.

    For any DataFrame with >= 252 rows of closing prices:
    - high_52w == max(closes[-252:])
    - high_52w >= every individual close in the last 252-row window

    **Validates: Requirements 3.4**
    """
    n_rows = min(len(closes), len(volumes))
    df = pd.DataFrame(
        {
            "Close": closes[:n_rows],
            "Volume": volumes[:n_rows],
        }
    )

    result = compute_indicators("TEST.NS", df)

    # n_rows >= 252 >= 200, so compute_indicators must return a valid result
    assert isinstance(result, Indicators), (
        f"Expected Indicators for {n_rows} rows, got {result!r}"
    )

    close_arr = np.array(closes[:n_rows], dtype=float)
    window = close_arr[-252:]
    expected_high_52w = float(np.max(window))

    assert math.isclose(result.high_52w, expected_high_52w, rel_tol=1e-9), (
        f"high_52w mismatch: got {result.high_52w}, expected {expected_high_52w}"
    )

    for i, close_val in enumerate(window):
        assert result.high_52w >= close_val, (
            f"high_52w {result.high_52w} is not >= close[{i}] = {close_val} in the 252-day window"
        )
