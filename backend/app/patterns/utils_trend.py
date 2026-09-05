"""Small helper shared by patterns that require prior-trend context to
disambiguate visually-identical candles (hammer vs hanging man, shooting
star vs inverted hammer)."""
from __future__ import annotations

import pandas as pd


def preceding_trend(df: pd.DataFrame, lookback: int = 5, exclude_last: int = 1) -> str:
    """Simple close-to-close slope over the `lookback` bars preceding the
    pattern candle(s) (the last `exclude_last` bars are excluded from the
    comparison since they ARE the pattern). Returns 'up', 'down', or 'flat'.
    """
    if len(df) < lookback + exclude_last + 1:
        return "flat"
    window = df.iloc[-(lookback + exclude_last + 1) : -exclude_last]
    if len(window) < 2:
        return "flat"
    start, end = window["close"].iloc[0], window["close"].iloc[-1]
    change_pct = (end - start) / start if start else 0.0
    if change_pct <= -0.01:
        return "down"
    if change_pct >= 0.01:
        return "up"
    return "flat"
