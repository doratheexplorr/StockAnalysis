"""
Candle-close confirmation (spec section 14).

By default, patterns are only evaluated - and can only ever produce an
alertable Signal - on a fully CLOSED candle. The still-forming (latest,
incomplete) bar can optionally be evaluated too (`allow_forming_pattern_detection`
in Settings) purely for UI/preview purposes ("forming pattern"), but such
detections are always marked `is_confirmed=False` and the scheduler
pipeline never lets them reach the scoring/alerting stage.

All timestamps are UTC. Daily-bar close detection uses a fixed UTC cutoff
as a simplification (US market close is 20:00 or 21:00 UTC depending on
DST) - see README "Known limitations" for the precise caveat and how to
tighten this for non-US markets or exact-close-time requirements.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from app.models.enums import Timeframe

_DAILY_CLOSE_CUTOFF_UTC_HOUR = 21  # conservative: covers both EST (UTC-5) and EDT (UTC-4) market closes


def is_bar_closed(bar_open_time: pd.Timestamp, timeframe: str, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now(dt.timezone.utc)
    bar_open_time = pd.Timestamp(bar_open_time).to_pydatetime()
    if bar_open_time.tzinfo is None:
        bar_open_time = bar_open_time.replace(tzinfo=dt.timezone.utc)

    tf = Timeframe(timeframe)
    if tf == Timeframe.D1:
        if bar_open_time.date() < now.date():
            return True
        if bar_open_time.date() == now.date() and now.hour >= _DAILY_CLOSE_CUTOFF_UTC_HOUR:
            return True
        return False

    close_time = bar_open_time + dt.timedelta(minutes=tf.minutes)
    return now >= close_time


def split_confirmed_and_forming(
    df: pd.DataFrame, timeframe: str, now: dt.datetime | None = None
) -> tuple[pd.DataFrame, pd.Series | None]:
    """Returns (confirmed_df, forming_row_or_None).

    `confirmed_df` contains only fully-closed candles, safe to run pattern
    detection + scoring + alerting on. `forming_row` is the still-open
    latest bar (or None if the last row in `df` is already closed) - useful
    only for an explicitly-labelled "forming pattern" preview.
    """
    if df.empty:
        return df, None

    now = now or dt.datetime.now(dt.timezone.utc)
    last_ts = df.index[-1]
    if is_bar_closed(last_ts, timeframe, now):
        return df, None
    return df.iloc[:-1], df.iloc[-1]
