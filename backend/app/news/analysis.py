"""
Turns raw news items into a single "does this news agree with the technical
setup" verdict (spec sections 27/29): SUPPORTIVE / CONFLICTING / NEUTRAL /
UNAVAILABLE, plus a signed point adjustment consumed by the scoring engine
and a CRITICAL-severity flag that can suppress a signal outright.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import Direction, NewsSentiment, NewsSeverity
from app.news.base import NewsItem


@dataclass
class NewsContextResult:
    status: str  # "supportive" | "conflicting" | "neutral" | "unavailable"
    adjustment_points: float  # signed, added to the news component of the score
    has_critical_conflict: bool
    headline_items: list[dict] = field(default_factory=list)  # for display/storage
    reason: str = ""


_SEVERITY_WEIGHT = {
    NewsSeverity.LOW: 0.3,
    NewsSeverity.MEDIUM: 0.6,
    NewsSeverity.HIGH: 1.0,
    NewsSeverity.CRITICAL: 1.6,
}

# a news item older than this contributes negligibly to the current signal
_MAX_RELEVANT_AGE_HOURS = 72


def _item_to_dict(item: NewsItem) -> dict:
    return {
        "headline": item.headline,
        "source": item.source,
        "url": item.url,
        "published_at": item.published_at.isoformat(),
        "age_hours": round(item.age_hours, 1),
        "recency": item.recency_bucket,
        "sentiment": item.sentiment_label.value,
        "sentiment_score": round(item.sentiment_score, 3),
        "severity": item.severity.value,
    }


def analyze_news_context(
    direction: Direction, items: list[NewsItem], max_points: float = 10.0
) -> NewsContextResult:
    if not items:
        return NewsContextResult(
            status="neutral",
            adjustment_points=0.0,
            has_critical_conflict=False,
            reason="No significant recent company-specific news identified.",
        )

    # prefer the most recent, most severe items; ignore stale background noise
    relevant = [i for i in items if i.age_hours <= _MAX_RELEVANT_AGE_HOURS]
    relevant = relevant or items[:3]
    relevant = sorted(relevant, key=lambda i: (_SEVERITY_WEIGHT[i.severity], -i.age_hours), reverse=True)[:5]

    weighted_sentiment = 0.0
    total_weight = 0.0
    has_critical_conflict = False
    for item in relevant:
        weight = _SEVERITY_WEIGHT[item.severity] / max(1.0, item.age_hours / 24)
        weighted_sentiment += item.sentiment_score * weight
        total_weight += weight
        directional_conflict = (
            (direction == Direction.BULLISH and item.sentiment_label == NewsSentiment.NEGATIVE)
            or (direction == Direction.BEARISH and item.sentiment_label == NewsSentiment.POSITIVE)
        )
        if item.severity == NewsSeverity.CRITICAL and directional_conflict:
            has_critical_conflict = True

    avg_sentiment = weighted_sentiment / total_weight if total_weight else 0.0

    # align sentiment sign with the setup's direction: for a bearish setup,
    # negative news is *agreement*, so flip the sign before scoring
    directional_alignment = avg_sentiment if direction == Direction.BULLISH else -avg_sentiment

    if directional_alignment >= 0.15:
        status = "supportive"
    elif directional_alignment <= -0.15:
        status = "conflicting"
    else:
        status = "neutral"

    adjustment_points = max(-max_points, min(max_points, directional_alignment * max_points))

    top = relevant[0]
    reason = f"{top.headline} ({top.recency_bucket.replace('_', ' ')}, {top.source})"

    return NewsContextResult(
        status=status,
        adjustment_points=round(adjustment_points, 2),
        has_critical_conflict=has_critical_conflict,
        headline_items=[_item_to_dict(i) for i in relevant],
        reason=reason,
    )
