"""Sample OHLCV dataset builders used across the test suite (spec section
16: "Create sample OHLCV datasets specifically for testing candlestick
patterns"). Kept intentionally simple/explicit (no randomness) so every
test is deterministic and its expected outcome is easy to reason about.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd


def candle(o: float, h: float, l: float, c: float, v: float = 100_000) -> dict:
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def build_df(rows: list[dict], start: dt.datetime | None = None, step_minutes: int = 60) -> pd.DataFrame:
    start = start or dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    idx = [start + dt.timedelta(minutes=step_minutes * i) for i in range(len(rows))]
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx, tz="UTC"))


def flat_padding(n: int, base: float = 100.0, step: float = 0.1, volume: float = 100_000) -> list[dict]:
    """Gentle, low-volatility drift used to give indicators (SMA/EMA/RSI/ATR)
    enough history before the "interesting" candle(s) under test."""
    rows = []
    price = base
    for i in range(n):
        o = price
        c = price + step
        h = max(o, c) + step * 2
        l = min(o, c) - step * 2
        rows.append(candle(o, h, l, c, volume))
        price = c
    return rows


def downtrend(n: int, start_price: float, step: float = 1.0, volume: float = 120_000) -> list[dict]:
    rows = []
    price = start_price
    for _ in range(n):
        o = price
        c = price - step
        h = o + step * 0.3
        l = c - step * 0.3
        rows.append(candle(o, h, l, c, volume))
        price = c
    return rows


def uptrend(n: int, start_price: float, step: float = 1.0, volume: float = 120_000) -> list[dict]:
    rows = []
    price = start_price
    for _ in range(n):
        o = price
        c = price + step
        h = c + step * 0.3
        l = o - step * 0.3
        rows.append(candle(o, h, l, c, volume))
        price = c
    return rows


def with_history(pattern_rows: list[dict], history_rows: list[dict] | None = None, pad_before: int = 10) -> list[dict]:
    """Prepends flat padding (and optional trend history) before the
    pattern-specific candles so detectors that need min_bars/trend context
    have enough data."""
    history_rows = history_rows or []
    return flat_padding(pad_before) + history_rows + pattern_rows
