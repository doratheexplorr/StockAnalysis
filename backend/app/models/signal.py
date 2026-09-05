from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Signal(Base, TimestampMixin):
    """A fully-scored, alert-worthy (or explicitly suppressed) trading setup.

    This is the central "explain everything" record: it stores the score
    breakdown, the risk levels, the news/regime context and the fingerprint
    used for deduplication, so the full alert can be reconstructed or
    re-rendered at any time without recomputing anything.
    """

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)

    detection_id: Mapped[int | None] = mapped_column(ForeignKey("candlestick_detections.id"), nullable=True)
    indicator_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("indicator_snapshots.id"), nullable=True
    )

    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), index=True)
    pattern_key: Mapped[str] = mapped_column(String(64))
    pattern_name: Mapped[str] = mapped_column(String(128))
    direction: Mapped[str] = mapped_column(String(10))

    candle_timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    detected_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)

    # --- Scoring ---
    quality_score: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(20))  # SignalClassification value
    score_breakdown: Mapped[dict] = mapped_column(JSON)  # {"pattern": 28, "trend": 18, ... , "weights_used": {...}}

    # --- Risk levels ---
    current_price: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    target_1: Mapped[float] = mapped_column(Float)
    target_2: Mapped[float] = mapped_column(Float)
    target_3: Mapped[float] = mapped_column(Float)
    risk_per_share: Mapped[float] = mapped_column(Float)
    reward_to_t1: Mapped[float] = mapped_column(Float)
    reward_to_t2: Mapped[float] = mapped_column(Float)
    reward_to_t3: Mapped[float] = mapped_column(Float)
    rr_t1: Mapped[float] = mapped_column(Float)
    rr_t2: Mapped[float] = mapped_column(Float)
    rr_t3: Mapped[float] = mapped_column(Float)
    risk_methodology: Mapped[str] = mapped_column(String(512))

    # --- Supporting context (stored fully so the alert is reproducible) ---
    technical_confirmations: Mapped[dict] = mapped_column(JSON)  # list of {"label": ..., "passed": bool, "detail": ...}
    news_context: Mapped[dict] = mapped_column(JSON)  # {"status": "supportive|conflicting|neutral|unavailable", "items": [...]}
    market_context: Mapped[dict] = mapped_column(JSON)  # {"regime": ..., "spy_trend": ..., "sector_trend": ...}
    explanation: Mapped[str] = mapped_column(String(2000))

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # dedup fingerprint: hash(symbol, timeframe, pattern_key, candle_timestamp)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, unique=True)

    detection = relationship("CandlestickDetection", back_populates="signal")
    alert_history = relationship("AlertHistory", back_populates="signal", cascade="all, delete-orphan")
