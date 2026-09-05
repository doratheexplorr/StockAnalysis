from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.market_data.base import MarketDataError
from app.market_data.factory import get_market_data_provider
from app.models.enums import Timeframe

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.get("/{symbol}")
def get_ohlcv(
    symbol: str,
    timeframe: str = Query(default="1d"),
    lookback_bars: int = Query(default=200, ge=10, le=2000),
):
    """Raw OHLCV for charting (Stock Detail page). Thin pass-through over
    the configured MarketDataProvider - kept separate from /api/signals so
    the frontend can render a chart even for a symbol with no signals yet.
    """
    if timeframe not in [tf.value for tf in Timeframe]:
        raise HTTPException(422, f"Unsupported timeframe '{timeframe}'")

    provider = get_market_data_provider()
    try:
        df = provider.get_ohlcv(symbol.upper(), timeframe, lookback_bars=lookback_bars)
    except MarketDataError as exc:
        raise HTTPException(502, f"Market data unavailable for {symbol}: {exc}") from exc

    return [
        {
            "time": int(ts.timestamp()),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for ts, row in df.iterrows()
    ]
