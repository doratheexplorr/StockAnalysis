"""
Sentiment scoring (VADER) and a heuristic news-severity classifier.

VADER is a lexicon/rule-based sentiment analyzer that needs no training
data and works reasonably well on short news headlines - a good fit for a
first version. Severity classification (LOW/MEDIUM/HIGH/CRITICAL, spec
section 28) is a transparent keyword-driven heuristic rather than a
trained classifier: it is intentionally simple and fully configurable
(see SEVERITY_KEYWORDS below) so its behaviour is auditable and can be
tuned without retraining a model.
"""
from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.models.enums import NewsSentiment, NewsSeverity

_analyzer = SentimentIntensityAnalyzer()

# Ordered from most to least severe; first matching category wins.
SEVERITY_KEYWORDS: dict[NewsSeverity, list[str]] = {
    NewsSeverity.CRITICAL: [
        "bankruptcy", "bankrupt", "fraud", "sec investigation", "sec charges",
        "recall", "halted", "trading halt", "delisted", "delisting",
        "ceo resigns", "ceo steps down", "restatement", "going concern",
        "data breach", "hack", "class action", "criminal probe", "indictment",
        "guidance withdrawn", "cuts guidance", "slashes guidance",
    ],
    NewsSeverity.HIGH: [
        "earnings miss", "misses estimates", "earnings beat", "beats estimates",
        "guidance cut", "raises guidance", "lowers guidance", "profit warning",
        "regulatory action", "fda rejects", "fda approves", "antitrust",
        "major contract", "acquisition", "merger", "acquires", "to acquire",
        "layoffs", "restructuring", "downgrade", "upgrade",
    ],
    NewsSeverity.MEDIUM: [
        "price target", "analyst", "initiates coverage", "reiterates",
        "partnership", "launch", "unveils", "expands", "insider selling",
        "insider buying", "buyback", "dividend",
    ],
}


def classify_severity(headline: str, summary: str | None = None) -> NewsSeverity:
    text = f"{headline} {summary or ''}".lower()
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return severity
    return NewsSeverity.LOW


def analyze_sentiment(text: str) -> tuple[float, NewsSentiment]:
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.2:
        label = NewsSentiment.POSITIVE
    elif compound <= -0.2:
        label = NewsSentiment.NEGATIVE
    else:
        label = NewsSentiment.NEUTRAL
    return compound, label
