import datetime as dt

from app.alerts.formatter import AlertData
from app.alerts.notifier import dispatch_signal
from app.models.enums import Direction, NotificationChannelType, SignalStatus
from app.models.signal import Signal


def _persisted_signal(db) -> Signal:
    signal = Signal(
        symbol="NVDA", timeframe="15m", pattern_key="bullish_engulfing", pattern_name="Bullish Engulfing",
        direction=Direction.BULLISH.value, candle_timestamp=dt.datetime.now(dt.timezone.utc),
        detected_at=dt.datetime.now(dt.timezone.utc), quality_score=85, classification="strong",
        score_breakdown={}, current_price=100, entry_price=101, stop_loss=98, target_1=105, target_2=108,
        target_3=112, risk_per_share=3, reward_to_t1=4, reward_to_t2=7, reward_to_t3=11, rr_t1=1.3,
        rr_t2=2.3, rr_t3=3.6, risk_methodology="test", technical_confirmations=[], news_context={},
        market_context={}, explanation="test", status=SignalStatus.ACTIVE.value, fingerprint="fp-test-1",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def _sample_alert() -> AlertData:
    return AlertData(
        symbol="NVDA", timeframe="15m", pattern_name="Bullish Engulfing", direction=Direction.BULLISH,
        quality_score=85, classification="strong", current_price=100, entry=101, stop_loss=98,
        target_1=105, target_2=108, target_3=112, rr_t1=1.3, rr_t2=2.3, rr_t3=3.6, confirmations=[],
        news_status="neutral", news_headline=None, market_regime="bullish", spy_trend="up",
        sector="Semiconductors", sector_trend="up", explanation="test", detected_at=dt.datetime.now(dt.timezone.utc),
        confidence_label="HIGH",
    )


def test_in_app_channel_always_succeeds(db):
    signal = _persisted_signal(db)
    records = dispatch_signal(db, signal, _sample_alert(), [NotificationChannelType.IN_APP.value])
    assert len(records) == 1
    assert records[0].status == "sent"


def test_unconfigured_email_channel_is_skipped_not_failed(db, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    from app.core.config import get_settings
    get_settings.cache_clear()
    signal = _persisted_signal(db)
    records = dispatch_signal(db, signal, _sample_alert(), [NotificationChannelType.EMAIL.value])
    assert records[0].status == "skipped"
    assert records[0].error_message is not None


def test_unknown_channel_is_silently_ignored_not_crashed(db):
    signal = _persisted_signal(db)
    records = dispatch_signal(db, signal, _sample_alert(), ["carrier_pigeon"])
    assert records == []
