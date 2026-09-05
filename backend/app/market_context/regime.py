"""
Market-regime classification (spec section 30): uses SPY (S&P 500 proxy)
and VIX daily data to decide whether the broader tape is supportive of or
hostile to a given signal's direction. Deliberately simple (moving-average
trend + VIX level) rather than a multi-factor macro model - the goal is a
directional sanity check ("don't treat a bullish candle as equally strong
during a severe market-wide selloff"), not a standalone macro forecast.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.indicators.core import sma
from app.market_data.base import MarketDataError
from app.market_data.base import MarketDataProvider
from app.models.enums import Direction, MarketRegime


@dataclass
class RegimeContext:
    regime: MarketRegime
    spy_trend: str  # up/down/sideways
    vix_level: float | None
    vix_bucket: str  # low/normal/elevated/high
    supportive_for: list[Direction]
    description: str


def _vix_bucket(vix: float | None) -> str:
    if vix is None:
        return "unknown"
    if vix < 15:
        return "low"
    if vix < 20:
        return "normal"
    if vix < 28:
        return "elevated"
    return "high"


def classify_market_regime(provider: MarketDataProvider) -> RegimeContext:
    try:
        spy = provider.get_ohlcv("SPY", "1d", lookback_bars=260)
        spy_sma20 = sma(spy, 20).iloc[-1]
        spy_sma50 = sma(spy, 50).iloc[-1]
        spy_close = spy["close"].iloc[-1]
        spy_pct_5d = (spy_close - spy["close"].iloc[-6]) / spy["close"].iloc[-6] if len(spy) > 6 else 0.0
    except (MarketDataError, IndexError, KeyError):
        spy_sma20 = spy_sma50 = spy_close = None
        spy_pct_5d = 0.0

    try:
        vix = provider.get_ohlcv("^VIX", "1d", lookback_bars=5)
        vix_level = float(vix["close"].iloc[-1])
    except Exception:
        vix_level = None

    vix_bucket = _vix_bucket(vix_level)

    if spy_close is None or spy_sma20 is None or spy_sma50 is None or pd.isna(spy_sma20) or pd.isna(spy_sma50):
        spy_trend = "sideways"
    elif spy_close > spy_sma20 > spy_sma50:
        spy_trend = "up"
    elif spy_close < spy_sma20 < spy_sma50:
        spy_trend = "down"
    else:
        spy_trend = "sideways"

    if vix_bucket == "high":
        regime = MarketRegime.HIGH_VOLATILITY
    elif spy_trend == "up" and spy_pct_5d > 0.02:
        regime = MarketRegime.STRONG_BULLISH
    elif spy_trend == "up":
        regime = MarketRegime.BULLISH
    elif spy_trend == "down" and spy_pct_5d < -0.02:
        regime = MarketRegime.STRONG_BEARISH
    elif spy_trend == "down":
        regime = MarketRegime.BEARISH
    else:
        regime = MarketRegime.NEUTRAL

    supportive_for = {
        MarketRegime.STRONG_BULLISH: [Direction.BULLISH],
        MarketRegime.BULLISH: [Direction.BULLISH],
        MarketRegime.NEUTRAL: [Direction.BULLISH, Direction.BEARISH],
        MarketRegime.BEARISH: [Direction.BEARISH],
        MarketRegime.STRONG_BEARISH: [Direction.BEARISH],
        MarketRegime.HIGH_VOLATILITY: [],
    }[regime]

    description = (
        f"S&P 500 (SPY) trend: {spy_trend}; VIX: "
        f"{'n/a' if vix_level is None else f'{vix_level:.1f} ({vix_bucket})'} -> regime = {regime.value}"
    )

    return RegimeContext(
        regime=regime,
        spy_trend=spy_trend,
        vix_level=vix_level,
        vix_bucket=vix_bucket,
        supportive_for=supportive_for,
        description=description,
    )


def sector_trend(provider: MarketDataProvider, etf_symbol: str) -> str:
    try:
        df = provider.get_ohlcv(etf_symbol, "1d", lookback_bars=60)
        s20 = sma(df, 20).iloc[-1]
        close = df["close"].iloc[-1]
        if pd.isna(s20):
            return "sideways"
        return "up" if close > s20 else "down"
    except Exception:
        return "unknown"
