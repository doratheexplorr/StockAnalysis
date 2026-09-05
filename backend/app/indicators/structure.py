"""
Price-structure analysis: support/resistance, higher-highs/higher-lows,
breakout/breakdown detection, consolidation, and trend direction.

These are heuristic, swing-based implementations chosen for explainability
(every value can be pointed back to specific bars) rather than maximal
sophistication - the scoring engine only needs a reasonably reliable signal
of "is this a confirmed trend / breakout", not a perfect one, and the
confirmation-factor design (see app.scoring.engine) means no single
indicator being imperfect can by itself produce a bad alert.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.indicators.core import atr, sma


def find_swing_points(df: pd.DataFrame, order: int = 3) -> tuple[pd.Series, pd.Series]:
    """Return boolean Series marking local swing highs / swing lows.

    A bar is a swing high if its high is the max within +/- `order` bars
    (and symmetrically for swing lows). Used for support/resistance and
    HH/HL vs LH/LL structure detection.
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)

    for i in range(order, n - order):
        window_high = highs[i - order : i + order + 1]
        window_low = lows[i - order : i + order + 1]
        if highs[i] == window_high.max() and np.argmax(window_high) == order:
            is_high[i] = True
        if lows[i] == window_low.min() and np.argmin(window_low) == order:
            is_low[i] = True

    return pd.Series(is_high, index=df.index), pd.Series(is_low, index=df.index)


def support_resistance(df: pd.DataFrame, lookback: int = 60, order: int = 3) -> tuple[float | None, float | None]:
    """Nearest support (below current close) and resistance (above current close),
    derived from recent swing lows/highs within `lookback` bars.
    """
    window = df.tail(lookback)
    if len(window) < order * 2 + 1:
        return None, None

    swing_high, swing_low = find_swing_points(window, order=order)
    current_price = df["close"].iloc[-1]

    resistances = window.loc[swing_high, "high"]
    resistances = resistances[resistances > current_price]
    supports = window.loc[swing_low, "low"]
    supports = supports[supports < current_price]

    resistance = float(resistances.min()) if not resistances.empty else None
    support = float(supports.max()) if not supports.empty else None
    return support, resistance


@dataclass
class TrendStructure:
    direction: str  # "up" | "down" | "sideways"
    structure: str  # "higher_highs_higher_lows" | "lower_highs_lower_lows" | "mixed"


def trend_direction(df: pd.DataFrame, fast_period: int = 20, slow_period: int = 50) -> TrendStructure:
    """Trend direction from moving-average slope/ordering, cross-checked
    against swing-point structure (higher highs/lows vs lower highs/lows).
    """
    if len(df) < slow_period + 5:
        return TrendStructure(direction="sideways", structure="mixed")

    fast_ma = sma(df, fast_period)
    slow_ma = sma(df, slow_period)

    fast_now, fast_prev = fast_ma.iloc[-1], fast_ma.iloc[-5]
    slow_now = slow_ma.iloc[-1]
    close_now = df["close"].iloc[-1]

    if pd.isna(fast_now) or pd.isna(slow_now):
        ma_direction = "sideways"
    elif close_now > slow_now and fast_now > slow_now and fast_now >= fast_prev:
        ma_direction = "up"
    elif close_now < slow_now and fast_now < slow_now and fast_now <= fast_prev:
        ma_direction = "down"
    else:
        ma_direction = "sideways"

    swing_high, swing_low = find_swing_points(df.tail(max(slow_period, 40)), order=3)
    highs = df.tail(max(slow_period, 40)).loc[swing_high, "high"]
    lows = df.tail(max(slow_period, 40)).loc[swing_low, "low"]

    structure = "mixed"
    if len(highs) >= 2 and len(lows) >= 2:
        if highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
            structure = "higher_highs_higher_lows"
        elif highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
            structure = "lower_highs_lower_lows"

    return TrendStructure(direction=ma_direction, structure=structure)


def is_consolidating(df: pd.DataFrame, period: int = 14, atr_period: int = 14, threshold: float = 0.6) -> bool:
    """A simple volatility-contraction consolidation heuristic: true if the
    recent trading range is small relative to ATR (i.e. price is compressing).
    """
    if len(df) < max(period, atr_period) + 5:
        return False
    window = df.tail(period)
    price_range = window["high"].max() - window["low"].min()
    current_atr = atr(df, atr_period).iloc[-1]
    if pd.isna(current_atr) or current_atr == 0:
        return False
    return bool(price_range < current_atr * period * threshold / 2)


def breakout_breakdown(
    df: pd.DataFrame, lookback: int = 20, confirm_with_volume: bool = True, rel_volume_threshold: float = 1.3
) -> str:
    """Returns 'breakout', 'breakdown', or 'none'.

    A breakout/breakdown requires the current close to exceed the prior
    `lookback`-bar high/low (excluding current bar) - optionally requiring
    above-average relative volume as confirmation, since an unconfirmed
    breakout is a classic false-signal source this system is designed to
    filter out (see README "Product principle").
    """
    from app.indicators.core import relative_volume as rel_vol_fn

    if len(df) < lookback + 2:
        return "none"

    prior = df.iloc[:-1].tail(lookback)
    current_close = df["close"].iloc[-1]

    rel_vol = rel_vol_fn(df, lookback).iloc[-1] if confirm_with_volume else None
    volume_ok = (not confirm_with_volume) or (pd.notna(rel_vol) and rel_vol >= rel_volume_threshold)

    if current_close > prior["high"].max() and volume_ok:
        return "breakout"
    if current_close < prior["low"].min() and volume_ok:
        return "breakdown"
    return "none"
