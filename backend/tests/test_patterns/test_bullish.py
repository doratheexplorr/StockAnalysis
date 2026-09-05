from tests.fixtures.ohlcv import build_df, candle, downtrend, flat_padding, with_history

from app.patterns.bullish import (
    BullishEngulfing,
    BullishHarami,
    Hammer,
    InvertedHammer,
    MorningStar,
    PiercingLine,
    ThreeWhiteSoldiers,
)


class TestBullishEngulfing:
    def test_detects_valid_pattern(self):
        rows = with_history([candle(105, 105.2, 103.0, 103.2, 150_000), candle(102.8, 106.5, 102.6, 106.2, 300_000)])
        df = build_df(rows)
        match = BullishEngulfing().detect(df)
        assert match is not None
        assert match.pattern_key == "bullish_engulfing"
        assert 0.0 < match.strength <= 1.0

    def test_rejects_when_body_does_not_engulf(self):
        rows = with_history([candle(105, 105.2, 103.0, 103.2, 150_000), candle(104.0, 105.5, 103.8, 105.0, 200_000)])
        df = build_df(rows)
        assert BullishEngulfing().detect(df) is None

    def test_rejects_when_prior_candle_is_bullish(self):
        rows = with_history([candle(103.0, 105.2, 102.8, 105.0, 150_000), candle(105.0, 108.0, 104.9, 107.8, 300_000)])
        df = build_df(rows)
        assert BullishEngulfing().detect(df) is None

    def test_insufficient_history_returns_none(self):
        df = build_df([candle(105, 105.2, 103.0, 103.2), candle(102.8, 106.5, 102.6, 106.2)])
        assert BullishEngulfing().detect(df) is None


class TestHammer:
    def test_detects_hammer_after_downtrend(self):
        rows = flat_padding(8) + downtrend(6, 110) + [candle(103.0, 103.3, 99.5, 103.2, 260_000)]
        df = build_df(rows)
        match = Hammer().detect(df)
        assert match is not None
        assert match.pattern_key == "hammer"

    def test_rejects_without_preceding_downtrend(self):
        rows = flat_padding(14) + [candle(103.0, 103.3, 99.5, 103.2, 260_000)]
        df = build_df(rows)
        assert Hammer().detect(df) is None

    def test_rejects_large_body(self):
        rows = flat_padding(8) + downtrend(6, 110) + [candle(100.0, 103.3, 99.5, 103.2, 260_000)]
        df = build_df(rows)
        assert Hammer().detect(df) is None


class TestInvertedHammer:
    def test_detects_inverted_hammer_after_downtrend(self):
        rows = flat_padding(8) + downtrend(6, 110) + [candle(103.0, 107.0, 102.7, 103.3, 260_000)]
        df = build_df(rows)
        match = InvertedHammer().detect(df)
        assert match is not None
        assert match.pattern_key == "inverted_hammer"

    def test_rejects_without_long_upper_shadow(self):
        rows = flat_padding(8) + downtrend(6, 110) + [candle(103.0, 103.3, 102.7, 103.2, 260_000)]
        df = build_df(rows)
        assert InvertedHammer().detect(df) is None


class TestMorningStar:
    def test_detects_valid_pattern(self):
        rows = with_history([
            candle(110, 110.2, 104.0, 104.5, 150_000),
            candle(104.0, 104.6, 103.4, 104.2, 90_000),
            candle(104.3, 109.0, 104.1, 108.5, 200_000),
        ])
        df = build_df(rows)
        match = MorningStar().detect(df)
        assert match is not None

    def test_rejects_when_third_candle_does_not_close_above_midpoint(self):
        rows = with_history([
            candle(110, 110.2, 104.0, 104.5, 150_000),
            candle(104.0, 104.6, 103.4, 104.2, 90_000),
            candle(104.3, 105.5, 104.1, 105.2, 200_000),
        ])
        df = build_df(rows)
        assert MorningStar().detect(df) is None


class TestPiercingLine:
    def test_detects_valid_pattern(self):
        rows = with_history([candle(110, 110.2, 105.0, 105.5, 150_000), candle(105.0, 109.0, 104.8, 108.5, 200_000)])
        df = build_df(rows)
        match = PiercingLine().detect(df)
        assert match is not None

    def test_rejects_shallow_penetration(self):
        rows = with_history([candle(110, 110.2, 105.0, 105.5, 150_000), candle(105.4, 106.0, 105.2, 105.9, 120_000)])
        df = build_df(rows)
        assert PiercingLine().detect(df) is None


class TestThreeWhiteSoldiers:
    def test_detects_valid_pattern(self):
        rows = with_history([
            candle(100.0, 103.2, 99.8, 103.0, 200_000),
            candle(103.0, 106.2, 102.8, 106.0, 210_000),
            candle(106.0, 109.2, 105.8, 109.0, 220_000),
        ])
        df = build_df(rows)
        match = ThreeWhiteSoldiers().detect(df)
        assert match is not None

    def test_rejects_when_closes_not_progressively_higher(self):
        rows = with_history([
            candle(100.0, 103.2, 99.8, 103.0, 200_000),
            candle(103.0, 106.2, 102.8, 104.0, 210_000),
            candle(104.0, 105.2, 103.8, 105.0, 220_000),
        ])
        df = build_df(rows)
        assert ThreeWhiteSoldiers().detect(df) is None


class TestBullishHarami:
    def test_detects_valid_pattern(self):
        rows = with_history([candle(108.0, 108.2, 103.0, 103.5, 200_000), candle(104.5, 106.0, 104.3, 105.5, 90_000)])
        df = build_df(rows)
        match = BullishHarami().detect(df)
        assert match is not None

    def test_rejects_when_not_contained(self):
        rows = with_history([candle(108.0, 108.2, 103.0, 103.5, 200_000), candle(103.0, 109.0, 102.5, 108.5, 200_000)])
        df = build_df(rows)
        assert BullishHarami().detect(df) is None
