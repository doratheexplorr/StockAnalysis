from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WatchlistItemCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    market: str = "US"
    enabled: bool = True
    timeframes: list[str] | None = None
    min_score_override: int | None = None
    enabled_patterns: list[str] | None = None
    notification_channels: list[str] | None = None


class WatchlistItemUpdate(BaseModel):
    enabled: bool | None = None
    timeframes: list[str] | None = None
    min_score_override: int | None = None
    enabled_patterns: list[str] | None = None
    notification_channels: list[str] | None = None


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    market: str
    enabled: bool
    timeframes: list[str] | None
    min_score_override: int | None
    enabled_patterns: list[str] | None
    notification_channels: list[str] | None
