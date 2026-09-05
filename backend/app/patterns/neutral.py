"""Neutral / structural candlestick patterns.

These do not carry an inherent bullish/bearish bias on their own (direction
is context-dependent) - the scoring engine treats them as lower base
weight and leans on trend/S-R/volume confirmation to decide significance,
consistent with the "don't just detect every textbook pattern" requirement.
"""
from __future__ import annotations

import pandas as pd

from app.models.enums import Direction
from app.patterns.base import PatternDetector, PatternMatch, body_pct, clamp, full_range, lower_shadow, upper_shadow


class Doji(PatternDetector):
    key = "doji"
    display_name = "Doji"
    direction = Direction.NEUTRAL
    min_bars = 2

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        cur = df.iloc[-1]
        bp = body_pct(cur)
        if bp > 0.1:
            return None
        strength = clamp(1.0 - bp * 8)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            f"Open and close nearly equal (body is {bp:.1%} of the range), indicating "
            f"indecision between buyers and sellers.",
        )


class SpinningTop(PatternDetector):
    key = "spinning_top"
    display_name = "Spinning Top"
    direction = Direction.NEUTRAL
    min_bars = 2

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        cur = df.iloc[-1]
        bp = body_pct(cur)
        if not (0.1 < bp <= 0.35):
            return None
        upper, lower = upper_shadow(cur), lower_shadow(cur)
        rng = full_range(cur)
        if upper / rng < 0.2 or lower / rng < 0.2:
            return None
        balance = 1 - abs(upper - lower) / rng
        strength = clamp(0.4 + 0.4 * balance)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Small body with upper and lower shadows of comparable size, showing "
            "balanced two-way trading and indecision.",
        )


class InsideBar(PatternDetector):
    key = "inside_bar"
    display_name = "Inside Bar"
    direction = Direction.NEUTRAL
    min_bars = 2

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not (cur["high"] <= prev["high"] and cur["low"] >= prev["low"]):
            return None
        containment = 1 - (full_range(cur) / max(full_range(prev), 1e-9))
        strength = clamp(0.4 + 0.5 * containment)
        return PatternMatch(
            self.key,
            self.display_name,
            self.direction,
            strength,
            "Current bar's range is fully contained within the prior bar's range, "
            "indicating a contraction/pause that often precedes a breakout in either direction.",
        )


class OutsideBar(PatternDetector):
    key = "outside_bar"
    display_name = "Outside Bar"
    direction = Direction.NEUTRAL
    min_bars = 2

    def detect(self, df: pd.DataFrame) -> PatternMatch | None:
        if not self.can_evaluate(df):
            return None
        prev, cur = df.iloc[-2], df.iloc[-1]
        if not (cur["high"] >= prev["high"] and cur["low"] <= prev["low"]):
            return None
        if full_range(cur) <= full_range(prev):
            return None
        expansion = clamp((full_range(cur) / max(full_range(prev), 1e-9) - 1) / 1.5)
        strength = clamp(0.45 + 0.45 * expansion)
        direction = Direction.BULLISH if cur["close"] > cur["open"] else Direction.BEARISH
        return PatternMatch(
            self.key,
            self.display_name,
            direction,
            strength,
            "Current bar's range fully engulfs the prior bar's range (an outside/engulfing "
            f"bar), closing {'up' if direction == Direction.BULLISH else 'down'} - a volatility expansion.",
        )


NEUTRAL_DETECTORS: list[PatternDetector] = [
    Doji(),
    SpinningTop(),
    InsideBar(),
    OutsideBar(),
]
