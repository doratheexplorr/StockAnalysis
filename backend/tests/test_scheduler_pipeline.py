"""
End-to-end integration tests for app.scheduler.pipeline.process_symbol_timeframe,
wiring every layer together (market data -> patterns -> indicators -> news ->
regime -> scoring -> risk -> dedup -> notification) against fake providers so
no live network access is required.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from app.market_data.base import MarketDataProvider, Quote
from app.models.enums import NewsSentiment, NewsSeverity
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.news.base import NewsItem, NewsProvider
from app.scheduler.pipeline import process_symbol_timeframe
from tests.fixtures.ohlcv import build_df, candle, flat_padding


def _engineered_bullish_engulfing_df(n_pad: int = 250, tf_minutes: int = 60) -> pd.DataFrame:
    rows = flat_padding(n_pad, base=100.0, step=0.3, volume=200_000)
    last = rows[-1]
    prev_bear_open = last["close"]
    prev_bear_close = prev_bear_open - 1.5
    rows[-1] = candle(prev_bear_open, prev_bear_open + 0.2, prev_bear_close - 0.3, prev_bear_close, 180_000)
    engulf_open = prev_bear_close - 0.2
    engulf_close = prev_bear_open + 2.5
    rows.append(candle(engulf_open, engulf_close + 0.3, engulf_open - 0.2, engulf_close, 500_000))
    return build_df(rows, step_minutes=tf_minutes)


class FakeProvider(MarketDataProvider):
    name = "fake"

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.spy = _engineered_bullish_engulfing_df(250, 1440)
        self.vix = build_df([candle(15, 16, 14, 15.5, 0)] * 10, step_minutes=1440)

    def get_ohlcv(self, symbol, timeframe, lookback_bars=300):
        if symbol == "SPY":
            return self.spy.tail(lookback_bars)
        if symbol == "^VIX":
            return self.vix.tail(lookback_bars)
        return self.df.tail(lookback_bars)

    def get_latest_price(self, symbol):
        return Quote(symbol=symbol, price=float(self.df["close"].iloc[-1]), as_of=pd.Timestamp.now(tz="UTC"))


class FakeNews(NewsProvider):
    name = "fake"

    def __init__(self, sentiment=NewsSentiment.POSITIVE, severity=NewsSeverity.MEDIUM, score=0.6):
        self.sentiment, self.severity, self.score = sentiment, severity, score

    def get_company_news(self, symbol, company_name=None, lookback_hours=168):
        return [
            NewsItem(
                headline="Company announces major partnership" if self.sentiment == NewsSentiment.POSITIVE else "Company issues weak guidance",
                source="TestWire", url="https://example.com", published_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20),
                sentiment_score=self.score, sentiment_label=self.sentiment, severity=self.severity,
            )
        ]

    def get_market_news(self, lookback_hours=48):
        return []

    def get_sector_news(self, sector, lookback_hours=72):
        return []


@pytest.fixture()
def watchlist_item(db):
    user = User(email="test@example.com", display_name="Test")
    db.add(user)
    db.flush()
    wl = Watchlist(user_id=user.id, name="Test")
    db.add(wl)
    db.flush()
    item = WatchlistItem(watchlist_id=wl.id, symbol="NVDA", timeframes=["1h"])
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


NOW = dt.datetime(2024, 6, 1, 12, 0, tzinfo=dt.timezone.utc)


def test_pipeline_emits_signal_for_a_clean_bullish_setup(db, watchlist_item):
    df = _engineered_bullish_engulfing_df()
    now = df.index[-1].to_pydatetime() + dt.timedelta(hours=1)
    provider = FakeProvider(df)
    news = FakeNews(sentiment=NewsSentiment.POSITIVE)

    result = process_symbol_timeframe(db, watchlist_item, "1h", provider, news, now=now)

    assert result.reason == "alert_emitted"
    assert result.signal is not None
    assert result.signal.direction == "bullish"
    assert result.signal.status == "active"
    assert result.signal.quality_score > 0


def test_pipeline_dedupes_on_second_run_same_candle(db, watchlist_item):
    df = _engineered_bullish_engulfing_df()
    now = df.index[-1].to_pydatetime() + dt.timedelta(hours=1)
    provider = FakeProvider(df)
    news = FakeNews(sentiment=NewsSentiment.POSITIVE)

    first = process_symbol_timeframe(db, watchlist_item, "1h", provider, news, now=now)
    assert first.reason == "alert_emitted"

    second = process_symbol_timeframe(db, watchlist_item, "1h", provider, news, now=now)
    assert second.signal is None
    assert "duplicate" in second.reason


def test_pipeline_suppresses_on_critical_conflicting_news(db, watchlist_item):
    df = _engineered_bullish_engulfing_df()
    now = df.index[-1].to_pydatetime() + dt.timedelta(hours=1)
    provider = FakeProvider(df)
    news = FakeNews(sentiment=NewsSentiment.NEGATIVE, severity=NewsSeverity.CRITICAL, score=-0.8)

    result = process_symbol_timeframe(db, watchlist_item, "1h", provider, news, now=now)
    assert result.signal is not None
    assert result.signal.status == "suppressed"
    assert "suppressed" in result.reason


def test_pipeline_returns_none_when_no_pattern_detected(db, watchlist_item):
    df = build_df(flat_padding(250, base=100.0, step=0.0, volume=100_000))
    now = df.index[-1].to_pydatetime() + dt.timedelta(hours=1)
    provider = FakeProvider(df)
    news = FakeNews()

    result = process_symbol_timeframe(db, watchlist_item, "1h", provider, news, now=now)
    assert result.signal is None


def test_pipeline_respects_per_item_min_score_override(db, watchlist_item):
    watchlist_item.min_score_override = 99  # impossibly high bar
    db.commit()
    df = _engineered_bullish_engulfing_df()
    now = df.index[-1].to_pydatetime() + dt.timedelta(hours=1)
    provider = FakeProvider(df)
    news = FakeNews(sentiment=NewsSentiment.POSITIVE)

    result = process_symbol_timeframe(db, watchlist_item, "1h", provider, news, now=now)
    assert result.signal is None
    assert "score_below_threshold" in result.reason
