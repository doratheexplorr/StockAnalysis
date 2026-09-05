import pandas as pd

from app.market_data.yfinance_provider import YFinanceProvider, _resample_to_4h


def test_supports_timeframe():
    provider = YFinanceProvider()
    assert provider.supports_timeframe("1h") is True
    assert provider.supports_timeframe("4h") is True
    assert provider.supports_timeframe("2h") is False


def test_resample_to_4h_aggregates_ohlcv_correctly():
    idx = pd.date_range("2024-01-01 00:00", periods=8, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10, 11, 12, 13, 20, 21, 22, 23],
            "high": [15, 15, 15, 15, 25, 25, 25, 25],
            "low": [9, 9, 9, 9, 19, 19, 19, 19],
            "close": [11, 12, 13, 14, 21, 22, 23, 24],
            "volume": [100] * 8,
        },
        index=idx,
    )
    resampled = _resample_to_4h(df)
    assert len(resampled) == 2
    first = resampled.iloc[0]
    assert first["open"] == 10
    assert first["close"] == 14
    assert first["high"] == 15
    assert first["low"] == 9
    assert first["volume"] == 400
