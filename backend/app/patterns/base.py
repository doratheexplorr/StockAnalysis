"""
Shared types + helper math for candlestick pattern detectors.

Every detector is a small, independently testable class implementing
`PatternDetector.detect(df) -> PatternMatch | None`. `df` is a pandas
DataFrame of OHLCV bars (oldest first); detectors look only at the *last*
bar(s) of `df` - callers (scheduler pipeline, backtester, tests) are
responsible for slicing the window and for candle-close confirmation
(app.alerts.candle_close) before calling detect() for a "confirmed" result.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from app.models.enums import Direction


@dataclass
class PatternMatch:
    pattern_key: str
    pattern_name: str
    direction: Direction
    strength: float  # 0.0-1.0, detector-internal confidence/quality
    description: str  # human-readable explanation of why it matched


class PatternDetector(ABC):
    key: str
    display_name: str
    direction: Direction
    min_bars: int = 5  # minimum bars of history required to evaluate

    def can_evaluate(self, df: pd.DataFrame) -> bool:
        return len(df) >= self.min_bars

    @abstractmethod
    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        """Evaluate the last bar of `df` as the candidate pattern candle.
        Returns None if the pattern is not present."""
        raise NotImplementedError


# --- Candle geometry helpers -------------------------------------------------

def body(row: pd.Series) -> float:
    return abs(row["close"] - row["open"])


def full_range(row: pd.Series) -> float:
    return max(row["high"] - row["low"], 1e-9)


def upper_shadow(row: pd.Series) -> float:
    return row["high"] - max(row["close"], row["open"])


def lower_shadow(row: pd.Series) -> float:
    return min(row["close"], row["open"]) - row["low"]


def body_pct(row: pd.Series) -> float:
    """Body size as a fraction of the full high-low range."""
    return body(row) / full_range(row)


def is_bullish_candle(row: pd.Series) -> bool:
    return row["close"] > row["open"]


def is_bearish_candle(row: pd.Series) -> bool:
    return row["close"] < row["open"]


def avg_body(df: pd.DataFrame, n: int = 10) -> float:
    window = df.tail(n + 1).iloc[:-1] if len(df) > n else df.iloc[:-1]
    if window.empty:
        return 1e-9
    return max((window["close"] - window["open"]).abs().mean(), 1e-9)


def avg_range(df: pd.DataFrame, n: int = 10) -> float:
    window = df.tail(n + 1).iloc[:-1] if len(df) > n else df.iloc[:-1]
    if window.empty:
        return 1e-9
    return max((window["high"] - window["low"]).mean(), 1e-9)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
