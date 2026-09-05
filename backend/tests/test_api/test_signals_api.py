import datetime as dt

from app.models.enums import Direction, SignalStatus
from app.models.signal import Signal


def _insert_signal(db, symbol="NVDA", score=85, status=SignalStatus.ACTIVE.value):
    signal = Signal(
        symbol=symbol, timeframe="15m", pattern_key="bullish_engulfing", pattern_name="Bullish Engulfing",
        direction=Direction.BULLISH.value, candle_timestamp=dt.datetime.now(dt.timezone.utc),
        detected_at=dt.datetime.now(dt.timezone.utc), quality_score=score, classification="strong",
        score_breakdown={}, current_price=100, entry_price=101, stop_loss=98, target_1=105, target_2=108,
        target_3=112, risk_per_share=3, reward_to_t1=4, reward_to_t2=7, reward_to_t3=11, rr_t1=1.3,
        rr_t2=2.3, rr_t3=3.6, risk_methodology="test", technical_confirmations=[], news_context={},
        market_context={}, explanation="test", status=status, fingerprint=f"fp-{symbol}-{score}-{status}",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def test_list_and_get_signal(client, db):
    signal = _insert_signal(db)
    resp = client.get("/api/signals")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp2 = client.get(f"/api/signals/{signal.id}")
    assert resp2.status_code == 200
    assert resp2.json()["symbol"] == "NVDA"
    assert resp2.json()["risk_methodology"] == "test"


def test_filter_by_symbol_and_status(db, client):
    _insert_signal(db, symbol="NVDA")
    _insert_signal(db, symbol="AMD")
    resp = client.get("/api/signals", params={"symbol": "AMD"})
    assert len(resp.json()) == 1
    assert resp.json()[0]["symbol"] == "AMD"


def test_strongest_signals_ordered_by_score(db, client):
    _insert_signal(db, symbol="A", score=72)
    _insert_signal(db, symbol="B", score=95)
    _insert_signal(db, symbol="C", score=81)
    resp = client.get("/api/signals/strongest")
    scores = [s["quality_score"] for s in resp.json()]
    assert scores == sorted(scores, reverse=True)


def test_get_missing_signal_404(client):
    resp = client.get("/api/signals/999999")
    assert resp.status_code == 404
