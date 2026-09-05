"""
The end-to-end analysis pipeline for one (symbol, timeframe) pair (spec
section 34):

MARKET DATA -> CANDLE CLOSE CHECK -> CANDLESTICK DETECTION -> INDICATORS ->
SUPPORT/RESISTANCE -> VOLUME/MOMENTUM -> COMPANY NEWS -> SECTOR/MACRO
CONTEXT -> SIGNAL SCORE -> RISK/REWARD CHECK -> DEDUP -> FINAL ALERT DECISION

This module is intentionally the only place that wires the independent
layers (market_data, indicators, patterns, news, market_context, scoring,
risk, alerts) together, so each of those stays independently testable and
this orchestration itself can be unit tested against fakes/mocks (see
backend/tests/test_scheduler).
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy.orm import Session

from app.alerts.candle_close import split_confirmed_and_forming
from app.alerts.dedup import should_emit_signal
from app.alerts.formatter import AlertData, confidence_from_classification
from app.alerts.notifier import dispatch_signal
from app.core.config import get_settings
from app.core.logging import get_logger
from app.indicators.snapshot import compute_indicator_snapshot
from app.market_context.regime import classify_market_regime, sector_trend as compute_sector_trend
from app.market_context.sector import get_sector, get_sector_etf
from app.market_data.base import MarketDataError, MarketDataProvider
from app.models.detection import CandlestickDetection
from app.models.enums import Direction, NotificationChannelType, SignalStatus
from app.models.indicator_snapshot import IndicatorSnapshot
from app.models.signal import Signal
from app.models.watchlist import WatchlistItem
from app.news.analysis import analyze_news_context
from app.news.base import NewsProvider, NewsUnavailableError
from app.patterns.registry import detect_all
from app.risk.calculator import calculate_risk_levels
from app.scoring.config import ScoringConfig, get_scoring_config
from app.scoring.engine import score_setup

logger = get_logger(__name__)

MIN_LOOKBACK_BARS = 60
PATTERN_WINDOW_BARS = 3  # bars examined for pattern_low/pattern_high risk anchoring


class PipelineResult:
    def __init__(self, signal: Signal | None, reason: str):
        self.signal = signal
        self.reason = reason


def _effective_timeframes(item: WatchlistItem, settings) -> list[str]:
    if item.timeframes:
        return item.timeframes
    return [tf.strip() for tf in settings.default_timeframes.split(",") if tf.strip()]


def _effective_min_score(item: WatchlistItem, config: ScoringConfig) -> float:
    return item.min_score_override if item.min_score_override is not None else config.min_signal_score


def _effective_channels(item: WatchlistItem) -> list[str]:
    if item.notification_channels:
        return item.notification_channels
    return [NotificationChannelType.IN_APP.value]


def process_symbol_timeframe(
    db: Session,
    item: WatchlistItem,
    timeframe: str,
    market_data: MarketDataProvider,
    news_provider: NewsProvider,
    now: dt.datetime | None = None,
) -> PipelineResult:
    now = now or dt.datetime.now(dt.timezone.utc)
    symbol = item.symbol.upper()
    settings = get_settings()
    config = get_scoring_config(db)

    # 1. MARKET DATA
    try:
        raw_df = market_data.get_ohlcv(symbol, timeframe, lookback_bars=300)
    except MarketDataError as exc:
        logger.warning("Market data fetch failed for %s/%s: %s", symbol, timeframe, exc)
        return PipelineResult(None, f"market_data_error: {exc}")

    # 2. CANDLE CLOSE CHECK
    confirmed_df, _forming = split_confirmed_and_forming(raw_df, timeframe, now)
    if len(confirmed_df) < MIN_LOOKBACK_BARS:
        return PipelineResult(None, "insufficient_confirmed_history")

    candle_timestamp = confirmed_df.index[-1].to_pydatetime()

    # 3. CANDLESTICK DETECTION
    enabled_patterns = item.enabled_patterns or None
    matches = detect_all(confirmed_df, enabled_keys=enabled_patterns)
    if not matches:
        return PipelineResult(None, "no_pattern_detected")

    # persist every raw detection for reproducibility/backtesting, regardless of score
    window = confirmed_df.tail(PATTERN_WINDOW_BARS)
    raw_ohlcv = window.reset_index().rename(columns={"index": "timestamp"}).assign(
        timestamp=lambda d: d["timestamp"].astype(str)
    ).to_dict(orient="records")

    for match in matches:
        db.add(
            CandlestickDetection(
                symbol=symbol,
                timeframe=timeframe,
                pattern_key=match.pattern_key,
                pattern_name=match.pattern_name,
                direction=match.direction.value,
                candle_timestamp=candle_timestamp,
                is_confirmed=True,
                pattern_strength=match.strength,
                raw_ohlcv=raw_ohlcv,
            )
        )
    db.commit()

    # "fewer, higher-quality signals": only the single strongest match on this
    # candle proceeds to scoring/alerting (a directional one, i.e. skip pure
    # NEUTRAL matches like a lone Doji unless nothing else fired)
    directional_matches = [m for m in matches if m.direction in (Direction.BULLISH, Direction.BEARISH)]
    best_match = max(directional_matches or matches, key=lambda m: m.strength)
    direction = best_match.direction
    if direction == Direction.NEUTRAL:
        return PipelineResult(None, "only_neutral_pattern_detected")

    # 4. INDICATORS / SUPPORT-RESISTANCE / VOLUME-MOMENTUM
    indicators = compute_indicator_snapshot(confirmed_df)
    snapshot_row = IndicatorSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        candle_timestamp=candle_timestamp,
        **{k: v for k, v in indicators.as_dict().items() if k not in ("consolidation",)},
        consolidation=indicators.consolidation,
    )
    db.add(snapshot_row)
    db.commit()

    current_price = float(confirmed_df["close"].iloc[-1])
    pattern_low = float(window["low"].min())
    pattern_high = float(window["high"].max())
    already_broken_out = (direction == Direction.BULLISH and indicators.breakout == "breakout") or (
        direction == Direction.BEARISH and indicators.breakout == "breakdown"
    )

    risk = calculate_risk_levels(
        direction=direction,
        current_price=current_price,
        atr=indicators.atr_14 or 0.0,
        pattern_low=pattern_low,
        pattern_high=pattern_high,
        support=indicators.support_level,
        resistance=indicators.resistance_level,
        already_broken_out=already_broken_out,
    )

    # 5. COMPANY NEWS
    try:
        news_items = news_provider.get_company_news(symbol)
        news_context = analyze_news_context(direction, news_items, max_points=config.weights.news)
    except NewsUnavailableError as exc:
        news_context = analyze_news_context(direction, [], max_points=config.weights.news)
        news_context.status = "unavailable"
        news_context.reason = "News unavailable — technical analysis only."
        logger.info("News unavailable for %s: %s", symbol, exc)

    # 6. SECTOR / MACRO / MARKET REGIME
    regime = classify_market_regime(market_data)
    sector = get_sector(symbol)
    etf = get_sector_etf(sector)
    sector_trend_value = compute_sector_trend(market_data, etf) if etf else "unknown"

    # 7. SIGNAL SCORE
    score_result = score_setup(
        pattern=best_match,
        direction=direction,
        current_price=current_price,
        indicators=indicators,
        risk=risk,
        news=news_context,
        regime=regime,
        sector=sector,
        sector_trend_value=sector_trend_value,
        config=config,
    )

    min_score = _effective_min_score(item, config)

    # 8. RISK/REWARD CHECK + FINAL ALERT DECISION
    if risk.rr_t1 < config.risk_policy.min_risk_reward_t1:
        return PipelineResult(None, f"risk_reward_below_minimum ({risk.rr_t1} < {config.risk_policy.min_risk_reward_t1})")

    if score_result.total_score < min_score and not score_result.suppressed:
        return PipelineResult(None, f"score_below_threshold ({score_result.total_score} < {min_score})")

    should_emit, fingerprint, dedup_reason = should_emit_signal(
        db, symbol, timeframe, best_match.pattern_key, candle_timestamp,
        cooldown_minutes=settings.default_alert_cooldown_minutes,
    )
    if not should_emit:
        return PipelineResult(None, dedup_reason)

    signal = Signal(
        detection_id=None,
        indicator_snapshot_id=snapshot_row.id,
        symbol=symbol,
        timeframe=timeframe,
        pattern_key=best_match.pattern_key,
        pattern_name=best_match.pattern_name,
        direction=direction.value,
        candle_timestamp=candle_timestamp,
        detected_at=now,
        quality_score=score_result.total_score,
        classification=score_result.classification,
        score_breakdown={**score_result.breakdown, "weights_used": score_result.weights_used},
        current_price=current_price,
        entry_price=risk.entry,
        stop_loss=risk.stop_loss,
        target_1=risk.target_1,
        target_2=risk.target_2,
        target_3=risk.target_3,
        risk_per_share=risk.risk_per_share,
        reward_to_t1=risk.reward_to_t1,
        reward_to_t2=risk.reward_to_t2,
        reward_to_t3=risk.reward_to_t3,
        rr_t1=risk.rr_t1,
        rr_t2=risk.rr_t2,
        rr_t3=risk.rr_t3,
        risk_methodology=risk.methodology,
        technical_confirmations=[c.as_dict() for c in score_result.confirmations],
        news_context={
            "status": news_context.status,
            "reason": news_context.reason,
            "items": news_context.headline_items,
        },
        market_context={
            "regime": regime.regime.value,
            "spy_trend": regime.spy_trend,
            "vix_level": regime.vix_level,
            "sector": sector,
            "sector_trend": sector_trend_value,
        },
        explanation=score_result.explanation,
        status=SignalStatus.SUPPRESSED.value if score_result.suppressed else SignalStatus.ACTIVE.value,
        fingerprint=fingerprint,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    if score_result.suppressed:
        logger.info("Signal for %s/%s suppressed: %s", symbol, timeframe, score_result.suppression_reason)
        return PipelineResult(signal, f"suppressed: {score_result.suppression_reason}")

    # 9. NOTIFY
    alert = AlertData(
        symbol=symbol,
        timeframe=timeframe,
        pattern_name=best_match.pattern_name,
        direction=direction,
        quality_score=score_result.total_score,
        classification=score_result.classification,
        current_price=current_price,
        entry=risk.entry,
        stop_loss=risk.stop_loss,
        target_1=risk.target_1,
        target_2=risk.target_2,
        target_3=risk.target_3,
        rr_t1=risk.rr_t1,
        rr_t2=risk.rr_t2,
        rr_t3=risk.rr_t3,
        confirmations=[c.as_dict() for c in score_result.confirmations],
        news_status=news_context.status,
        news_headline=news_context.headline_items[0]["headline"] if news_context.headline_items else None,
        market_regime=regime.regime.value,
        spy_trend=regime.spy_trend,
        sector=sector,
        sector_trend=sector_trend_value,
        explanation=score_result.explanation,
        detected_at=now,
        confidence_label=confidence_from_classification(score_result.classification),
    )
    dispatch_signal(db, signal, alert, _effective_channels(item))

    return PipelineResult(signal, "alert_emitted")
