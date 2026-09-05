"""
The signal-quality scoring engine (spec sections 5 & 27) - the heart of the
"fewer, higher-quality signals" product principle. A raw pattern match is
NEVER alerted on its own; it must pass through every confirmation factor
here and clear the configured minimum score.

Score = pattern + trend + volume + support/resistance + momentum +
        risk/reward + news + macro + sector   (weights configurable, see
        app.scoring.config.ScoringWeights)

A CRITICAL-severity news conflict can suppress the alert outright
regardless of score, per RiskPolicy.suppress_on_critical_conflict.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.indicators.snapshot import IndicatorValues
from app.market_context.regime import RegimeContext
from app.models.enums import Direction
from app.news.analysis import NewsContextResult
from app.patterns.base import PatternMatch
from app.risk.calculator import RiskLevels
from app.scoring.config import ScoringConfig, classify_score


@dataclass
class Confirmation:
    label: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"label": self.label, "passed": self.passed, "detail": self.detail}


@dataclass
class ScoreResult:
    total_score: float
    classification: str
    breakdown: dict  # component -> points awarded
    weights_used: dict
    confirmations: list[Confirmation]
    suppressed: bool
    suppression_reason: str | None
    explanation: str


def _pattern_component(pattern: PatternMatch, max_points: float) -> tuple[float, Confirmation]:
    points = pattern.strength * max_points
    return points, Confirmation(
        label=f"{pattern.pattern_name} pattern",
        passed=True,
        detail=f"detector confidence {pattern.strength:.0%}",
    )


def _trend_component(direction: Direction, ind: IndicatorValues, max_points: float) -> tuple[float, Confirmation]:
    """Rewards the current trend/momentum structure being aligned with the
    signal's direction - true for continuation patterns forming mid-trend,
    and for reversal patterns where short-term momentum (EMA9/21, MACD
    histogram) has already started turning in the new direction."""
    score = 0.0
    reasons = []

    wants_up = direction == Direction.BULLISH
    if ind.trend_direction == ("up" if wants_up else "down"):
        score += 0.5
        reasons.append(f"{ind.trend_direction} trend")
    elif ind.trend_direction == "sideways":
        score += 0.15

    if ind.structure == ("higher_highs_higher_lows" if wants_up else "lower_highs_lower_lows"):
        score += 0.25
        reasons.append("confirmed swing structure")

    if ind.ema_9 is not None and ind.ema_21 is not None:
        aligned = ind.ema_9 > ind.ema_21 if wants_up else ind.ema_9 < ind.ema_21
        if aligned:
            score += 0.25
            reasons.append("EMA9/EMA21 aligned")

    passed = score >= 0.5
    detail = ", ".join(reasons) if reasons else "trend not clearly aligned with signal direction"
    label = "Bullish trend" if wants_up else "Bearish trend"
    return score * max_points, Confirmation(label, passed, detail)


def _volume_component(ind: IndicatorValues, max_points: float) -> tuple[float, Confirmation]:
    rel_vol = ind.relative_volume
    if rel_vol is None:
        return 0.0, Confirmation("Relative volume", False, "insufficient volume history")
    # 1.0x -> 0 points, 2.0x+ -> full points, linear in between (floor 0)
    score = max(0.0, min(1.0, (rel_vol - 1.0) / 1.0))
    passed = rel_vol >= 1.3
    return score * max_points, Confirmation("Relative volume", passed, f"{rel_vol:.1f}x average volume")


def _support_resistance_component(
    direction: Direction, current_price: float, ind: IndicatorValues, max_points: float
) -> tuple[float, Confirmation]:
    score = 0.0
    details = []
    if direction == Direction.BULLISH:
        if ind.breakout == "breakout":
            score += 0.6
            details.append("breakout above resistance")
        elif ind.support_level is not None and ind.atr_14:
            proximity = abs(current_price - ind.support_level) / max(ind.atr_14, 1e-6)
            if proximity <= 1.5:
                score += 0.6 * max(0.0, 1 - proximity / 1.5)
                details.append(f"forming near support (${ind.support_level:.2f})")
        if ind.resistance_level is not None:
            score += 0.4
            details.append(f"resistance identified at ${ind.resistance_level:.2f} for target reference")
    else:
        if ind.breakout == "breakdown":
            score += 0.6
            details.append("breakdown below support")
        elif ind.resistance_level is not None and ind.atr_14:
            proximity = abs(current_price - ind.resistance_level) / max(ind.atr_14, 1e-6)
            if proximity <= 1.5:
                score += 0.6 * max(0.0, 1 - proximity / 1.5)
                details.append(f"forming near resistance (${ind.resistance_level:.2f})")
        if ind.support_level is not None:
            score += 0.4
            details.append(f"support identified at ${ind.support_level:.2f} for target reference")

    score = min(1.0, score)
    passed = score >= 0.5
    detail = ", ".join(details) if details else "no clear support/resistance confluence"
    return score * max_points, Confirmation("Support/resistance", passed, detail)


def _momentum_component(direction: Direction, ind: IndicatorValues, max_points: float) -> tuple[float, Confirmation]:
    score = 0.0
    details = []
    if ind.rsi_14 is not None:
        if direction == Direction.BULLISH:
            if 40 <= ind.rsi_14 <= 70:
                score += 0.5
            elif ind.rsi_14 < 40:
                score += 0.3  # recovering from oversold - plausible reversal momentum
            details.append(f"RSI {ind.rsi_14:.0f}")
        else:
            if 30 <= ind.rsi_14 <= 60:
                score += 0.5
            elif ind.rsi_14 > 60:
                score += 0.3
            details.append(f"RSI {ind.rsi_14:.0f}")

    if ind.macd_hist is not None:
        aligned = ind.macd_hist > 0 if direction == Direction.BULLISH else ind.macd_hist < 0
        if aligned:
            score += 0.5
            details.append("MACD histogram aligned")

    score = min(1.0, score)
    passed = score >= 0.5
    detail = ", ".join(details) if details else "momentum not aligned"
    return score * max_points, Confirmation("Momentum", passed, detail)


def _risk_reward_component(risk: RiskLevels, min_rr: float, max_points: float) -> tuple[float, Confirmation]:
    rr = risk.rr_t1
    score = max(0.0, min(1.0, (rr - min_rr) / (3.0 - min_rr))) if rr > min_rr else 0.0
    passed = rr >= min_rr
    return score * max_points, Confirmation("Risk/reward", passed, f"R:R to T1 = 1:{rr:.1f}")


def _news_component(news: NewsContextResult, max_points: float) -> tuple[float, Confirmation]:
    # news.adjustment_points is already scaled to +/- max_points by the caller
    points = max(0.0, news.adjustment_points)  # component score is non-negative; conflict is handled as a penalty below
    passed = news.status == "supportive"
    label_map = {"supportive": "🟢 Supportive", "conflicting": "🔴 Conflicting", "neutral": "⚪ Neutral", "unavailable": "⚪ Unavailable"}
    return points, Confirmation("News context", passed, f"{label_map.get(news.status, news.status)}: {news.reason}")


def _macro_component(direction: Direction, regime: RegimeContext, max_points: float) -> tuple[float, Confirmation]:
    if direction in regime.supportive_for and len(regime.supportive_for) == 1:
        score = 1.0
    elif direction in regime.supportive_for:
        score = 0.5
    else:
        score = 0.0
    passed = score >= 0.5
    return score * max_points, Confirmation("Market regime", passed, regime.description)


def _sector_component(direction: Direction, sector_trend: str, sector: str, max_points: float) -> tuple[float, Confirmation]:
    wants_up = direction == Direction.BULLISH
    if sector_trend == "up":
        score = 1.0 if wants_up else 0.0
    elif sector_trend == "down":
        score = 1.0 if not wants_up else 0.0
    else:
        score = 0.5  # unknown/sideways - neutral credit
    passed = score >= 0.5
    return score * max_points, Confirmation("Sector context", passed, f"{sector} sector trend: {sector_trend}")


def score_setup(
    *,
    pattern: PatternMatch,
    direction: Direction,
    current_price: float,
    indicators: IndicatorValues,
    risk: RiskLevels,
    news: NewsContextResult,
    regime: RegimeContext,
    sector: str,
    sector_trend_value: str,
    config: ScoringConfig,
) -> ScoreResult:
    w = config.weights
    breakdown: dict[str, float] = {}
    confirmations: list[Confirmation] = []

    pts, conf = _pattern_component(pattern, w.pattern)
    breakdown["pattern"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _trend_component(direction, indicators, w.trend)
    breakdown["trend"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _volume_component(indicators, w.volume)
    breakdown["volume"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _support_resistance_component(direction, current_price, indicators, w.support_resistance)
    breakdown["support_resistance"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _momentum_component(direction, indicators, w.momentum)
    breakdown["momentum"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _risk_reward_component(risk, config.risk_policy.min_risk_reward_t1, w.risk_reward)
    breakdown["risk_reward"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _news_component(news, w.news)
    breakdown["news"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _macro_component(direction, regime, w.macro)
    breakdown["macro"] = round(pts, 2)
    confirmations.append(conf)

    pts, conf = _sector_component(direction, sector_trend_value, sector, w.sector)
    breakdown["sector"] = round(pts, 2)
    confirmations.append(conf)

    total = sum(breakdown.values())

    suppressed = False
    suppression_reason = None

    # News conflict penalty: a conflicting or critical news item pulls the
    # total down (it already contributed 0 to the news component above -
    # this additionally discounts the OTHER components since the market may
    # reprice the whole technical picture on major conflicting news).
    if news.status == "conflicting":
        penalty_factor = 0.7 if not news.has_critical_conflict else 0.4
        total *= penalty_factor
        breakdown["news_conflict_penalty_factor"] = penalty_factor

    if news.has_critical_conflict and config.risk_policy.suppress_on_critical_conflict:
        suppressed = True
        suppression_reason = (
            "Suppressed: CRITICAL-severity news conflicts with the technical setup's direction "
            "(see news_context for the triggering headline)."
        )

    if regime.regime.value == "high_volatility" and direction is not None:
        total *= 0.85  # dampen confidence during high-volatility/risk-off tape, but don't zero it out

    total = max(0.0, min(100.0, total))
    classification = classify_score(total, config.thresholds)

    passed_labels = [c.label for c in confirmations if c.passed]
    explanation = (
        f"{pattern.pattern_name} ({direction.value}) on confirmed candle close, scoring {total:.0f}/100 "
        f"({classification}). Confirmed by: {', '.join(passed_labels) if passed_labels else 'pattern shape alone - weak confirmation'}. "
        f"{pattern.description}"
    )

    return ScoreResult(
        total_score=round(total, 1),
        classification=classification,
        breakdown=breakdown,
        weights_used={
            "pattern": w.pattern, "trend": w.trend, "volume": w.volume,
            "support_resistance": w.support_resistance, "momentum": w.momentum,
            "risk_reward": w.risk_reward, "news": w.news, "macro": w.macro, "sector": w.sector,
        },
        confirmations=confirmations,
        suppressed=suppressed,
        suppression_reason=suppression_reason,
        explanation=explanation,
    )
