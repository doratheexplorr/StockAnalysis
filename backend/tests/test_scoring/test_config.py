from app.scoring.config import ScoreThresholds, ScoringConfig, classify_score


def test_classify_score_boundaries():
    t = ScoreThresholds()
    assert classify_score(95, t) == "exceptional"
    assert classify_score(90, t) == "exceptional"
    assert classify_score(89.9, t) == "strong"
    assert classify_score(80, t) == "strong"
    assert classify_score(70, t) == "good"
    assert classify_score(60, t) == "watch"
    assert classify_score(59.9, t) == "ignore"


def test_scoring_config_roundtrip_through_dict():
    config = ScoringConfig()
    config.weights.pattern = 40
    config.min_signal_score = 65
    data = config.to_dict()
    restored = ScoringConfig.from_dict(data)
    assert restored.weights.pattern == 40
    assert restored.min_signal_score == 65


def test_default_weights_sum_to_100():
    config = ScoringConfig()
    assert config.weights.total_possible() == 100.0
