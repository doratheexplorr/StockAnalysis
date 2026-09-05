from tests.fixtures.ohlcv import build_df, candle, flat_padding, uptrend, with_history

from app.patterns.bearish import (
    BearishEngulfing,
    BearishHarami,
    DarkCloudCover,
    EveningStar,
    HangingMan,
    ShootingStar,
    ThreeBlackCrows,
)


class TestBearishEngulfing:
    def test_detects_valid_pattern(self):
        rows = with_history([candle(103.0, 106.2, 102.8, 106.0, 150_000), candle(106.2, 106.4, 102.5, 102.8, 300_000)])
        df = build_df(rows)
        match = BearishEngulfing().detect(df)
        assert match is not None
        assert match.pattern_key == "bearish_engulfing"

    def test_rejects_when_body_does_not_engulf(self):
        rows = with_history([candle(103.0, 106.2, 102.8, 106.0, 150_000), candle(105.0, 105.5, 104.0, 104.5, 200_000)])
        df = build_df(rows)
        assert BearishEngulfing().detect(df) is None


class TestShootingStar:
    def test_detects_after_uptrend(self):
        rows = flat_padding(8) + uptrend(6, 90) + [candle(103.0, 107.0, 102.85, 103.2, 260_000)]
        df = build_df(rows)
        match = ShootingStar().detect(df)
        assert match is not None

    def test_rejects_without_preceding_uptrend(self):
        rows = flat_padding(14) + [candle(103.0, 107.0, 102.85, 103.2, 260_000)]
        df = build_df(rows)
        assert ShootingStar().detect(df) is None


class TestHangingMan:
    def test_detects_after_uptrend(self):
        rows = flat_padding(8) + uptrend(6, 90) + [candle(103.0, 103.3, 99.5, 103.2, 260_000)]
        df = build_df(rows)
        match = HangingMan().detect(df)
        assert match is not None

    def test_rejects_without_preceding_uptrend(self):
        rows = flat_padding(14) + [candle(103.0, 103.3, 99.5, 103.2, 260_000)]
        df = build_df(rows)
        assert HangingMan().detect(df) is None


class TestEveningStar:
    def test_detects_valid_pattern(self):
        rows = with_history([
            candle(100, 109.0, 99.8, 108.5, 200_000),
            candle(108.5, 109.2, 107.8, 108.7, 90_000),
            candle(108.5, 108.7, 103.0, 103.5, 220_000),
        ])
        df = build_df(rows)
        match = EveningStar().detect(df)
        assert match is not None

    def test_rejects_when_third_candle_does_not_close_below_midpoint(self):
        rows = with_history([
            candle(100, 109.0, 99.8, 108.5, 200_000),
            candle(108.5, 109.2, 107.8, 108.7, 90_000),
            candle(108.5, 108.7, 106.5, 107.0, 220_000),
        ])
        df = build_df(rows)
        assert EveningStar().detect(df) is None


class TestDarkCloudCover:
    def test_detects_valid_pattern(self):
        rows = with_history([candle(100.0, 105.5, 99.8, 105.0, 150_000), candle(105.5, 105.8, 101.5, 102.0, 200_000)])
        df = build_df(rows)
        match = DarkCloudCover().detect(df)
        assert match is not None

    def test_rejects_shallow_penetration(self):
        rows = with_history([candle(100.0, 105.5, 99.8, 105.0, 150_000), candle(105.0, 105.4, 104.5, 104.6, 120_000)])
        df = build_df(rows)
        assert DarkCloudCover().detect(df) is None


class TestThreeBlackCrows:
    def test_detects_valid_pattern(self):
        rows = with_history([
            candle(109.0, 109.2, 105.8, 106.0, 200_000),
            candle(106.0, 106.2, 102.8, 103.0, 210_000),
            candle(103.0, 103.2, 99.8, 100.0, 220_000),
        ])
        df = build_df(rows)
        match = ThreeBlackCrows().detect(df)
        assert match is not None

    def test_rejects_when_closes_not_progressively_lower(self):
        rows = with_history([
            candle(109.0, 109.2, 105.8, 106.0, 200_000),
            candle(106.0, 106.2, 104.8, 105.0, 210_000),
            candle(105.0, 105.2, 104.0, 104.5, 220_000),
        ])
        df = build_df(rows)
        assert ThreeBlackCrows().detect(df) is None


class TestBearishHarami:
    def test_detects_valid_pattern(self):
        rows = with_history([candle(103.0, 108.5, 102.8, 108.0, 200_000), candle(107.0, 107.3, 105.5, 105.8, 90_000)])
        df = build_df(rows)
        match = BearishHarami().detect(df)
        assert match is not None

    def test_rejects_when_not_contained(self):
        rows = with_history([candle(103.0, 108.5, 102.8, 108.0, 200_000), candle(108.0, 109.0, 101.5, 102.0, 200_000)])
        df = build_df(rows)
        assert BearishHarami().detect(df) is None
