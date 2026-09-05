"""
Default market-data adapter: Yahoo Finance via the `yfinance` package.

Chosen as the default because it requires no API key and has reasonable
intraday coverage for a first working version (see README "Market data
provider evaluation" for the rate-limit/licensing tradeoffs against
Polygon/Alpha Vantage/Finnhub/Twelve Data, and why those are still wired up
as swappable stubs rather than the default).
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import yfinance as yf

from app.core.logging import get_logger
from app.market_data.base import InvalidSymbolError, MarketDataError, MarketDataProvider, Quote

logger = get_logger(__name__)

# yfinance's native interval strings, and the max lookback period it allows
# for each (Yahoo enforces these; requesting more silently truncates or
# errors depending on version, so we pick a safe period per interval).
_YF_INTERVAL = {
    "1m": ("1m", "7d"),
    "5m": ("5m", "60d"),
    "15m": ("15m", "60d"),
    "30m": ("30m", "60d"),
    "1h": ("60m", "730d"),
    "4h": ("60m", "730d"),  # fetched as 1h then resampled to 4h locally
    "1d": ("1d", "10y"),
}


def _resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    resampled = df.resample("4h", origin="start_day").agg(agg).dropna(how="any")
    return resampled


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    def get_ohlcv(self, symbol: str, timeframe: str, lookback_bars: int = 300) -> pd.DataFrame:
        if timeframe not in _YF_INTERVAL:
            raise MarketDataError(f"Unsupported timeframe '{timeframe}' for provider {self.name}")

        interval, period = _YF_INTERVAL[timeframe]
        try:
            raw = yf.download(
                tickers=symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
            )
        except Exception as exc:  # yfinance raises assorted exceptions on network/HTTP errors
            raise MarketDataError(f"yfinance request failed for {symbol}/{timeframe}: {exc}") from exc

        if raw is None or raw.empty:
            raise InvalidSymbolError(f"No data returned for symbol '{symbol}' (timeframe {timeframe})")

        # yfinance>=0.2 returns MultiIndex columns even for a single ticker
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw.rename(
            columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        )[["open", "high", "low", "close", "volume"]]

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        if timeframe == "4h":
            df = _resample_to_4h(df)

        df = df.tail(lookback_bars)
        return df

    def get_latest_price(self, symbol: str) -> Quote:
        try:
            ticker = yf.Ticker(symbol)
            fast_info = ticker.fast_info
            price = float(fast_info["last_price"])
        except Exception as exc:
            raise MarketDataError(f"Failed to fetch latest price for {symbol}: {exc}") from exc
        return Quote(symbol=symbol, price=price, as_of=pd.Timestamp.now(tz="UTC"))

    def supports_timeframe(self, timeframe: str) -> bool:
        return timeframe in _YF_INTERVAL
