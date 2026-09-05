from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class CandlestickDetection(Base, TimestampMixin):
    """Raw output of the pattern-detection layer, independent of scoring.

    Every detector run that finds a match is persisted here, *before* the
    scoring/confirmation pipeline decides whether it becomes a tradeable
    `Signal`. This gives full reproducibility ("why was this signal
    generated") and lets low-score detections be inspected/backtested even
    though they never became an alert.
    """

    __tablename__ = "candlestick_detections"

    id: Mapped[int] = mapped_column(primary_key=True)

    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), index=True)

    pattern_key: Mapped[str] = mapped_column(String(64), index=True)
    pattern_name: Mapped[str] = mapped_column(String(128))
    direction: Mapped[str] = mapped_column(String(10))  # Direction enum value

    # UTC timestamp of the candle's OPEN time that the pattern was evaluated on
    candle_timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    # True once the candle has fully closed and confirmations have run
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    pattern_strength: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1, detector-internal confidence
    raw_ohlcv: Mapped[dict] = mapped_column(JSON)  # the candle window used, for reproducibility

    signal = relationship("Signal", back_populates="detection", uselist=False)
