from tests.fixtures.ohlcv import build_df, downtrend, flat_padding, uptrend

from app.indicators import structure


def test_trend_direction_up_in_uptrend():
    df = build_df(uptrend(120, 100.0, step=0.5))
    result = structure.trend_direction(df)
    assert result.direction == "up"


def test_trend_direction_down_in_downtrend():
    df = build_df(downtrend(120, 200.0, step=0.5))
    result = structure.trend_direction(df)
    assert result.direction == "down"


def test_trend_direction_sideways_with_insufficient_history():
    df = build_df(flat_padding(10))
    result = structure.trend_direction(df, fast_period=20, slow_period=50)
    assert result.direction == "sideways"


def test_breakout_detected_above_prior_range_with_volume():
    rows = flat_padding(25, base=100.0, step=0.05)
    # push a strong breakout candle with a volume spike
    last = rows[-1]
    rows[-1] = {"open": last["close"], "high": last["close"] + 5, "low": last["close"] - 0.1, "close": last["close"] + 4.8, "volume": 800_000}
    df = build_df(rows)
    assert structure.breakout_breakdown(df) == "breakout"


def test_no_breakout_without_volume_confirmation():
    rows = flat_padding(25, base=100.0, step=0.05)
    last = rows[-1]
    rows[-1] = {"open": last["close"], "high": last["close"] + 5, "low": last["close"] - 0.1, "close": last["close"] + 4.8, "volume": 100_000}
    df = build_df(rows)
    assert structure.breakout_breakdown(df, confirm_with_volume=True) == "none"


def test_support_resistance_returns_none_with_insufficient_history():
    df = build_df(flat_padding(5))
    support, resistance = structure.support_resistance(df)
    assert support is None
    assert resistance is None
