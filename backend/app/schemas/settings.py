from __future__ import annotations

from pydantic import BaseModel

from app.scoring.config import RiskPolicy, ScoreThresholds, ScoringWeights


class ScoringConfigOut(BaseModel):
    weights: ScoringWeights
    thresholds: ScoreThresholds
    risk_policy: RiskPolicy
    min_signal_score: float


class ScoringConfigUpdate(BaseModel):
    weights: ScoringWeights | None = None
    thresholds: ScoreThresholds | None = None
    risk_policy: RiskPolicy | None = None
    min_signal_score: float | None = None


class PatternInfo(BaseModel):
    key: str
    display_name: str
    direction: str


class NotificationPreferenceOut(BaseModel):
    channel: str
    enabled: bool
    config: dict | None = None


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool
    config: dict | None = None
