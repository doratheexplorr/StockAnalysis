import datetime as dt

from app.alerts.dedup import is_in_cooldown, make_fingerprint, should_emit_signal
from app.models.enums import Direction, SignalStatus
from app.models.signal import Signal


def _make_signal(db, symbol="NVDA", timeframe="15m", pattern_key="bullish_engulfing", candle_ts=None, detected_at=None):
    candle_ts = candle_ts or dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    detected_at = detected_at or dt.datetime.now(dt.timezone.utc)
    fingerprint = make_fingerprint(symbol, timeframe, pattern_key, candle_ts)
    signal = Signal(
        symbol=symbol, timeframe=timeframe, pattern_key=pattern_key, pattern_name="Bullish Engulfing",
        direction=Direction.BULLISH.value, candle_timestamp=candle_ts, detected_at=detected_at,
        quality_score=80, classification="strong", score_breakdown={}, current_price=100, entry_price=101,
        stop_loss=98, target_1=105, target_2=108, target_3=112, risk_per_share=3, reward_to_t1=4,
        reward_to_t2=7, reward_to_t3=11, rr_t1=1.3, rr_t2=2.3, rr_t3=3.6, risk_methodology="test",
        technical_confirmations=[], news_context={}, market_context={}, explanation="test",
        status=SignalStatus.ACTIVE.value, fingerprint=fingerprint,
    )
    db.add(signal)
    db.commit()
    return signal


def test_fingerprint_is_deterministic_and_unique_per_candle():
    ts1 = dt.datetime(2024, 1, 1, 10, 0, tzinfo=dt.timezone.utc)
    ts2 = dt.datetime(2024, 1, 1, 10, 15, tzinfo=dt.timezone.utc)
    fp1a = make_fingerprint("NVDA", "15m", "bullish_engulfing", ts1)
    fp1b = make_fingerprint("NVDA", "15m", "bullish_engulfing", ts1)
    fp2 = make_fingerprint("NVDA", "15m", "bullish_engulfing", ts2)
    assert fp1a == fp1b
    assert fp1a != fp2


def test_duplicate_fingerprint_blocks_re_emission(db):
    ts = dt.datetime(2024, 1, 1, 10, 0, tzinfo=dt.timezone.utc)
    _make_signal(db, candle_ts=ts)
    should_emit, _, reason = should_emit_signal(db, "NVDA", "15m", "bullish_engulfing", ts, cooldown_minutes=240)
    assert should_emit is False
    assert "duplicate" in reason


def test_cooldown_blocks_a_different_candle_within_window(db):
    _make_signal(db, candle_ts=dt.datetime(2024, 1, 1, 10, 0, tzinfo=dt.timezone.utc), detected_at=dt.datetime.now(dt.timezone.utc))
    new_candle = dt.datetime(2024, 1, 1, 10, 15, tzinfo=dt.timezone.utc)
    should_emit, _, reason = should_emit_signal(db, "NVDA", "15m", "bullish_engulfing", new_candle, cooldown_minutes=240)
    assert should_emit is False
    assert "cooldown" in reason


def test_cooldown_zero_disables_cooldown_check(db):
    old_detected = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
    _make_signal(db, candle_ts=dt.datetime(2024, 1, 1, 10, 0, tzinfo=dt.timezone.utc), detected_at=old_detected)
    assert is_in_cooldown(db, "NVDA", "15m", "bullish_engulfing", cooldown_minutes=0) is False


def test_different_symbol_or_pattern_is_not_blocked(db):
    _make_signal(db, symbol="NVDA", candle_ts=dt.datetime(2024, 1, 1, 10, 0, tzinfo=dt.timezone.utc))
    ts2 = dt.datetime(2024, 1, 1, 10, 15, tzinfo=dt.timezone.utc)
    should_emit, _, _ = should_emit_signal(db, "AMD", "15m", "bullish_engulfing", ts2, cooldown_minutes=240)
    assert should_emit is True
    should_emit2, _, _ = should_emit_signal(db, "NVDA", "15m", "hammer", ts2, cooldown_minutes=240)
    assert should_emit2 is True
