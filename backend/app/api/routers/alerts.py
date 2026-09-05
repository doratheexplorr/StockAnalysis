from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.alert import AlertHistory
from app.schemas.alert import AlertHistoryOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertHistoryOut])
def list_alert_history(
    db: Session = Depends(get_db),
    signal_id: int | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(AlertHistory).order_by(AlertHistory.created_at.desc())
    if signal_id:
        stmt = stmt.where(AlertHistory.signal_id == signal_id)
    if status:
        stmt = stmt.where(AlertHistory.status == status)
    stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()
