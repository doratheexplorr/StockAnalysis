from tests.fixtures.ohlcv import build_df, candle, flat_padding

from app.patterns.neutral import Doji, InsideBar, OutsideBar, SpinningTop
from app.models.enums import Direction


class TestDoji:
    def test_detects_doji(self):
        df = build_df(flat_padding(10) + [candle(105.0, 106.0, 104.0, 105.02, 100_000)])
        match = Doji().detect(df)
        assert match is not None
        assert match.pattern_key == "doji"

    def test_rejects_large_body(self):
        df = build_df(flat_padding(10) + [candle(105.0, 106.5, 103.5, 106.2, 100_000)])
        assert Doji().detect(df) is None


class TestSpinningTop:
    def test_detects_spinning_top(self):
        df = build_df(flat_padding(10) + [candle(104.5, 106.5, 102.5, 105.0, 100_000)])
        match = SpinningTop().detect(df)
        assert match is not None

    def test_rejects_when_shadows_unbalanced(self):
        df = build_df(flat_padding(10) + [candle(104.5, 104.7, 100.0, 104.9, 100_000)])
        assert SpinningTop().detect(df) is None


class TestInsideBar:
    def test_detects_inside_bar(self):
        rows = flat_padding(9) + [candle(100.0, 108.0, 95.0, 103.0, 100_000), candle(102.0, 104.0, 100.0, 103.0, 90_000)]
        df = build_df(rows)
        match = InsideBar().detect(df)
        assert match is not None

    def test_rejects_when_range_exceeds_prior_bar(self):
        rows = flat_padding(9) + [candle(100.0, 104.0, 99.0, 103.0, 100_000), candle(102.0, 106.0, 98.0, 103.0, 90_000)]
        df = build_df(rows)
        assert InsideBar().detect(df) is None


class TestOutsideBar:
    def test_detects_bullish_outside_bar(self):
        rows = flat_padding(9) + [candle(101.0, 102.0, 100.0, 101.5, 100_000), candle(99.0, 104.0, 98.5, 103.5, 250_000)]
        df = build_df(rows)
        match = OutsideBar().detect(df)
        assert match is not None
        assert match.direction == Direction.BULLISH

    def test_detects_bearish_outside_bar(self):
        rows = flat_padding(9) + [candle(101.0, 102.0, 100.0, 101.5, 100_000), candle(103.0, 104.0, 97.5, 98.0, 250_000)]
        df = build_df(rows)
        match = OutsideBar().detect(df)
        assert match is not None
        assert match.direction == Direction.BEARISH

    def test_rejects_when_not_engulfing_range(self):
        rows = flat_padding(9) + [candle(100.0, 104.0, 99.0, 103.0, 100_000), candle(101.0, 103.5, 100.5, 102.0, 90_000)]
        df = build_df(rows)
        assert OutsideBar().detect(df) is None
