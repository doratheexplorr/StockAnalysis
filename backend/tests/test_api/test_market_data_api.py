import datetime as dt

import pandas as pd

from app.market_data.base import MarketDataProvider, Quote


class _FakeProvider(MarketDataProvider):
    name = "fake"

    def get_ohlcv(self, symbol, timeframe, lookback_bars=300):
        idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        return pd.DataFrame(
            {"open": [1, 2, 3, 4, 5], "high": [2, 3, 4, 5, 6], "low": [0, 1, 2, 3, 4], "close": [1.5, 2.5, 3.5, 4.5, 5.5], "volume": [10, 20, 30, 40, 50]},
            index=idx,
        )

    def get_latest_price(self, symbol):
        return Quote(symbol=symbol, price=5.5, as_of=pd.Timestamp.now(tz="UTC"))


def test_market_data_endpoint_returns_ohlcv_series(client, monkeypatch):
    import app.api.routers.market_data as market_data_module

    monkeypatch.setattr(market_data_module, "get_market_data_provider", lambda: _FakeProvider())
    resp = client.get("/api/market-data/AAPL", params={"timeframe": "1d", "lookback_bars": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    assert set(data[0].keys()) == {"time", "open", "high", "low", "close", "volume"}


def test_market_data_endpoint_rejects_bad_timeframe(client):
    resp = client.get("/api/market-data/AAPL", params={"timeframe": "3m"})
    assert resp.status_code == 422
