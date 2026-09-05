from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class IndicatorSnapshot(Base, TimestampMixin):
    """A point-in-time snapshot of all computed indicators for a symbol/timeframe/candle.

    Persisted independently of signals so indicator history can be charted
    and so a signal can always point back to the exact numbers that produced
    its score, even if indicator logic changes later.
    """

    __tablename__ = "indicator_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), index=True)
    candle_timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)

    sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_9: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_21: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_volume_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_high_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_low_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    resistance_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)  # up/down/sideways
    structure: Mapped[str | None] = mapped_column(String(20), nullable=True)  # HH_HL / LH_LL / mixed
    breakout: Mapped[str | None] = mapped_column(String(20), nullable=True)  # breakout/breakdown/none
    consolidation: Mapped[bool | None] = mapped_column(nullable=True)

    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
