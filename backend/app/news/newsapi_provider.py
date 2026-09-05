"""
NewsAPI.org adapter (https://newsapi.org).

Free "Developer" tier: 100 requests/day, articles capped at ~1 month old,
and (important licensing caveat) the free tier is for development/testing
only - production use requires a paid plan. Chosen as the default because
it aggregates thousands of sources with one simple key and matches the
existing side-project stack noted in the user's own notes. See README
"News provider evaluation" for alternatives (Finnhub news, Marketaux,
Alpha Vantage NEWS_SENTIMENT) if a different tradeoff is needed.
"""
from __future__ import annotations

import datetime as dt

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.news.base import NewsItem, NewsProvider, NewsUnavailableError
from app.news.sentiment import analyze_sentiment, classify_severity

logger = get_logger(__name__)


class NewsAPIProvider(NewsProvider):
    name = "newsapi"
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self) -> None:
        self.api_key = get_settings().newsapi_api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise NewsUnavailableError("NEWSAPI_API_KEY is not configured")
        return self.api_key

    def _search(self, query: str, lookback_hours: int, page_size: int = 20) -> list[NewsItem]:
        key = self._require_key()
        since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        params = {
            "q": query,
            "from": since,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": page_size,
            "apiKey": key,
        }
        try:
            resp = httpx.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise NewsUnavailableError(f"NewsAPI request failed: {exc}") from exc

        if data.get("status") != "ok":
            raise NewsUnavailableError(f"NewsAPI returned an error: {data.get('message', data)}")

        items: list[NewsItem] = []
        for article in data.get("articles", []):
            headline = article.get("title") or ""
            summary = article.get("description")
            published_raw = article.get("publishedAt")
            if not headline or not published_raw:
                continue
            published_at = dt.datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            score, label = analyze_sentiment(f"{headline}. {summary or ''}")
            severity = classify_severity(headline, summary)
            items.append(
                NewsItem(
                    headline=headline,
                    source=(article.get("source") or {}).get("name", "Unknown"),
                    url=article.get("url"),
                    published_at=published_at,
                    summary=summary,
                    sentiment_score=score,
                    sentiment_label=label,
                    severity=severity,
                )
            )
        return items

    def get_company_news(
        self, symbol: str, company_name: str | None = None, lookback_hours: int = 168
    ) -> list[NewsItem]:
        query = f'"{company_name}" OR "{symbol}"' if company_name else symbol
        return self._search(query, lookback_hours)

    def get_market_news(self, lookback_hours: int = 48) -> list[NewsItem]:
        query = "stock market OR Federal Reserve OR inflation OR S&P 500"
        return self._search(query, lookback_hours)

    def get_sector_news(self, sector: str, lookback_hours: int = 72) -> list[NewsItem]:
        return self._search(sector, lookback_hours)
