import pytest

from app.indicators.snapshot import IndicatorValues
from app.market_context.regime import RegimeContext
from app.models.enums import Direction, MarketRegime
from app.news.analysis import NewsContextResult
from app.patterns.base import PatternMatch
from app.risk.calculator import calculate_risk_levels
from app.scoring.config import ScoringConfig
from app.scoring.engine import score_setup


def _strong_bullish_indicators() -> IndicatorValues:
    return IndicatorValues(
        sma_20=100, sma_50=95, sma_200=90, ema_9=101, ema_21=99, rsi_14=58,
        macd=1.2, macd_signal=0.8, macd_hist=0.4, atr_14=2.0, volume=500_000,
        avg_volume_20=300_000, relative_volume=1.8, recent_high_20=108, recent_low_20=94,
        support_level=98.0, resistance_level=110.0, trend_direction="up",
        structure="higher_highs_higher_lows", breakout="breakout", consolidation=False,
    )


def _supportive_news(max_points: float) -> NewsContextResult:
    return NewsContextResult(status="supportive", adjustment_points=max_points * 0.8, has_critical_conflict=False, reason="Positive headline")


def _bullish_regime() -> RegimeContext:
    return RegimeContext(regime=MarketRegime.BULLISH, spy_trend="up", vix_level=15.0, vix_bucket="normal", supportive_for=[Direction.BULLISH], description="bullish tape")


@pytest.fixture()
def config() -> ScoringConfig:
    return ScoringConfig()


def test_fully_aligned_bullish_setup_scores_strong_or_better(config):
    pattern = PatternMatch("bullish_engulfing", "Bullish Engulfing", Direction.BULLISH, 0.9, "desc")
    risk = calculate_risk_levels(Direction.BULLISH, 106.5, 2.0, 103.0, 105.5, 98.0, 110.0, already_broken_out=True)
    result = score_setup(
        pattern=pattern, direction=Direction.BULLISH, current_price=106.5, indicators=_strong_bullish_indicators(),
        risk=risk, news=_supportive_news(config.weights.news), regime=_bullish_regime(), sector="Semiconductors",
        sector_trend_value="up", config=config,
    )
    assert result.total_score >= 80
    assert result.classification in ("strong", "exceptional")
    assert result.suppressed is False


def test_weak_setup_with_no_confirmations_scores_low(config):
    pattern = PatternMatch("doji", "Doji", Direction.BULLISH, 0.3, "weak")
    weak_indicators = IndicatorValues(
        sma_20=100, sma_50=105, sma_200=110, ema_9=99, ema_21=101, rsi_14=45,
        macd=-0.2, macd_signal=0.1, macd_hist=-0.3, atr_14=2.0, volume=100_000,
        avg_volume_20=300_000, relative_volume=0.4, recent_high_20=108, recent_low_20=94,
        support_level=None, resistance_level=None, trend_direction="down",
        structure="lower_highs_lower_lows", breakout="none", consolidation=False,
    )
    risk = calculate_risk_levels(Direction.BULLISH, 100.0, 2.0, 98.0, 99.5, None, None, already_broken_out=False)
    neutral_news = NewsContextResult(status="neutral", adjustment_points=0.0, has_critical_conflict=False, reason="none")
    neutral_regime = RegimeContext(regime=MarketRegime.NEUTRAL, spy_trend="sideways", vix_level=18, vix_bucket="normal", supportive_for=[Direction.BULLISH, Direction.BEARISH], description="neutral")
    result = score_setup(
        pattern=pattern, direction=Direction.BULLISH, current_price=100.0, indicators=weak_indicators,
        risk=risk, news=neutral_news, regime=neutral_regime, sector="Diversified", sector_trend_value="unknown", config=config,
    )
    assert result.classification in ("ignore", "watch")


def test_critical_conflicting_news_suppresses_regardless_of_score(config):
    pattern = PatternMatch("bullish_engulfing", "Bullish Engulfing", Direction.BULLISH, 0.9, "desc")
    risk = calculate_risk_levels(Direction.BULLISH, 106.5, 2.0, 103.0, 105.5, 98.0, 110.0, already_broken_out=True)
    bad_news = NewsContextResult(status="conflicting", adjustment_points=-config.weights.news, has_critical_conflict=True, reason="Bad guidance")
    result = score_setup(
        pattern=pattern, direction=Direction.BULLISH, current_price=106.5, indicators=_strong_bullish_indicators(),
        risk=risk, news=bad_news, regime=_bullish_regime(), sector="Semiconductors", sector_trend_value="up", config=config,
    )
    assert result.suppressed is True
    assert result.suppression_reason is not None


def test_suppression_can_be_disabled_via_risk_policy(config):
    config.risk_policy.suppress_on_critical_conflict = False
    pattern = PatternMatch("bullish_engulfing", "Bullish Engulfing", Direction.BULLISH, 0.9, "desc")
    risk = calculate_risk_levels(Direction.BULLISH, 106.5, 2.0, 103.0, 105.5, 98.0, 110.0, already_broken_out=True)
    bad_news = NewsContextResult(status="conflicting", adjustment_points=-config.weights.news, has_critical_conflict=True, reason="Bad guidance")
    result = score_setup(
        pattern=pattern, direction=Direction.BULLISH, current_price=106.5, indicators=_strong_bullish_indicators(),
        risk=risk, news=bad_news, regime=_bullish_regime(), sector="Semiconductors", sector_trend_value="up", config=config,
    )
    assert result.suppressed is False


def test_weights_drive_component_scale(config):
    config.weights.pattern = 50.0  # double the default
    pattern = PatternMatch("bullish_engulfing", "Bullish Engulfing", Direction.BULLISH, 1.0, "desc")
    risk = calculate_risk_levels(Direction.BULLISH, 106.5, 2.0, 103.0, 105.5, 98.0, 110.0, already_broken_out=True)
    result = score_setup(
        pattern=pattern, direction=Direction.BULLISH, current_price=106.5, indicators=_strong_bullish_indicators(),
        risk=risk, news=_supportive_news(config.weights.news), regime=_bullish_regime(), sector="Semiconductors",
        sector_trend_value="up", config=config,
    )
    assert result.breakdown["pattern"] == pytest.approx(50.0, abs=0.01)
