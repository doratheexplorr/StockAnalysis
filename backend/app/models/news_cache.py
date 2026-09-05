from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class NewsCacheItem(Base, TimestampMixin):
    """Cached news items (company/sector/macro) with sentiment + severity.

    Caching avoids re-hitting rate-limited news APIs on every polling cycle
    and gives full source transparency for any signal that used it later
    (headline, source, published_at, sentiment, severity are all preserved
    exactly as retrieved - never fabricated, see app.news.base).
    """

    __tablename__ = "news_cache"

    id: Mapped[int] = mapped_column(primary_key=True)

    category: Mapped[str] = mapped_column(String(20), index=True)  # company/sector/macro
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    headline: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

    sentiment_score: Mapped[float] = mapped_column(Float)  # VADER compound, -1..1
    sentiment_label: Mapped[str] = mapped_column(String(10))  # NewsSentiment value
    severity: Mapped[str] = mapped_column(String(10))  # NewsSeverity value
    relevance: Mapped[float] = mapped_column(Float, default=1.0)  # 0-1
