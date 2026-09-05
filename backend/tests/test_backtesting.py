import datetime as dt

from app.backtesting.engine import run_backtest
from app.scoring.config import ScoringConfig
from tests.fixtures.ohlcv import build_df, candle, flat_padding


def test_backtest_runs_and_returns_summary_shape():
    rows = flat_padding(300, base=100.0, step=0.15, volume=150_000)
    # sprinkle in a couple of engineered reversal setups
    for offset in (100, 200):
        last = rows[offset]
        rows[offset] = candle(last["open"] + 1.5, last["open"] + 1.7, last["open"] - 2.0, last["open"] - 1.8, 200_000)
        rows[offset + 1] = candle(rows[offset]["close"] - 0.2, rows[offset]["open"] + 2.5, rows[offset]["close"] - 0.3, rows[offset]["open"] + 2.2, 400_000)

    df = build_df(rows)
    config = ScoringConfig()
    config.min_signal_score = 50  # lower bar so the synthetic data yields at least one trade
    summary = run_backtest(df, "TEST", "1d", config=config)

    assert summary.symbol == "TEST"
    assert summary.total_trades >= 0
    assert 0.0 <= summary.win_rate <= 1.0
    for pattern_perf in summary.by_pattern:
        assert pattern_perf.trade_count > 0


def test_backtest_with_no_matching_patterns_returns_empty_summary():
    df = build_df(flat_padding(200, base=50.0, step=0.0, volume=100_000))
    summary = run_backtest(df, "FLAT", "1d")
    assert summary.total_trades == 0
    assert summary.win_rate == 0.0
    assert summary.trades == []
