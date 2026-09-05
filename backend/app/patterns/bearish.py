"""Bearish candlestick pattern detectors (mirror image of app.patterns.bullish)."""
from __future__ import annotations

import pandas as pd

from app.models.enums import Direction
from app.patterns.base import (
    PatternDetector,
    PatternMatch,
    avg_body,
    body,
    clamp,
    full_range,
    is_bearish_candle,
    is_bullish_candle,
    lower_shadow,
    upper_shadow,
)
from app.patterns.utils_trend import preceding_trend


class BearishEngulfing(PatternDetector):
    key = "bearish_engulfing"
    display_name = "Bearish Engulfing"
    direction = Direction.BEARISH
    min_bars = 6

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not (is_bullish_candle(prev) and is_bearish_candle(cur)):
            return None
        if not (cur["open"] >= prev["close"] and cur["close"] <= prev["open"]):
            return None
        prev_body, cur_body = body(prev), body(cur)
        if cur_body <= prev_body:
            return None

        size_ratio = clamp(cur_body / max(prev_body, 1e-9) / 2.0)
        strength = clamp(0.5 + 0.5 * size_ratio)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            f"Bearish candle (body {cur_body:.2f}) fully engulfed the prior bullish "
            f"candle's body ({prev_body:.2f}), signalling a shift from buying to selling pressure.",
        )


class ShootingStar(PatternDetector):
    key = "shooting_star"
    display_name = "Shooting Star"
    direction = Direction.BEARISH
    min_bars = 8

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        cur = df.iloc[-1]
        rng = full_range(cur)
        b = body(cur)
        lower = lower_shadow(cur)
        upper = upper_shadow(cur)

        if preceding_trend(df, lookback=5) != "up":
            return None
        if b / rng > 0.35:
            return None
        if upper < 2 * max(b, rng * 0.05):
            return None
        if lower > b * 1.0:
            return None

        strength = clamp(0.4 + 0.6 * clamp(upper / rng))
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            f"Small body near the bottom of the range with a long upper shadow "
            f"({upper:.2f} vs body {b:.2f}) after a preceding uptrend, suggesting "
            f"buyers were rejected at higher prices.",
        )


class HangingMan(PatternDetector):
    key = "hanging_man"
    display_name = "Hanging Man"
    direction = Direction.BEARISH
    min_bars = 8

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        cur = df.iloc[-1]
        rng = full_range(cur)
        b = body(cur)
        lower = lower_shadow(cur)
        upper = upper_shadow(cur)

        if preceding_trend(df, lookback=5) != "up":
            return None
        if b / rng > 0.35:
            return None
        if lower < 2 * max(b, rng * 0.05):
            return None
        if upper > b * 1.0:
            return None

        strength = clamp(0.4 + 0.6 * clamp(lower / rng))
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            f"Small body near the top of the range with a long lower shadow "
            f"({lower:.2f} vs body {b:.2f}) after an uptrend - a warning that selling "
            f"pressure emerged intraday even though the close held up.",
        )


class EveningStar(PatternDetector):
    key = "evening_star"
    display_name = "Evening Star"
    direction = Direction.BEARISH
    min_bars = 7

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        first, star, third = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        if not is_bullish_candle(first) or body(first) / full_range(first) < 0.5:
            return None
        if body(star) / full_range(star) > 0.35:
            return None
        if not is_bearish_candle(third):
            return None

        first_mid = (first["open"] + first["close"]) / 2
        if third["close"] >= first_mid:
            return None
        gap_up = star[["open", "close"]].min() > first["close"]

        strength = clamp(0.5 + 0.25 * (first_mid - third["close"]) / max(body(first), 1e-9) + (0.15 if gap_up else 0))
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Three-bar reversal: long bullish candle, a small-bodied indecision candle, "
            "then a bearish candle closing back below the midpoint of the first candle's body.",
        )


class DarkCloudCover(PatternDetector):
    key = "dark_cloud_cover"
    display_name = "Dark Cloud Cover"
    direction = Direction.BEARISH
    min_bars = 6

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not is_bullish_candle(prev) or not is_bearish_candle(cur):
            return None
        prev_mid = (prev["open"] + prev["close"]) / 2
        if cur["open"] < prev["close"]:
            return None
        if not (cur["close"] < prev_mid and cur["close"] > prev["open"]):
            return None

        penetration = (prev_mid - cur["close"]) / max(body(prev), 1e-9)
        strength = clamp(0.45 + 0.45 * penetration)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Bearish candle opened near/above the prior bullish close and closed below "
            "the midpoint of the prior candle's body, covering prior buying.",
        )


class ThreeBlackCrows(PatternDetector):
    key = "three_black_crows"
    display_name = "Three Black Crows"
    direction = Direction.BEARISH
    min_bars = 7

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        candles = [c1, c2, c3]
        if not all(is_bearish_candle(c) for c in candles):
            return None
        if not (c1["close"] > c2["close"] > c3["close"]):
            return None
        if not (c1["open"] > c2["open"] > c3["open"]):
            return None
        avg_b = avg_body(df, 10)
        if any(body(c) < avg_b * 0.6 for c in candles):
            return None
        if any(lower_shadow(c) > body(c) * 0.5 for c in candles):
            return None

        strength = clamp(0.55 + 0.15 * sum(body(c) / avg_b for c in candles) / 3 - 0.15)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Three consecutive bearish candles with progressively lower closes and "
            "opens, each with strong bodies and small lower shadows - sustained selling pressure.",
        )


class BearishHarami(PatternDetector):
    key = "bearish_harami"
    display_name = "Bearish Harami"
    direction = Direction.BEARISH
    min_bars = 6

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not is_bullish_candle(prev) or not is_bearish_candle(cur):
            return None
        if body(prev) / full_range(prev) < 0.5:
            return None
        if not (cur["open"] < prev["close"] and cur["close"] > prev["open"]):
            return None

        containment = 1 - (body(cur) / max(body(prev), 1e-9))
        strength = clamp(0.4 + 0.5 * containment)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Small bearish candle contained entirely within the prior large bullish "
            "candle's body, signalling that buying momentum is stalling.",
        )


BEARISH_DETECTORS: list[PatternDetector] = [
    BearishEngulfing(),
    ShootingStar(),
    HangingMan(),
    EveningStar(),
    DarkCloudCover(),
    ThreeBlackCrows(),
    BearishHarami(),
]
