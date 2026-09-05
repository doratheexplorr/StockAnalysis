from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.news.base import NewsProvider
from app.news.newsapi_provider import NewsAPIProvider
from app.news.null_provider import NullNewsProvider

_PROVIDERS = {
    "newsapi": NewsAPIProvider,
    "none": NullNewsProvider,
}


@lru_cache
def get_news_provider() -> NewsProvider:
    settings = get_settings()
    if settings.news_provider == "newsapi" and not settings.newsapi_api_key:
        # graceful degrade: configured for newsapi but no key supplied yet
        return NullNewsProvider()
    provider_cls = _PROVIDERS.get(settings.news_provider, NullNewsProvider)
    return provider_cls()
