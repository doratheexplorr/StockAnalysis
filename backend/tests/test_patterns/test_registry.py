from tests.fixtures.ohlcv import build_df, candle, downtrend, flat_padding

from app.patterns.registry import ALL_DETECTORS, all_pattern_keys, detect_all, get_detector


def test_registry_has_18_unique_patterns():
    keys = all_pattern_keys()
    assert len(keys) == len(set(keys)) == 18


def test_get_detector_roundtrip():
    for key in all_pattern_keys():
        detector = get_detector(key)
        assert detector.key == key


def test_detect_all_respects_enabled_keys_filter():
    rows = flat_padding(8) + downtrend(6, 110) + [candle(103.0, 103.3, 99.5, 103.2, 260_000)]
    df = build_df(rows)
    matches_all = detect_all(df)
    matches_filtered = detect_all(df, enabled_keys=["doji"])
    assert any(m.pattern_key == "hammer" for m in matches_all)
    assert all(m.pattern_key == "doji" for m in matches_filtered)


def test_a_broken_detector_does_not_crash_detect_all(monkeypatch):
    df = build_df(flat_padding(20))

    def boom(self, df):
        raise RuntimeError("simulated detector bug")

    monkeypatch.setattr(ALL_DETECTORS[0].__class__, "detect", boom)
    # should not raise, and should not include a match from the broken detector
    matches = detect_all(df)
    assert isinstance(matches, list)
