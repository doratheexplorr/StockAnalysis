import datetime as dt

from app.models.enums import Direction, NewsSentiment, NewsSeverity
from app.news.analysis import analyze_news_context
from app.news.base import NewsItem


def _item(sentiment, severity, minutes_ago=20, score=0.6):
    return NewsItem(
        headline="test headline", source="TestWire", url=None,
        published_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago),
        sentiment_score=score if sentiment == NewsSentiment.POSITIVE else -score,
        sentiment_label=sentiment, severity=severity,
    )


def test_no_items_returns_neutral():
    result = analyze_news_context(Direction.BULLISH, [])
    assert result.status == "neutral"
    assert result.adjustment_points == 0.0
    assert result.has_critical_conflict is False


def test_positive_news_supports_bullish_direction():
    result = analyze_news_context(Direction.BULLISH, [_item(NewsSentiment.POSITIVE, NewsSeverity.MEDIUM)])
    assert result.status == "supportive"
    assert result.adjustment_points > 0


def test_negative_news_conflicts_with_bullish_direction():
    result = analyze_news_context(Direction.BULLISH, [_item(NewsSentiment.NEGATIVE, NewsSeverity.HIGH)])
    assert result.status == "conflicting"
    assert result.adjustment_points < 0


def test_negative_news_supports_bearish_direction():
    result = analyze_news_context(Direction.BEARISH, [_item(NewsSentiment.NEGATIVE, NewsSeverity.MEDIUM)])
    assert result.status == "supportive"


def test_critical_conflict_flagged():
    result = analyze_news_context(Direction.BULLISH, [_item(NewsSentiment.NEGATIVE, NewsSeverity.CRITICAL)])
    assert result.has_critical_conflict is True


def test_non_critical_conflict_not_flagged():
    result = analyze_news_context(Direction.BULLISH, [_item(NewsSentiment.NEGATIVE, NewsSeverity.LOW)])
    assert result.has_critical_conflict is False


def test_stale_news_is_deprioritized_but_still_considered():
    old_item = _item(NewsSentiment.POSITIVE, NewsSeverity.LOW, minutes_ago=60 * 24 * 10)
    result = analyze_news_context(Direction.BULLISH, [old_item])
    assert result.status in ("supportive", "neutral")
