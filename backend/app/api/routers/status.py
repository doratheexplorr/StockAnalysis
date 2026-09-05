from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.enums import Timeframe
from app.models.signal import Signal
from app.models.watchlist import WatchlistItem

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("")
def system_status(db: Session = Depends(get_db)):
    settings = get_settings()
    watchlist_count = db.execute(select(func.count(WatchlistItem.id)).where(WatchlistItem.enabled.is_(True))).scalar()
    latest_signal = db.execute(select(Signal).order_by(Signal.detected_at.desc()).limit(1)).scalar_one_or_none()

    now = dt.datetime.now(dt.timezone.utc)
    # crude US-equity-market-hours heuristic (weekdays, 13:30-20:00 UTC ~ 9:30am-4pm ET
    # ignoring the exact DST offset - see README "Known limitations")
    is_weekday = now.weekday() < 5
    market_open = is_weekday and dt.time(13, 30) <= now.time() <= dt.time(20, 0)

    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "polling_enabled": settings.polling_enabled,
        "market_data_provider": settings.market_data_provider,
        "news_provider": settings.news_provider,
        "supported_timeframes": [tf.value for tf in Timeframe],
        "active_watchlist_symbols": watchlist_count,
        "market_status": "open" if market_open else "closed",
        "latest_signal_at": latest_signal.detected_at.isoformat() if latest_signal else None,
        "server_time_utc": now.isoformat(),
    }
