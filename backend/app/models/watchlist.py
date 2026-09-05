from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Watchlist(Base, TimestampMixin):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="My Watchlist")

    user = relationship("User", back_populates="watchlists")
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base, TimestampMixin):
    """A single monitored stock within a watchlist.

    Per-item overrides (timeframes, min score, enabled patterns, notification
    channels) fall back to the global `SystemConfiguration` defaults when
    left null/empty, so a user can just "add a ticker" without configuring
    everything up front, but can fine-tune per symbol when they want to.
    """

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id"), index=True)

    symbol: Mapped[str] = mapped_column(String(20), index=True)
    market: Mapped[str] = mapped_column(String(20), default="US")  # architected for future non-US markets
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # comma-free JSON list of Timeframe values, e.g. ["15m", "1h", "1d"]; null/empty = use global default
    timeframes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # null = use global default_min_signal_score
    min_score_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # JSON list of pattern keys (see app.patterns.registry); null/empty = all enabled patterns
    enabled_patterns: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # JSON list of NotificationChannelType values; null = use global defaults
    notification_channels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    watchlist = relationship("Watchlist", back_populates="items")

    __table_args__ = ()
