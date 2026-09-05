"""
Central application configuration.

All runtime configuration is sourced from environment variables (see
`.env.example` at the repository root). Nothing secret is hardcoded here.

Config that affects *business logic* (scoring weights, thresholds, enabled
patterns/timeframes) is deliberately kept in the database (`SystemConfiguration`
table, see app.models.config) rather than here, so it can be changed at
runtime from the Settings UI without a redeploy. This module only holds
infrastructure-level settings that legitimately require a process restart.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Stock Signal Engine"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_json: bool = False
    timezone: str = "UTC"  # all internal timestamps are UTC regardless of this

    # --- Database ---
    database_url: str = "sqlite:///./data/app.db"

    # --- Market data provider ---
    # one of: yfinance | alpha_vantage | finnhub | polygon | twelvedata
    market_data_provider: str = "yfinance"
    alpha_vantage_api_key: str | None = None
    finnhub_api_key: str | None = None
    polygon_api_key: str | None = None
    twelvedata_api_key: str | None = None

    # --- News provider ---
    # one of: newsapi | none
    news_provider: str = "newsapi"
    newsapi_api_key: str | None = None
    news_cache_ttl_minutes: int = 30

    # --- Notifications ---
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    alert_email_from: str | None = None
    alert_email_to: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # --- Scheduler / polling ---
    polling_enabled: bool = True
    # how often (seconds) each timeframe's job checks for newly-closed candles
    poll_interval_seconds_intraday: int = 60
    poll_interval_seconds_daily: int = 900

    # --- Signal engine defaults (fallback if DB config row is missing) ---
    default_min_signal_score: int = 70
    default_timeframes: str = "15m,1h,1d"  # comma separated
    default_alert_cooldown_minutes: int = 240

    # --- Candle close confirmation ---
    # if True, evaluate patterns on the still-forming (latest incomplete) candle too,
    # but such detections are always flagged is_confirmed=False and never alerted.
    allow_forming_pattern_detection: bool = True

    # --- API ---
    api_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    secret_key: str = "change-me-in-.env-this-is-not-used-for-anything-security-critical-yet"


@lru_cache
def get_settings() -> Settings:
    return Settings()
