"""
Backtesting foundation (spec section 15).

Replays the SAME detector/indicator/scoring/risk code paths used live -
via an expanding walk-forward window - so backtest results are a faithful
approximation of what the live system would have alerted on. This is
explicitly a "foundation" per the spec ("you do not need to build a
sophisticated backtesting UI") rather than a full historical
news/regime-aware simulator:

    * News and market-regime context are NOT replayed historically (that
      would require a historical news + SPY/VIX archive this MVP does not
      fetch/store) - the news/macro/sector score components are held
      neutral during backtests. This means backtested scores are
      systematically a bit different from what a fully news-aware live
      alert would have scored; treat backtest scores as a technical-only
      lower/upper bound, not an exact replay.
    * When both a stop and a target could technically be hit within the
      same subsequent bar (a wide bar), the stop is assumed to hit first
      (a conservative assumption for risk purposes).

See README "Backtesting architecture" for how to extend this with a
historical news archive later.
"""
from __future__ import annotations

import pandas as pd

from app.alerts.dedup import make_fingerprint
from app.backtesting.metrics import BacktestSummary, TradeOutcome, summarize
from app.indicators.snapshot import compute_indicator_snapshot
from app.market_context.regime import RegimeContext
from app.models.enums import Direction, MarketRegime
from app.news.analysis import NewsContextResult
from app.patterns.registry import detect_all
from app.risk.calculator import calculate_risk_levels
from app.scoring.config import ScoringConfig
from app.scoring.engine import score_setup

MIN_LOOKBACK_BARS = 60
PATTERN_WINDOW_BARS = 3
MAX_HOLDING_BARS = 50

_NEUTRAL_NEWS = NewsContextResult(
    status="neutral", adjustment_points=0.0, has_critical_conflict=False,
    reason="Backtest mode: historical news is not replayed.",
)
_NEUTRAL_REGIME = RegimeContext(
    regime=MarketRegime.NEUTRAL, spy_trend="sideways", vix_level=None, vix_bucket="unknown",
    supportive_for=[Direction.BULLISH, Direction.BEARISH],
    description="Backtest mode: historical market regime is not replayed.",
)


def _simulate_trade_outcome(
    df: pd.DataFrame, entry_idx: int, direction: Direction, entry: float, stop: float, t1: float, t2: float, t3: float
) -> tuple[str, float]:
    """Walk forward from entry_idx+1 and return (exit_reason, r_multiple)."""
    risk = abs(entry - stop)
    if risk <= 0:
        return "expired", 0.0

    end = min(len(df), entry_idx + 1 + MAX_HOLDING_BARS)
    for i in range(entry_idx + 1, end):
        bar = df.iloc[i]
        if direction == Direction.BULLISH:
            hit_stop = bar["low"] <= stop
            hit_t3 = bar["high"] >= t3
            hit_t2 = bar["high"] >= t2
            hit_t1 = bar["high"] >= t1
        else:
            hit_stop = bar["high"] >= stop
            hit_t3 = bar["low"] <= t3
            hit_t2 = bar["low"] <= t2
            hit_t1 = bar["low"] <= t1

        if hit_stop:
            return "stop", -1.0
        if hit_t3:
            return "target_3", abs(t3 - entry) / risk
        if hit_t2:
            return "target_2", abs(t2 - entry) / risk
        if hit_t1:
            return "target_1", abs(t1 - entry) / risk

    # never hit - mark to the last available close within the holding window
    final_close = df.iloc[end - 1]["close"]
    r = (final_close - entry) / risk if direction == Direction.BULLISH else (entry - final_close) / risk
    return "expired", round(r, 3)


def run_backtest(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    config: ScoringConfig | None = None,
    enabled_patterns: list[str] | None = None,
) -> BacktestSummary:
    config = config or ScoringConfig()
    trades: list[TradeOutcome] = []
    seen_fingerprints: set[str] = set()

    for i in range(MIN_LOOKBACK_BARS, len(df)):
        window = df.iloc[: i + 1]
        matches = detect_all(window, enabled_keys=enabled_patterns)
        directional = [m for m in matches if m.direction in (Direction.BULLISH, Direction.BEARISH)]
        if not directional:
            continue
        best = max(directional, key=lambda m: m.strength)

        candle_timestamp = window.index[-1].to_pydatetime()
        fingerprint = make_fingerprint(symbol, timeframe, best.pattern_key, candle_timestamp)
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)

        indicators = compute_indicator_snapshot(window)
        current_price = float(window["close"].iloc[-1])
        pattern_window = window.tail(PATTERN_WINDOW_BARS)
        already_broken_out = (best.direction == Direction.BULLISH and indicators.breakout == "breakout") or (
            best.direction == Direction.BEARISH and indicators.breakout == "breakdown"
        )

        risk = calculate_risk_levels(
            direction=best.direction,
            current_price=current_price,
            atr=indicators.atr_14 or 0.0,
            pattern_low=float(pattern_window["low"].min()),
            pattern_high=float(pattern_window["high"].max()),
            support=indicators.support_level,
            resistance=indicators.resistance_level,
            already_broken_out=already_broken_out,
        )
        if risk.rr_t1 < config.risk_policy.min_risk_reward_t1:
            continue

        score_result = score_setup(
            pattern=best,
            direction=best.direction,
            current_price=current_price,
            indicators=indicators,
            risk=risk,
            news=_NEUTRAL_NEWS,
            regime=_NEUTRAL_REGIME,
            sector="Unknown",
            sector_trend_value="unknown",
            config=config,
        )
        if score_result.total_score < config.min_signal_score or score_result.suppressed:
            continue

        exit_reason, r_multiple = _simulate_trade_outcome(
            df, i, best.direction, risk.entry, risk.stop_loss, risk.target_1, risk.target_2, risk.target_3
        )
        exit_idx = min(len(df) - 1, i + MAX_HOLDING_BARS)
        trades.append(
            TradeOutcome(
                symbol=symbol,
                timeframe=timeframe,
                pattern_key=best.pattern_key,
                direction=best.direction.value,
                entry_time=str(candle_timestamp),
                exit_time=str(df.index[exit_idx]),
                exit_reason=exit_reason,
                r_multiple=r_multiple,
                quality_score=score_result.total_score,
            )
        )

    return summarize(symbol, timeframe, trades)
