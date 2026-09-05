"""Shared enums used across models, schemas and business logic."""
from __future__ import annotations

import enum


class Timeframe(str, enum.Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

    @property
    def minutes(self) -> int:
        return {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }[self.value]

    @property
    def is_intraday(self) -> bool:
        return self != Timeframe.D1


class Direction(str, enum.Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SignalClassification(str, enum.Enum):
    EXCEPTIONAL = "exceptional"  # 90-100
    STRONG = "strong"  # 80-89
    GOOD = "good"  # 70-79
    WATCH = "watch"  # 60-69
    IGNORE = "ignore"  # <60


class SignalStatus(str, enum.Enum):
    ACTIVE = "active"          # newly generated, still being tracked
    HIT_TARGET1 = "hit_target1"
    HIT_TARGET2 = "hit_target2"
    HIT_TARGET3 = "hit_target3"
    HIT_STOP = "hit_stop"
    EXPIRED = "expired"        # no longer tracked (too old / superseded)
    SUPPRESSED = "suppressed"  # scored but suppressed (e.g. CRITICAL conflicting news)


class NotificationChannelType(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"          # not yet implemented, reserved
    DISCORD = "discord"  # not yet implemented, reserved
    SLACK = "slack"      # not yet implemented, reserved
    PUSH = "push"        # not yet implemented, reserved


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # channel disabled / not configured


class NewsSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NewsSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class MarketRegime(str, enum.Enum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"
    HIGH_VOLATILITY = "high_volatility"
