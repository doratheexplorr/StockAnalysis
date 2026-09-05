"""
Renders a fully-scored setup into the alert text shown in-app and sent via
email/Telegram (spec sections 7, 29, 35). One AlertData -> multiple render
formats (plain text for Telegram/email body, and a dict for the in-app/API
JSON representation) so formatting logic lives in exactly one place.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.models.enums import Direction


@dataclass
class AlertData:
    symbol: str
    timeframe: str
    pattern_name: str
    direction: Direction
    quality_score: float
    classification: str
    current_price: float
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    rr_t1: float
    rr_t2: float
    rr_t3: float
    confirmations: list[dict]  # [{"label":..., "passed":..., "detail":...}]
    news_status: str  # supportive/conflicting/neutral/unavailable
    news_headline: str | None
    market_regime: str
    spy_trend: str
    sector: str
    sector_trend: str
    explanation: str
    detected_at: dt.datetime
    confidence_label: str  # HIGH/MEDIUM/LOW derived from classification


_NEWS_ICON = {"supportive": "🟢", "conflicting": "🔴", "neutral": "⚪", "unavailable": "⚪"}
_NEWS_TEXT = {
    "supportive": "Supportive",
    "conflicting": "Conflicting",
    "neutral": "Neutral",
    "unavailable": "Unavailable",
}
_CLASS_ICON = {"exceptional": "🔥", "strong": "🔥", "good": "✅", "watch": "👀", "ignore": "❌"}


def confidence_from_classification(classification: str) -> str:
    return {"exceptional": "HIGH", "strong": "HIGH", "good": "MEDIUM", "watch": "LOW", "ignore": "LOW"}.get(
        classification, "LOW"
    )


def render_text(alert: AlertData) -> str:
    direction_label = "BULLISH" if alert.direction == Direction.BULLISH else (
        "BEARISH" if alert.direction == Direction.BEARISH else "NEUTRAL"
    )
    icon = _CLASS_ICON.get(alert.classification, "")
    divider = "━" * 20

    confirmations_lines = "\n".join(
        f"{'✓' if c['passed'] else '✗'} {c['detail'] if c['detail'] else c['label']}"
        for c in alert.confirmations
        if c["passed"]
    ) or "(no confirmation factors passed)"

    news_line = f"{_NEWS_ICON.get(alert.news_status, '⚪')} {_NEWS_TEXT.get(alert.news_status, alert.news_status.title())}"
    news_headline_line = f'\n"{alert.news_headline}"' if alert.news_headline else ""

    text = f"""{divider}
{icon} {alert.classification.upper()} {direction_label} SETUP
{divider}

Ticker: {alert.symbol}
Timeframe: {alert.timeframe}

Pattern:
{alert.pattern_name}

Signal Score:
{alert.quality_score:.0f}/100 — {alert.classification.upper()}

Price:
${alert.current_price:.2f}

Entry:
${alert.entry:.2f}

Stop:
${alert.stop_loss:.2f}

Target 1:
${alert.target_1:.2f}

Target 2:
${alert.target_2:.2f}

Target 3:
${alert.target_3:.2f}

R:R:
1:{alert.rr_t1:.1f} / 1:{alert.rr_t2:.1f} / 1:{alert.rr_t3:.1f}

TECHNICALS:
{confirmations_lines}

NEWS:
{news_line}{news_headline_line}

MARKET:
Regime: {alert.market_regime} (S&P 500 {alert.spy_trend})
Sector ({alert.sector}): {alert.sector_trend}

REASON:
{alert.explanation}

CONFIDENCE:
{alert.confidence_label}

{divider}
This is an analytical signal, NOT a guaranteed trading recommendation.
Always do your own research and manage risk appropriately.
{divider}"""
    return text


def render_summary(alert: AlertData) -> str:
    direction_label = "Bullish" if alert.direction == Direction.BULLISH else "Bearish"
    return (
        f"{alert.symbol} {alert.timeframe}: {alert.pattern_name} ({direction_label}) - "
        f"{alert.quality_score:.0f}/100 {alert.classification}"
    )
