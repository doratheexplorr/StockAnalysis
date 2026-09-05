from tests.fixtures.ohlcv import build_df, uptrend

from app.indicators.snapshot import compute_indicator_snapshot


def test_snapshot_computes_all_fields():
    df = build_df(uptrend(250, 100.0, step=0.4))
    snap = compute_indicator_snapshot(df)
    d = snap.as_dict()
    for field in ("sma_20", "sma_50", "sma_200", "ema_9", "ema_21", "rsi_14", "atr_14", "relative_volume"):
        assert d[field] is not None
    assert snap.trend_direction == "up"
