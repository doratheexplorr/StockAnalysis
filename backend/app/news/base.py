"""
News provider abstraction (section 31 of the spec).

Like `MarketDataProvider`, nothing outside this package should import a
news SDK/HTTP client directly. `NewsProvider` never fabricates content -
if a provider can't be reached or isn't configured, it raises
`NewsUnavailableError` and callers MUST surface "News unavailable -
technical analysis only" rather than silently proceeding as if news was
checked (see app.scoring.engine).
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import NewsSentiment, NewsSeverity


class NewsUnavailableError(Exception):
    """Raised when news cannot be retrieved (no API key configured, request
    failed, rate limited). Never caught-and-ignored silently - the caller
    must record that news was unavailable."""


@dataclass
class NewsItem:
    headline: str
    source: str
    url: str | None
    published_at: dt.datetime  # UTC
    summary: str | None = None
    sentiment_score: float = 0.0  # VADER compound, filled in by app.news.sentiment
    sentiment_label: NewsSentiment = NewsSentiment.NEUTRAL
    severity: NewsSeverity = NewsSeverity.LOW
    relevance: float = 1.0

    @property
    def age_hours(self) -> float:
        now = dt.datetime.now(dt.timezone.utc)
        return (now - self.published_at).total_seconds() / 3600

    @property
    def recency_bucket(self) -> str:
        """breaking (<1h) / last_24h / last_7d / older - per spec section 26."""
        h = self.age_hours
        if h < 1:
            return "breaking"
        if h < 24:
            return "last_24h"
        if h < 24 * 7:
            return "last_7d"
        return "older"


class NewsProvider(ABC):
    name: str

    @abstractmethod
    def get_company_news(self, symbol: str, company_name: str | None = None, lookback_hours: int = 168) -> list[NewsItem]:
        raise NotImplementedError

    @abstractmethod
    def get_market_news(self, lookback_hours: int = 48) -> list[NewsItem]:
        raise NotImplementedError

    @abstractmethod
    def get_sector_news(self, sector: str, lookback_hours: int = 72) -> list[NewsItem]:
        raise NotImplementedError
