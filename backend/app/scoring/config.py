"""
Configurable scoring weights/thresholds (spec sections 5 and 27).

These are stored in the `system_configuration` DB table (key
"scoring_config") rather than hardcoded, so they can be tuned from the
Settings UI without a redeploy - `get_scoring_config()`/`save_scoring_config()`
are the only functions the rest of the app should use to read/write them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from app.models.config import SystemConfiguration

CONFIG_KEY = "scoring_config"


@dataclass
class ScoringWeights:
    """Max points per component. Spec section 27's news-aware 100-point
    rubric is the default (it supersedes the simpler section-5 rubric,
    which is the special case news=macro=sector=0, pattern/trend/volume/
    support_resistance/momentum/risk_reward rescaled to 30/20/15/15/10/10).
    """

    pattern: float = 25.0
    trend: float = 15.0
    volume: float = 10.0
    support_resistance: float = 10.0
    momentum: float = 10.0
    risk_reward: float = 10.0
    news: float = 10.0
    macro: float = 5.0
    sector: float = 5.0

    def total_possible(self) -> float:
        return sum(asdict(self).values())


@dataclass
class ScoreThresholds:
    exceptional: float = 90.0
    strong: float = 80.0
    good: float = 70.0
    watch: float = 60.0
    # below `watch` => ignore


@dataclass
class RiskPolicy:
    # if True, a CRITICAL-severity news item conflicting with the setup's
    # direction suppresses the alert outright regardless of score (spec
    # section 28: "A CRITICAL event should be capable of suppressing a
    # technical signal"). If False, it only applies the score penalty.
    suppress_on_critical_conflict: bool = True
    # minimum acceptable risk:reward to target 1 for a signal to be alertable
    min_risk_reward_t1: float = 1.2


@dataclass
class ScoringConfig:
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    thresholds: ScoreThresholds = field(default_factory=ScoreThresholds)
    risk_policy: RiskPolicy = field(default_factory=RiskPolicy)
    min_signal_score: float = 70.0  # global default gate; per-watchlist-item override in WatchlistItem.min_score_override

    def to_dict(self) -> dict:
        return {
            "weights": asdict(self.weights),
            "thresholds": asdict(self.thresholds),
            "risk_policy": asdict(self.risk_policy),
            "min_signal_score": self.min_signal_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoringConfig":
        return cls(
            weights=ScoringWeights(**data.get("weights", {})),
            thresholds=ScoreThresholds(**data.get("thresholds", {})),
            risk_policy=RiskPolicy(**data.get("risk_policy", {})),
            min_signal_score=data.get("min_signal_score", 70.0),
        )


def classify_score(score: float, thresholds: ScoreThresholds) -> str:
    if score >= thresholds.exceptional:
        return "exceptional"
    if score >= thresholds.strong:
        return "strong"
    if score >= thresholds.good:
        return "good"
    if score >= thresholds.watch:
        return "watch"
    return "ignore"


def get_scoring_config(db: Session) -> ScoringConfig:
    row = db.query(SystemConfiguration).filter_by(key=CONFIG_KEY).one_or_none()
    if row is None:
        return ScoringConfig()
    try:
        return ScoringConfig.from_dict(row.value)
    except Exception:
        return ScoringConfig()


def save_scoring_config(db: Session, config: ScoringConfig) -> None:
    row = db.query(SystemConfiguration).filter_by(key=CONFIG_KEY).one_or_none()
    if row is None:
        row = SystemConfiguration(
            key=CONFIG_KEY,
            value=config.to_dict(),
            description="Signal scoring weights, classification thresholds, and risk policy",
        )
        db.add(row)
    else:
        row.value = config.to_dict()
    db.commit()
