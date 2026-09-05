"""
Central pattern registry.

Adding a new candlestick pattern later means: write a `PatternDetector`
subclass in bullish.py/bearish.py/neutral.py (or a new module), append an
instance to the relevant list, and import that list here - nothing else in
the system (scoring, API, watchlist "enabled patterns" config) needs to
change since everything keys off `pattern_key` strings.
"""
from __future__ import annotations

import pandas as pd

from app.patterns.base import PatternDetector, PatternMatch
from app.patterns.bearish import BEARISH_DETECTORS
from app.patterns.bullish import BULLISH_DETECTORS
from app.patterns.neutral import NEUTRAL_DETECTORS

ALL_DETECTORS: list[PatternDetector] = [*BULLISH_DETECTORS, *BEARISH_DETECTORS, *NEUTRAL_DETECTORS]

REGISTRY: dict[str, PatternDetector] = {d.key: d for d in ALL_DETECTORS}


def all_pattern_keys() -> list[str]:
    return list(REGISTRY.keys())


def get_detector(key: str) -> PatternDetector:
    return REGISTRY[key]


def detect_all(df: pd.DataFrame, enabled_keys: list[str] | None = None) -> list[PatternMatch]:
    """Run every enabled detector against the last bar of `df`.

    More than one pattern can legitimately match the same candle (e.g. a
    Doji that is also an Inside Bar) - callers decide how to handle
    multiple matches (the scoring engine scores each independently and, by
    default, keeps only the highest-scoring match per candle to honor the
    "fewer, higher-quality signals" principle).
    """
    keys = enabled_keys if enabled_keys else all_pattern_keys()
    matches: list[PatternMatch] = []
    for key in keys:
        detector = REGISTRY.get(key)
        if detector is None:
            continue
        try:
            match = detector.detect(df)
        except Exception:
            # a single misbehaving detector must never take down the whole
            # detection pass for a symbol (see README "Logging & error handling")
            match = None
        if match is not None:
            matches.append(match)
    return matches
