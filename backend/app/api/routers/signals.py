from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.signal import Signal
from app.schemas.signal import SignalListItem, SignalOut

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=list[SignalListItem])
def list_signals(
    db: Session = Depends(get_db),
    symbol: str | None = None,
    status: str | None = None,
    classification: str | None = None,
    since_hours: int | None = Query(default=None, ge=1, le=24 * 90),
    limit: int = Query(default=50, ge=1, le=500),
):
    stmt = select(Signal).order_by(Signal.detected_at.desc())
    if symbol:
        stmt = stmt.where(Signal.symbol == symbol.upper())
    if status:
        stmt = stmt.where(Signal.status == status)
    if classification:
        stmt = stmt.where(Signal.classification == classification)
    if since_hours:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=since_hours)
        stmt = stmt.where(Signal.detected_at >= cutoff)
    stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/strongest", response_model=list[SignalListItem])
def strongest_signals(db: Session = Depends(get_db), limit: int = Query(default=10, ge=1, le=100)):
    stmt = (
        select(Signal)
        .where(Signal.status == "active")
        .order_by(Signal.quality_score.desc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


@router.get("/{signal_id}", response_model=SignalOut)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(404, "Signal not found")
    return signal
