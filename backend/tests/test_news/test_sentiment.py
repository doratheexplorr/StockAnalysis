from app.models.enums import NewsSentiment, NewsSeverity
from app.news.sentiment import analyze_sentiment, classify_severity


def test_positive_headline_scores_positive():
    score, label = analyze_sentiment("Company announces record profits and strong growth outlook")
    assert label == NewsSentiment.POSITIVE
    assert score > 0


def test_negative_headline_scores_negative():
    score, label = analyze_sentiment("Company reports massive losses and disappointing sales decline")
    assert label == NewsSentiment.NEGATIVE
    assert score < 0


def test_neutral_headline_scores_neutral():
    score, label = analyze_sentiment("Company will report quarterly earnings on Thursday")
    assert label == NewsSentiment.NEUTRAL


def test_critical_severity_keywords():
    assert classify_severity("Company files for bankruptcy protection") == NewsSeverity.CRITICAL
    assert classify_severity("SEC investigation launched into accounting practices") == NewsSeverity.CRITICAL


def test_high_severity_keywords():
    assert classify_severity("Company misses estimates for Q3 earnings") == NewsSeverity.HIGH
    assert classify_severity("Analyst downgrades stock to sell") == NewsSeverity.HIGH


def test_medium_severity_keywords():
    assert classify_severity("Analyst sets new price target for stock") == NewsSeverity.MEDIUM


def test_low_severity_default():
    assert classify_severity("Company to present at investor conference") == NewsSeverity.LOW
