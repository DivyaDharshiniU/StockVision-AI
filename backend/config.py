"""Central configuration — all thresholds loaded from here, never hardcoded."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScoringConfig:
    # Weights
    volume_weight: float = 0.40
    structure_weight: float = 0.30
    pattern_weight: float = 0.20
    rs_weight: float = 0.10

    # Final score weights
    final_composite_w: float = 0.40
    final_minervini_w: float = 0.20
    final_rmv_w: float = 0.15
    final_rs_w: float = 0.15
    final_elder_w: float = 0.10

    # Hard filter thresholds
    min_close_price: float = 20.0          # INR — lower than US$10 equivalent
    min_avg_dollar_volume: float = 5e7     # ₹5 Cr daily avg
    min_history_bars: int = 150
    min_distance_above_52w_low_pct: float = 0.50
    max_distance_below_52w_high_pct: float = 0.35
    earnings_window_days: int = 10

    # Stage 2
    sma50_slope_min: float = 0.003
    sma200_slope_min: float = 0.0
    min_above_52w_low_ratio: float = 1.30
    min_of_52w_high_ratio: float = 0.75

    # Pattern
    min_pattern_confidence: float = 0.4

    # Extension guardrail
    ext_5d_pct: float = 0.10
    ext_10d_pct: float = 0.15
    ext_above_sma20_pct: float = 0.10
    ext_above_sma50_pct: float = 0.15
    ext_above_pivot_pct: float = 0.05

    # Entry / stop / target
    entry_lower_offset: float = 0.001
    entry_upper_offset: float = 0.02
    stop_buffer: float = 0.001
    stop_atr_multiplier: float = 2.0
    max_risk_pct: float = 0.07
    position_risk_pct: float = 0.01
    max_portfolio_hint_pct: float = 0.12

    # Regime
    bearish_score_multiplier: float = 0.65

    # RS ranks
    rs_rank_high: int = 80
    rs_rank_mid_high: int = 70
    rs_rank_mid: int = 50

    # Minervini
    min_minervini_passes: int = 6
    min_minervini_score: int = 60
    pct_from_pivot_max: float = 0.05


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    polygon_token: str = Field(default="", alias="POLYGON_TOKEN")
    massive_base_url: str = Field(
        default="https://api.massive.com", alias="MASSIVE_BASE_URL"
    )

    # Market context — Indian market uses NIFTY 50 proxy (^NSEI via yfinance or
    # "NIFTY" symbol on NSE feed).  We fall back to "NIFTY" for Massive calls.
    regime_symbol: str = Field(default="NIFTY", alias="REGIME_SYMBOL")
    regime_symbol_yf: str = Field(default="^NSEI", alias="REGIME_SYMBOL_YF")

    concurrency_limit: int = Field(default=5, alias="CONCURRENCY_LIMIT")
    request_timeout: int = Field(default=10, alias="REQUEST_TIMEOUT_S")
    cache_dir: str = Field(default=".cache", alias="CACHE_DIR")
    db_path: str = Field(default="scans.db", alias="DB_PATH")
    dedup_ttl_seconds: int = Field(default=60, alias="DEDUP_TTL_SECONDS")

    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def config_hash(settings: Settings) -> str:
    """SHA-256 of the scoring config for reproducibility."""
    d = {k: v for k, v in vars(settings.scoring).items() if not k.startswith("_")}
    raw = json.dumps(d, sort_keys=True)
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()[:16]
