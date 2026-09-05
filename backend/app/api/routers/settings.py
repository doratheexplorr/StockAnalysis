from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.config import NotificationPreference
from app.models.enums import NotificationChannelType
from app.patterns.registry import ALL_DETECTORS
from app.schemas.settings import (
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    PatternInfo,
    ScoringConfigOut,
    ScoringConfigUpdate,
)
from app.scoring.config import ScoringConfig, get_scoring_config, save_scoring_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/scoring", response_model=ScoringConfigOut)
def get_scoring_settings(db: Session = Depends(get_db)):
    config = get_scoring_config(db)
    save_scoring_config(db, config)  # persist defaults on first read so the UI has something to edit
    return ScoringConfigOut(**config.to_dict())


@router.put("/scoring", response_model=ScoringConfigOut)
def update_scoring_settings(payload: ScoringConfigUpdate, db: Session = Depends(get_db)):
    current = get_scoring_config(db)
    updated = ScoringConfig(
        weights=payload.weights or current.weights,
        thresholds=payload.thresholds or current.thresholds,
        risk_policy=payload.risk_policy or current.risk_policy,
        min_signal_score=payload.min_signal_score if payload.min_signal_score is not None else current.min_signal_score,
    )
    save_scoring_config(db, updated)
    return ScoringConfigOut(**updated.to_dict())


@router.get("/patterns", response_model=list[PatternInfo])
def list_patterns():
    return [
        PatternInfo(key=d.key, display_name=d.display_name, direction=d.direction.value)
        for d in ALL_DETECTORS
    ]


@router.get("/notifications", response_model=list[NotificationPreferenceOut])
def get_notification_preferences(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    rows = db.query(NotificationPreference).filter_by(user_id=user_id).all()
    existing = {r.channel for r in rows}
    # ensure every implemented channel has a row (defaulting to enabled) so the UI can render toggles
    for channel in (NotificationChannelType.IN_APP, NotificationChannelType.EMAIL, NotificationChannelType.TELEGRAM):
        if channel.value not in existing:
            row = NotificationPreference(user_id=user_id, channel=channel.value, enabled=True)
            db.add(row)
            rows.append(row)
    db.commit()
    return rows


@router.put("/notifications/{channel}", response_model=NotificationPreferenceOut)
def update_notification_preference(
    channel: str, payload: NotificationPreferenceUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    row = db.query(NotificationPreference).filter_by(user_id=user_id, channel=channel).one_or_none()
    if row is None:
        row = NotificationPreference(user_id=user_id, channel=channel)
        db.add(row)
    row.enabled = payload.enabled
    row.config = payload.config
    db.commit()
    db.refresh(row)
    return row
