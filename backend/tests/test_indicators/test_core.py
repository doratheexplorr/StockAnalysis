import pandas as pd
import pytest

from tests.fixtures.ohlcv import build_df, uptrend

from app.indicators import core


@pytest.fixture()
def trending_df():
    return build_df(uptrend(250, 100.0, step=0.5))


def test_sma_matches_manual_calculation(trending_df):
    result = core.sma(trending_df, 20)
    manual = trending_df["close"].rolling(20).mean()
    pd.testing.assert_series_equal(result, manual, check_names=False)


def test_ema_reacts_faster_than_sma_to_recent_move(trending_df):
    sma20 = core.sma(trending_df, 20).iloc[-1]
    ema9 = core.ema(trending_df, 9).iloc[-1]
    # in a steady uptrend, the faster EMA should sit above the slower SMA
    assert ema9 > sma20


def test_rsi_is_high_in_sustained_uptrend(trending_df):
    rsi = core.rsi(trending_df, 14).iloc[-1]
    assert rsi > 65


def test_rsi_bounded_between_0_and_100(trending_df):
    rsi = core.rsi(trending_df, 14).dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


def test_macd_returns_three_columns(trending_df):
    result = core.macd(trending_df)
    assert set(result.columns) == {"macd", "signal", "hist"}
    assert result["hist"].iloc[-1] == pytest.approx(result["macd"].iloc[-1] - result["signal"].iloc[-1])


def test_atr_is_positive(trending_df):
    atr = core.atr(trending_df, 14).dropna()
    assert (atr > 0).all()


def test_relative_volume_flags_a_volume_spike():
    rows = uptrend(30, 100.0, step=0.2)
    for r in rows:
        r["volume"] = 100_000
    rows[-1]["volume"] = 500_000
    df = build_df(rows)
    rel_vol = core.relative_volume(df, 20).iloc[-1]
    assert rel_vol == pytest.approx(5.0, rel=0.05)


def test_missing_required_column_raises():
    df = pd.DataFrame({"open": [1, 2], "high": [1, 2], "low": [1, 2]})
    with pytest.raises(ValueError):
        core.sma(df, 1)
