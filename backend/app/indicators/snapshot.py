"""
Aggregates every indicator calculation into a single `IndicatorValues` snapshot
for the latest (most recent CLOSED) candle in a DataFrame. This is the object
the pattern-confirmation and scoring layers consume, and the shape persisted
via app.models.indicator_snapshot.IndicatorSnapshot.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from app.indicators import core, structure


@dataclass
class IndicatorValues:
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    ema_9: float | None
    ema_21: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    macd_hist: float | None
    atr_14: float | None
    volume: float | None
    avg_volume_20: float | None
    relative_volume: float | None
    recent_high_20: float | None
    recent_low_20: float | None
    support_level: float | None
    resistance_level: float | None
    trend_direction: str
    structure: str
    breakout: str
    consolidation: bool

    def as_dict(self) -> dict:
        return asdict(self)


def _last_or_none(series: pd.Series) -> float | None:
    if series is None or len(series) == 0:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)


def compute_indicator_snapshot(df: pd.DataFrame) -> IndicatorValues:
    """`df` must contain only CLOSED candles (caller is responsible for
    stripping the still-forming bar - see app.alerts.candle_close)."""
    macd_df = core.macd(df)
    trend = structure.trend_direction(df)
    support, resistance = structure.support_resistance(df)

    return IndicatorValues(
        sma_20=_last_or_none(core.sma(df, 20)),
        sma_50=_last_or_none(core.sma(df, 50)),
        sma_200=_last_or_none(core.sma(df, 200)),
        ema_9=_last_or_none(core.ema(df, 9)),
        ema_21=_last_or_none(core.ema(df, 21)),
        rsi_14=_last_or_none(core.rsi(df, 14)),
        macd=_last_or_none(macd_df["macd"]),
        macd_signal=_last_or_none(macd_df["signal"]),
        macd_hist=_last_or_none(macd_df["hist"]),
        atr_14=_last_or_none(core.atr(df, 14)),
        volume=_last_or_none(df["volume"]),
        avg_volume_20=_last_or_none(core.average_volume(df, 20)),
        relative_volume=_last_or_none(core.relative_volume(df, 20)),
        recent_high_20=_last_or_none(core.recent_high(df, 20)),
        recent_low_20=_last_or_none(core.recent_low(df, 20)),
        support_level=support,
        resistance_level=resistance,
        trend_direction=trend.direction,
        structure=trend.structure,
        breakout=structure.breakout_breakdown(df),
        consolidation=structure.is_consolidating(df),
    )
