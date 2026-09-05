"""Bullish candlestick pattern detectors."""
from __future__ import annotations

import pandas as pd

from app.models.enums import Direction
from app.patterns.base import (
    PatternDetector,
    PatternMatch,
    avg_body,
    body,
    body_pct,
    clamp,
    full_range,
    is_bearish_candle,
    is_bullish_candle,
    lower_shadow,
    upper_shadow,
)
from app.patterns.utils_trend import preceding_trend


class BullishEngulfing(PatternDetector):
    key = "bullish_engulfing"
    display_name = "Bullish Engulfing"
    direction = Direction.BULLISH
    min_bars = 6

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not (is_bearish_candle(prev) and is_bullish_candle(cur)):
            return None
        if not (cur["open"] <= prev["close"] and cur["close"] >= prev["open"]):
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
            f"Bullish candle (body {cur_body:.2f}) fully engulfed the prior bearish "
            f"candle's body ({prev_body:.2f}), signalling a shift from selling to buying pressure.",
        )


class Hammer(PatternDetector):
    key = "hammer"
    display_name = "Hammer"
    direction = Direction.BULLISH
    min_bars = 8

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        cur = df.iloc[-1]
        rng = full_range(cur)
        b = body(cur)
        lower = lower_shadow(cur)
        upper = upper_shadow(cur)

        if preceding_trend(df, lookback=5) != "down":
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
            f"({lower:.2f} vs body {b:.2f}) after a preceding downtrend, suggesting "
            f"buyers rejected lower prices.",
        )


class InvertedHammer(PatternDetector):
    key = "inverted_hammer"
    display_name = "Inverted Hammer"
    direction = Direction.BULLISH
    min_bars = 8

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        cur = df.iloc[-1]
        rng = full_range(cur)
        b = body(cur)
        lower = lower_shadow(cur)
        upper = upper_shadow(cur)

        if preceding_trend(df, lookback=5) != "down":
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
            f"({upper:.2f} vs body {b:.2f}) after a downtrend, suggesting a tentative "
            f"push higher that needs confirmation.",
        )


class MorningStar(PatternDetector):
    key = "morning_star"
    display_name = "Morning Star"
    direction = Direction.BULLISH
    min_bars = 7

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        first, star, third = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        if not is_bearish_candle(first) or body(first) / full_range(first) < 0.5:
            return None
        if body(star) / full_range(star) > 0.35:
            return None
        if not is_bullish_candle(third):
            return None

        first_mid = (first["open"] + first["close"]) / 2
        if third["close"] <= first_mid:
            return None
        gap_down = star[["open", "close"]].max() < first["close"]

        strength = clamp(0.5 + 0.25 * (third["close"] - first_mid) / max(body(first), 1e-9) + (0.15 if gap_down else 0))
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Three-bar reversal: long bearish candle, a small-bodied indecision candle, "
            "then a bullish candle closing back above the midpoint of the first candle's body.",
        )


class PiercingLine(PatternDetector):
    key = "piercing_line"
    display_name = "Piercing Line"
    direction = Direction.BULLISH
    min_bars = 6

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not is_bearish_candle(prev) or not is_bullish_candle(cur):
            return None
        prev_mid = (prev["open"] + prev["close"]) / 2
        if cur["open"] >= prev["close"] and cur["open"] >= prev["low"]:
            # require the open to gap down toward/through prior close for a genuine piercing open
            if cur["open"] > prev["close"]:
                return None
        if not (cur["close"] > prev_mid and cur["close"] < prev["open"]):
            return None

        penetration = (cur["close"] - prev_mid) / max(body(prev), 1e-9)
        strength = clamp(0.45 + 0.45 * penetration)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Bullish candle opened near/below the prior bearish close and closed above "
            "the midpoint of the prior candle's body, piercing into prior selling.",
        )


class ThreeWhiteSoldiers(PatternDetector):
    key = "three_white_soldiers"
    display_name = "Three White Soldiers"
    direction = Direction.BULLISH
    min_bars = 7

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        candles = [c1, c2, c3]
        if not all(is_bullish_candle(c) for c in candles):
            return None
        if not (c1["close"] < c2["close"] < c3["close"]):
            return None
        if not (c1["open"] < c2["open"] < c3["open"]):
            return None
        avg_b = avg_body(df, 10)
        if any(body(c) < avg_b * 0.6 for c in candles):
            return None
        # small upper shadows (each closes near its high)
        if any(upper_shadow(c) > body(c) * 0.5 for c in candles):
            return None

        strength = clamp(0.55 + 0.15 * sum(body(c) / avg_b for c in candles) / 3 - 0.15)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Three consecutive bullish candles with progressively higher closes and "
            "opens, each with strong bodies and small upper shadows - sustained buying pressure.",
        )


class BullishHarami(PatternDetector):
    key = "bullish_harami"
    display_name = "Bullish Harami"
    direction = Direction.BULLISH
    min_bars = 6

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not is_bearish_candle(prev) or not is_bullish_candle(cur):
            return None
        if body(prev) / full_range(prev) < 0.5:
            return None
        if not (cur["open"] > prev["close"] and cur["close"] < prev["open"]):
            return None

        containment = 1 - (body(cur) / max(body(prev), 1e-9))
        strength = clamp(0.4 + 0.5 * containment)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Small bullish candle contained entirely within the prior large bearish "
            "candle's body, signalling that selling momentum is stalling.",
        )


BULLISH_DETECTORS: list[PatternDetector] = [
    BullishEngulfing(),
    Hammer(),
    InvertedHammer(),
    MorningStar(),
    PiercingLine(),
    ThreeWhiteSoldiers(),
    BullishHarami(),
]
