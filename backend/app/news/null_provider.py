"""Explicit "no news provider configured" adapter.

Rather than silently returning empty lists (which would look identical to
"checked and found nothing"), this always raises `NewsUnavailableError` so
the alert pipeline is forced to render "News unavailable - technical
analysis only" (spec section 33) instead of ever implying news was checked
when it wasn't.
"""
from __future__ import annotations

from app.news.base import NewsItem, NewsProvider, NewsUnavailableError


class NullNewsProvider(NewsProvider):
    name = "none"

    def get_company_news(self, symbol: str, company_name: str | None = None, lookback_hours: int = 168) -> list[NewsItem]:
        raise NewsUnavailableError("No news provider is configured (NEWS_PROVIDER=none or missing API key)")

    def get_market_news(self, lookback_hours: int = 48) -> list[NewsItem]:
        raise NewsUnavailableError("No news provider is configured (NEWS_PROVIDER=none or missing API key)")

    def get_sector_news(self, sector: str, lookback_hours: int = 72) -> list[NewsItem]:
        raise NewsUnavailableError("No news provider is configured (NEWS_PROVIDER=none or missing API key)")
