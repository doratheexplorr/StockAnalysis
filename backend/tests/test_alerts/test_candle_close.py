import datetime as dt

import pandas as pd

from app.alerts.candle_close import is_bar_closed, split_confirmed_and_forming
from tests.fixtures.ohlcv import build_df, uptrend


def test_intraday_bar_closed_after_full_interval():
    bar_open = pd.Timestamp("2024-01-01 10:00", tz="UTC")
    now = dt.datetime(2024, 1, 1, 10, 15, tzinfo=dt.timezone.utc)
    assert is_bar_closed(bar_open, "15m", now) is True


def test_intraday_bar_not_closed_before_interval_elapses():
    bar_open = pd.Timestamp("2024-01-01 10:00", tz="UTC")
    now = dt.datetime(2024, 1, 1, 10, 10, tzinfo=dt.timezone.utc)
    assert is_bar_closed(bar_open, "15m", now) is False


def test_daily_bar_closed_next_day():
    bar_open = pd.Timestamp("2024-01-01 00:00", tz="UTC")
    now = dt.datetime(2024, 1, 2, 5, 0, tzinfo=dt.timezone.utc)
    assert is_bar_closed(bar_open, "1d", now) is True


def test_daily_bar_not_closed_same_day_before_cutoff():
    bar_open = pd.Timestamp("2024-01-01 00:00", tz="UTC")
    now = dt.datetime(2024, 1, 1, 18, 0, tzinfo=dt.timezone.utc)
    assert is_bar_closed(bar_open, "1d", now) is False


def test_daily_bar_closed_same_day_after_cutoff():
    bar_open = pd.Timestamp("2024-01-01 00:00", tz="UTC")
    now = dt.datetime(2024, 1, 1, 21, 30, tzinfo=dt.timezone.utc)
    assert is_bar_closed(bar_open, "1d", now) is True


def test_split_confirmed_and_forming_separates_last_open_bar():
    df = build_df(uptrend(10, 100.0, step=0.5), step_minutes=60)
    # last bar opened at index[-1]; "now" is only 10 minutes after that open -> still forming
    now = df.index[-1].to_pydatetime() + dt.timedelta(minutes=10)
    confirmed, forming = split_confirmed_and_forming(df, "1h", now=now)
    assert len(confirmed) == len(df) - 1
    assert forming is not None


def test_split_confirmed_and_forming_all_closed():
    df = build_df(uptrend(10, 100.0, step=0.5), step_minutes=60)
    now = df.index[-1].to_pydatetime() + dt.timedelta(hours=2)
    confirmed, forming = split_confirmed_and_forming(df, "1h", now=now)
    assert len(confirmed) == len(df)
    assert forming is None
