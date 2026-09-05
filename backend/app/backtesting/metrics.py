"""Performance metrics computed from a list of simulated trade outcomes
(spec section 15: win rate, avg return, max drawdown, profit factor, avg R,
per-pattern performance)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TradeOutcome:
    symbol: str
    timeframe: str
    pattern_key: str
    direction: str
    entry_time: str
    exit_time: str
    exit_reason: str  # "target_1" | "target_2" | "target_3" | "stop" | "expired"
    r_multiple: float  # return expressed in multiples of risk (R)
    quality_score: float


@dataclass
class PatternPerformance:
    pattern_key: str
    trade_count: int
    win_rate: float
    avg_r: float
    profit_factor: float


@dataclass
class BacktestSummary:
    symbol: str
    timeframe: str
    total_trades: int
    win_rate: float
    avg_r: float
    max_drawdown_r: float
    profit_factor: float
    total_r: float
    by_pattern: list[PatternPerformance] = field(default_factory=list)
    trades: list[TradeOutcome] = field(default_factory=list)


def _profit_factor(r_values: list[float]) -> float:
    gross_profit = sum(r for r in r_values if r > 0)
    gross_loss = abs(sum(r for r in r_values if r < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 2)


def _max_drawdown(r_values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_values:
        equity += r
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return round(max_dd, 2)


def summarize(symbol: str, timeframe: str, trades: list[TradeOutcome]) -> BacktestSummary:
    if not trades:
        return BacktestSummary(
            symbol=symbol, timeframe=timeframe, total_trades=0, win_rate=0.0, avg_r=0.0,
            max_drawdown_r=0.0, profit_factor=0.0, total_r=0.0, by_pattern=[], trades=[],
        )

    r_values = [t.r_multiple for t in trades]
    wins = [r for r in r_values if r > 0]

    by_pattern: dict[str, list[float]] = {}
    for t in trades:
        by_pattern.setdefault(t.pattern_key, []).append(t.r_multiple)

    pattern_perf = [
        PatternPerformance(
            pattern_key=key,
            trade_count=len(values),
            win_rate=round(sum(1 for v in values if v > 0) / len(values), 3),
            avg_r=round(sum(values) / len(values), 3),
            profit_factor=_profit_factor(values),
        )
        for key, values in sorted(by_pattern.items())
    ]

    return BacktestSummary(
        symbol=symbol,
        timeframe=timeframe,
        total_trades=len(trades),
        win_rate=round(len(wins) / len(trades), 3),
        avg_r=round(sum(r_values) / len(r_values), 3),
        max_drawdown_r=_max_drawdown(r_values),
        profit_factor=_profit_factor(r_values),
        total_r=round(sum(r_values), 2),
        by_pattern=pattern_perf,
        trades=trades,
    )
