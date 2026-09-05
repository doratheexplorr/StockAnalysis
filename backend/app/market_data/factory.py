"""Provider factory - the single place that knows how to construct a
MarketDataProvider from configuration. Everything else depends only on
`MarketDataProvider` (app.market_data.base)."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.market_data.base import MarketDataProvider
from app.market_data.stub_providers import (
    AlphaVantageProvider,
    FinnhubProvider,
    PolygonProvider,
    TwelveDataProvider,
)
from app.market_data.yfinance_provider import YFinanceProvider

_PROVIDERS = {
    "yfinance": YFinanceProvider,
    "alpha_vantage": AlphaVantageProvider,
    "finnhub": FinnhubProvider,
    "polygon": PolygonProvider,
    "twelvedata": TwelveDataProvider,
}


@lru_cache
def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    provider_cls = _PROVIDERS.get(settings.market_data_provider)
    if provider_cls is None:
        raise ValueError(
            f"Unknown MARKET_DATA_PROVIDER '{settings.market_data_provider}'. "
            f"Valid options: {', '.join(_PROVIDERS)}"
        )
    return provider_cls()
