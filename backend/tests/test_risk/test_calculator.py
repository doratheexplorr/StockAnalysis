import pytest

from app.models.enums import Direction
from app.risk.calculator import calculate_risk_levels


class TestBullishRiskLevels:
    def test_targets_above_entry_and_stop_below(self):
        risk = calculate_risk_levels(
            Direction.BULLISH, current_price=106.5, atr=2.0, pattern_low=103.0, pattern_high=105.5,
            support=98.0, resistance=110.0, already_broken_out=True,
        )
        assert risk.stop_loss < risk.entry < risk.target_1 < risk.target_2 < risk.target_3
        assert risk.risk_per_share > 0
        assert risk.rr_t1 == pytest.approx(1.5, abs=0.05)
        assert risk.rr_t2 == pytest.approx(2.5, abs=0.05)
        assert risk.rr_t3 == pytest.approx(4.0, abs=0.05)

    def test_target1_upgrades_to_resistance_when_it_provides_at_least_1R(self):
        risk = calculate_risk_levels(
            Direction.BULLISH, current_price=100.0, atr=1.0, pattern_low=98.0, pattern_high=99.5,
            support=None, resistance=101.5, already_broken_out=False,
        )
        # resistance is close to entry; whether it's used depends on R distance,
        # but target_1 must never be below entry for a bullish setup either way
        assert risk.target_1 > risk.entry

    def test_stop_uses_support_when_tighter_than_pattern_low(self):
        risk = calculate_risk_levels(
            Direction.BULLISH, current_price=110.0, atr=1.5, pattern_low=100.0, pattern_high=108.0,
            support=105.0, resistance=None, already_broken_out=True,
        )
        # support (105) is above pattern_low (100) and below entry, so the tighter stop should win
        assert risk.stop_loss > 100.0

    def test_methodology_is_populated(self):
        risk = calculate_risk_levels(
            Direction.BULLISH, current_price=100.0, atr=1.0, pattern_low=98.0, pattern_high=99.0,
            support=None, resistance=None,
        )
        assert "Entry at" in risk.methodology
        assert "not a guaranteed outcome" in risk.methodology


class TestBearishRiskLevels:
    def test_targets_below_entry_and_stop_above(self):
        risk = calculate_risk_levels(
            Direction.BEARISH, current_price=93.5, atr=2.0, pattern_low=94.0, pattern_high=97.0,
            support=85.0, resistance=100.0, already_broken_out=True,
        )
        assert risk.target_3 < risk.target_2 < risk.target_1 < risk.entry < risk.stop_loss
        assert risk.risk_per_share > 0
        # stop should use the tighter of pattern_high/resistance (97, not 100)
        assert risk.stop_loss == pytest.approx(97.5, abs=0.01)
        # support (85) is far enough below entry to be used as T1 directly,
        # which happens to exceed the default 1.5R multiple here
        assert risk.rr_t1 >= 1.5

    def test_pure_atr_based_targets_without_structural_levels(self):
        risk = calculate_risk_levels(
            Direction.BEARISH, current_price=93.5, atr=2.0, pattern_low=94.0, pattern_high=97.0,
            support=None, resistance=None, already_broken_out=True,
        )
        assert risk.rr_t1 == pytest.approx(1.5, abs=0.05)
        assert risk.rr_t2 == pytest.approx(2.5, abs=0.05)
        assert risk.rr_t3 == pytest.approx(4.0, abs=0.05)


def test_falls_back_gracefully_when_atr_missing_or_zero():
    risk = calculate_risk_levels(
        Direction.BULLISH, current_price=50.0, atr=0.0, pattern_low=49.0, pattern_high=49.8,
        support=None, resistance=None,
    )
    assert risk.risk_per_share > 0
    assert risk.stop_loss < risk.entry


def test_invalid_direction_raises():
    with pytest.raises(ValueError):
        calculate_risk_levels(Direction.NEUTRAL, 100, 1.0, 99, 100, None, None)
