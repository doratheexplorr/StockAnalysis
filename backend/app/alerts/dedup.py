"""
Signal deduplication (spec section 13) - arguably the most important
correctness property of the whole system: never alert the same setup
repeatedly.

Two layers:
1. Fingerprint uniqueness - `fingerprint = sha256(symbol|timeframe|pattern_key|
   candle_timestamp)` is a DB-unique column on `Signal` (see
   app.models.signal), so the *exact same* pattern on the *exact same*
   closed candle can only ever produce one row, enforced at the database
   level even under concurrent scheduler runs.
2. Cooldown - a configurable minimum gap between alerts for the same
   (symbol, timeframe, pattern_key) even across *different* candles, so a
   choppy market flip-flopping between two patterns every few bars doesn't
   spam notifications.
"""
from __future__ import annotations

import datetime as dt
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.signal import Signal


def make_fingerprint(symbol: str, timeframe: str, pattern_key: str, candle_timestamp: dt.datetime) -> str:
    raw = f"{symbol.upper()}|{timeframe}|{pattern_key}|{candle_timestamp.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fingerprint_exists(db: Session, fingerprint: str) -> bool:
    return db.execute(select(Signal.id).where(Signal.fingerprint == fingerprint)).first() is not None


def is_in_cooldown(
    db: Session,
    symbol: str,
    timeframe: str,
    pattern_key: str,
    cooldown_minutes: int,
    now: dt.datetime | None = None,
) -> bool:
    if cooldown_minutes <= 0:
        return False
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(minutes=cooldown_minutes)
    stmt = (
        select(Signal.id)
        .where(
            Signal.symbol == symbol,
            Signal.timeframe == timeframe,
            Signal.pattern_key == pattern_key,
            Signal.detected_at >= cutoff,
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def should_emit_signal(
    db: Session,
    symbol: str,
    timeframe: str,
    pattern_key: str,
    candle_timestamp: dt.datetime,
    cooldown_minutes: int,
) -> tuple[bool, str, str]:
    """Returns (should_emit, fingerprint, reason_if_not)."""
    fingerprint = make_fingerprint(symbol, timeframe, pattern_key, candle_timestamp)
    if fingerprint_exists(db, fingerprint):
        return False, fingerprint, "duplicate: this exact pattern/candle already produced a signal"
    if is_in_cooldown(db, symbol, timeframe, pattern_key, cooldown_minutes):
        return False, fingerprint, f"cooldown active ({cooldown_minutes}m since last {pattern_key} alert on {symbol}/{timeframe})"
    return True, fingerprint, ""
