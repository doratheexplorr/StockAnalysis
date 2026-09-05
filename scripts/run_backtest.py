#!/usr/bin/env python3
"""
Minimal backtesting CLI (spec section 15 - "foundation", not a full UI).

Usage:
    python scripts/run_backtest.py NVDA --timeframe 1d --lookback-bars 500

Fetches historical OHLCV via the configured MarketDataProvider and replays
it through the exact same detector/indicator/scoring/risk pipeline the live
system uses (app.backtesting.engine.run_backtest), then prints win rate,
average R, max drawdown, profit factor, and a per-pattern breakdown.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.backtesting.engine import run_backtest  # noqa: E402
from app.market_data.factory import get_market_data_provider  # noqa: E402
from app.scoring.config import ScoringConfig  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest the candlestick signal engine against historical data")
    parser.add_argument("symbol")
    parser.add_argument("--timeframe", default="1d", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
    parser.add_argument("--lookback-bars", type=int, default=500)
    parser.add_argument("--min-score", type=float, default=None, help="override the configured minimum signal score")
    parser.add_argument("--json", action="store_true", help="print raw JSON instead of a formatted summary")
    args = parser.parse_args()

    provider = get_market_data_provider()
    df = provider.get_ohlcv(args.symbol.upper(), args.timeframe, lookback_bars=args.lookback_bars)

    config = ScoringConfig()
    if args.min_score is not None:
        config.min_signal_score = args.min_score

    summary = run_backtest(df, args.symbol.upper(), args.timeframe, config=config)

    if args.json:
        print(json.dumps(summary.__dict__, default=lambda o: getattr(o, "__dict__", str(o)), indent=2))
        return

    print(f"\nBacktest: {summary.symbol} / {summary.timeframe}  ({summary.total_trades} trades)")
    print("-" * 60)
    print(f"Win rate:        {summary.win_rate:.1%}")
    print(f"Avg R:           {summary.avg_r:+.2f}")
    print(f"Total R:         {summary.total_r:+.2f}")
    print(f"Max drawdown:    {summary.max_drawdown_r:.2f}R")
    print(f"Profit factor:   {summary.profit_factor}")
    print("\nBy pattern:")
    for p in summary.by_pattern:
        print(f"  {p.pattern_key:<24} trades={p.trade_count:<4} win_rate={p.win_rate:.0%}  avg_R={p.avg_r:+.2f}  PF={p.profit_factor}")
    print(
        "\nNote: backtests are technical-only (news/market-regime context is neutral - "
        "not replayed historically). See README 'Backtesting architecture'.\n"
    )


if __name__ == "__main__":
    main()
