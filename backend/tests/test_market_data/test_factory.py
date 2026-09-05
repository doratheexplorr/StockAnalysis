import pytest

from app.market_data.factory import get_market_data_provider
from app.market_data.stub_providers import FinnhubProvider
from app.market_data.yfinance_provider import YFinanceProvider


def test_default_provider_is_yfinance(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    get_market_data_provider.cache_clear()
    provider = get_market_data_provider()
    assert isinstance(provider, YFinanceProvider)


def test_switching_provider_via_env_var(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "finnhub")
    get_settings.cache_clear()
    get_market_data_provider.cache_clear()
    provider = get_market_data_provider()
    assert isinstance(provider, FinnhubProvider)
    monkeypatch.delenv("MARKET_DATA_PROVIDER", raising=False)
    get_settings.cache_clear()
    get_market_data_provider.cache_clear()


def test_unknown_provider_raises(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "not_a_real_provider")
    get_settings.cache_clear()
    get_market_data_provider.cache_clear()
    with pytest.raises(ValueError):
        get_market_data_provider()
    monkeypatch.delenv("MARKET_DATA_PROVIDER", raising=False)
    get_settings.cache_clear()
    get_market_data_provider.cache_clear()


def test_provider_without_api_key_raises_on_use():
    provider = FinnhubProvider()
    with pytest.raises(Exception):
        provider.get_ohlcv("AAPL", "1d")
