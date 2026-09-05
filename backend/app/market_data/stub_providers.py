"""
Skeleton adapters for market-data providers evaluated but not wired up as
the default (see README "Adding a new market-data provider" and the
evaluation table). Each implements the full `MarketDataProvider` interface
against its respective REST API so switching `MARKET_DATA_PROVIDER` in
`.env` "just works" once an API key is supplied - no changes needed
anywhere else in the app.

These are intentionally minimal (single-endpoint, common response shape)
rather than exhaustive SDK wrappers; harden the parsing/pagination for
your specific plan before relying on one in production.
"""
from __future__ import annotations

import datetime as dt

import httpx
import pandas as pd

from app.core.config import get_settings
from app.market_data.base import InvalidSymbolError, MarketDataError, MarketDataProvider, Quote

_TIMEFRAME_TO_MINUTES = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440,
}


class AlphaVantageProvider(MarketDataProvider):
    """https://www.alphavantage.co - free tier: 25 requests/day, 5/minute.
    Good for daily bars; intraday quickly exhausts the free quota, so this
    is best suited to a paid key or daily-timeframe-only watchlists.
    """

    name = "alpha_vantage"
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self) -> None:
        self.api_key = get_settings().alpha_vantage_api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise MarketDataError("ALPHA_VANTAGE_API_KEY is not configured")
        return self.api_key

    def get_ohlcv(self, symbol: str, timeframe: str, lookback_bars: int = 300) -> pd.DataFrame:
        key = self._require_key()
        if timeframe == "1d":
            function, ts_key = "TIME_SERIES_DAILY", "Time Series (Daily)"
            params = {"function": function, "symbol": symbol, "outputsize": "full", "apikey": key}
        else:
            minutes = _TIMEFRAME_TO_MINUTES[timeframe]
            interval = f"{minutes}min" if minutes < 60 else "60min"
            function, ts_key = "TIME_SERIES_INTRADAY", f"Time Series ({interval})"
            params = {
                "function": function,
                "symbol": symbol,
                "interval": interval,
                "outputsize": "full",
                "apikey": key,
            }
        try:
            resp = httpx.get(self.BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise MarketDataError(f"Alpha Vantage request failed: {exc}") from exc

        series = data.get(ts_key)
        if not series:
            raise InvalidSymbolError(
                f"Alpha Vantage returned no data for {symbol}/{timeframe}: {data.get('Note') or data.get('Information') or data}"
            )

        rows = []
        for ts, ohlcv in series.items():
            rows.append(
                {
                    "timestamp": pd.Timestamp(ts, tz="UTC"),
                    "open": float(ohlcv["1. open"]),
                    "high": float(ohlcv["2. high"]),
                    "low": float(ohlcv["3. low"]),
                    "close": float(ohlcv["4. close"]),
                    "volume": float(ohlcv["5. volume"]),
                }
            )
        df = pd.DataFrame(rows).set_index("timestamp").sort_index()
        return df.tail(lookback_bars)

    def get_latest_price(self, symbol: str) -> Quote:
        key = self._require_key()
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key}
        resp = httpx.get(self.BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json().get("Global Quote", {})
        if not data:
            raise InvalidSymbolError(f"No quote for {symbol}")
        return Quote(symbol=symbol, price=float(data["05. price"]), as_of=pd.Timestamp.now(tz="UTC"))


class FinnhubProvider(MarketDataProvider):
    """https://finnhub.io - generous free tier (60 req/min) with real-time
    quotes; historical candles require a paid plan for most US equities."""

    name = "finnhub"
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self) -> None:
        self.api_key = get_settings().finnhub_api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise MarketDataError("FINNHUB_API_KEY is not configured")
        return self.api_key

    def get_ohlcv(self, symbol: str, timeframe: str, lookback_bars: int = 300) -> pd.DataFrame:
        key = self._require_key()
        resolution = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "60", "1d": "D"}[timeframe]
        minutes = _TIMEFRAME_TO_MINUTES[timeframe]
        now = dt.datetime.now(dt.timezone.utc)
        frm = now - dt.timedelta(minutes=minutes * lookback_bars * 2)
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": int(frm.timestamp()),
            "to": int(now.timestamp()),
            "token": key,
        }
        try:
            resp = httpx.get(f"{self.BASE_URL}/stock/candle", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise MarketDataError(f"Finnhub request failed: {exc}") from exc

        if data.get("s") != "ok":
            raise InvalidSymbolError(f"Finnhub returned status '{data.get('s')}' for {symbol}")

        df = pd.DataFrame(
            {
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            },
            index=pd.to_datetime(data["t"], unit="s", utc=True),
        ).sort_index()
        return df.tail(lookback_bars)

    def get_latest_price(self, symbol: str) -> Quote:
        key = self._require_key()
        resp = httpx.get(f"{self.BASE_URL}/quote", params={"symbol": symbol, "token": key}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if not data or data.get("c") in (None, 0):
            raise InvalidSymbolError(f"No quote for {symbol}")
        return Quote(symbol=symbol, price=float(data["c"]), as_of=pd.Timestamp.now(tz="UTC"))


class PolygonProvider(MarketDataProvider):
    """https://polygon.io - best intraday depth/licensing for production
    use but requires a paid plan for real-time + more than 2 years history."""

    name = "polygon"
    BASE_URL = "https://api.polygon.io"

    def __init__(self) -> None:
        self.api_key = get_settings().polygon_api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise MarketDataError("POLYGON_API_KEY is not configured")
        return self.api_key

    def get_ohlcv(self, symbol: str, timeframe: str, lookback_bars: int = 300) -> pd.DataFrame:
        key = self._require_key()
        multiplier, span = {
            "1m": (1, "minute"), "5m": (5, "minute"), "15m": (15, "minute"),
            "30m": (30, "minute"), "1h": (1, "hour"), "4h": (4, "hour"), "1d": (1, "day"),
        }[timeframe]
        minutes = _TIMEFRAME_TO_MINUTES[timeframe]
        now = dt.datetime.now(dt.timezone.utc)
        frm = (now - dt.timedelta(minutes=minutes * lookback_bars * 2)).strftime("%Y-%m-%d")
        to = now.strftime("%Y-%m-%d")
        url = f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/range/{multiplier}/{span}/{frm}/{to}"
        try:
            resp = httpx.get(url, params={"apiKey": key, "sort": "asc", "limit": 50000}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise MarketDataError(f"Polygon request failed: {exc}") from exc

        results = data.get("results")
        if not results:
            raise InvalidSymbolError(f"Polygon returned no results for {symbol}: {data.get('message', data)}")

        df = pd.DataFrame(results).rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        df.index = pd.to_datetime(df["t"], unit="ms", utc=True)
        return df[["open", "high", "low", "close", "volume"]].sort_index().tail(lookback_bars)

    def get_latest_price(self, symbol: str) -> Quote:
        key = self._require_key()
        resp = httpx.get(f"{self.BASE_URL}/v2/last/trade/{symbol}", params={"apiKey": key}, timeout=20)
        resp.raise_for_status()
        data = resp.json().get("results")
        if not data:
            raise InvalidSymbolError(f"No trade data for {symbol}")
        return Quote(symbol=symbol, price=float(data["p"]), as_of=pd.Timestamp.now(tz="UTC"))


class TwelveDataProvider(MarketDataProvider):
    """https://twelvedata.com - free tier: 8 req/min, 800/day; solid
    intraday coverage across equities/forex/crypto with one unified API."""

    name = "twelvedata"
    BASE_URL = "https://api.twelvedata.com"

    def __init__(self) -> None:
        self.api_key = get_settings().twelvedata_api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise MarketDataError("TWELVEDATA_API_KEY is not configured")
        return self.api_key

    def get_ohlcv(self, symbol: str, timeframe: str, lookback_bars: int = 300) -> pd.DataFrame:
        key = self._require_key()
        interval = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1day"}[
            timeframe
        ]
        params = {"symbol": symbol, "interval": interval, "outputsize": lookback_bars, "apikey": key, "order": "ASC"}
        try:
            resp = httpx.get(f"{self.BASE_URL}/time_series", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise MarketDataError(f"Twelve Data request failed: {exc}") from exc

        values = data.get("values")
        if not values:
            raise InvalidSymbolError(f"Twelve Data returned no values for {symbol}: {data.get('message', data)}")

        df = pd.DataFrame(values).rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp").sort_index()
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)
        return df[["open", "high", "low", "close", "volume"]].tail(lookback_bars)

    def get_latest_price(self, symbol: str) -> Quote:
        key = self._require_key()
        resp = httpx.get(f"{self.BASE_URL}/price", params={"symbol": symbol, "apikey": key}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if "price" not in data:
            raise InvalidSymbolError(f"No price for {symbol}: {data}")
        return Quote(symbol=symbol, price=float(data["price"]), as_of=pd.Timestamp.now(tz="UTC"))
