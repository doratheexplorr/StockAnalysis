"""
Market data provider abstraction.

`MarketDataProvider` is the only interface the rest of the system talks to
for OHLCV data - the scheduler, backtester, and API never import a
provider-specific SDK directly. This is what lets the app swap Yahoo
Finance (free, default) for Polygon/Alpha Vantage/Finnhub/Twelve Data later
by adding one adapter class and flipping `MARKET_DATA_PROVIDER` in `.env`
(see app.market_data.factory).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


class MarketDataError(Exception):
    """Raised for any provider failure (network, rate limit, invalid symbol).

    The scheduler pipeline catches this per-symbol so one bad request never
    takes down the whole polling cycle (see app.scheduler.pipeline).
    """


class RateLimitError(MarketDataError):
    pass


class InvalidSymbolError(MarketDataError):
    pass


@dataclass
class Quote:
    symbol: str
    price: float
    as_of: "pd.Timestamp"


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, lookback_bars: int = 300) -> pd.DataFrame:
        """Return a DataFrame indexed by UTC timestamp (ascending, oldest
        first) with columns open/high/low/close/volume. Must include the
        most recent bar even if it is still forming (caller decides whether
        to use it - see app.alerts.candle_close).

        Raises MarketDataError subclasses on failure; must never return
        partially-corrupt data silently.
        """
        raise NotImplementedError

    @abstractmethod
    def get_latest_price(self, symbol: str) -> Quote:
        raise NotImplementedError

    def supports_timeframe(self, timeframe: str) -> bool:
        return True
