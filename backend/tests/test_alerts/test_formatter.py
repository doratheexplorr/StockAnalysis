import datetime as dt

from app.alerts.formatter import AlertData, confidence_from_classification, render_summary, render_text
from app.models.enums import Direction


def _sample_alert(**overrides) -> AlertData:
    defaults = dict(
        symbol="NVDA", timeframe="15m", pattern_name="Bullish Engulfing", direction=Direction.BULLISH,
        quality_score=87, classification="strong", current_price=450.2, entry=451.0, stop_loss=443.5,
        target_1=460.0, target_2=468.0, target_3=478.0, rr_t1=2.4, rr_t2=3.8, rr_t3=5.1,
        confirmations=[{"label": "Bullish trend", "passed": True, "detail": "Bullish trend"},
                        {"label": "Relative volume", "passed": True, "detail": "Relative volume 1.8x"},
                        {"label": "Momentum", "passed": False, "detail": "not aligned"}],
        news_status="supportive", news_headline="NVIDIA announces major AI partnership",
        market_regime="bullish", spy_trend="up", sector="Semiconductors", sector_trend="up",
        explanation="Bullish engulfing formed at support with above-average volume.",
        detected_at=dt.datetime.now(dt.timezone.utc), confidence_label="HIGH",
    )
    defaults.update(overrides)
    return AlertData(**defaults)


def test_render_text_contains_all_required_fields():
    alert = _sample_alert()
    text = render_text(alert)
    for expected in ["NVDA", "15m", "Bullish Engulfing", "87/100", "STRONG", "$451.00", "$443.50",
                      "$460.00", "$468.00", "$478.00", "1:2.4", "1:3.8", "1:5.1", "HIGH",
                      "NOT a guaranteed trading recommendation"]:
        assert expected in text


def test_render_text_only_shows_passed_confirmations():
    alert = _sample_alert()
    text = render_text(alert)
    assert "Bullish trend" in text
    assert "not aligned" not in text  # the failed Momentum confirmation must not be listed as a checkmark


def test_render_summary_is_concise_one_liner():
    alert = _sample_alert()
    summary = render_summary(alert)
    assert "\n" not in summary
    assert "NVDA" in summary and "Bullish Engulfing" in summary


def test_confidence_mapping():
    assert confidence_from_classification("exceptional") == "HIGH"
    assert confidence_from_classification("strong") == "HIGH"
    assert confidence_from_classification("good") == "MEDIUM"
    assert confidence_from_classification("watch") == "LOW"
    assert confidence_from_classification("ignore") == "LOW"


def test_conflicting_news_status_rendered():
    alert = _sample_alert(news_status="conflicting", news_headline="Weak guidance issued")
    text = render_text(alert)
    assert "Conflicting" in text
    assert "Weak guidance issued" in text


def test_unavailable_news_status_rendered_without_headline():
    alert = _sample_alert(news_status="unavailable", news_headline=None)
    text = render_text(alert)
    assert "Unavailable" in text
