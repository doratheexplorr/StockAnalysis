from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db, get_or_create_default_watchlist
from app.models.watchlist import WatchlistItem
from app.patterns.registry import all_pattern_keys
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemOut, WatchlistItemUpdate

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemOut])
def list_watchlist(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    watchlist = get_or_create_default_watchlist(db, user_id)
    db.commit()
    return watchlist.items


@router.post("", response_model=WatchlistItemOut, status_code=201)
def add_stock(payload: WatchlistItemCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    watchlist = get_or_create_default_watchlist(db, user_id)

    symbol = payload.symbol.upper().strip()
    existing = next((i for i in watchlist.items if i.symbol == symbol), None)
    if existing:
        raise HTTPException(409, f"{symbol} is already on the watchlist")

    if payload.enabled_patterns:
        unknown = set(payload.enabled_patterns) - set(all_pattern_keys())
        if unknown:
            raise HTTPException(422, f"Unknown pattern keys: {sorted(unknown)}")

    item = WatchlistItem(
        watchlist_id=watchlist.id,
        symbol=symbol,
        market=payload.market,
        enabled=payload.enabled,
        timeframes=payload.timeframes,
        min_score_override=payload.min_score_override,
        enabled_patterns=payload.enabled_patterns,
        notification_channels=payload.notification_channels,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=WatchlistItemOut)
def update_stock(item_id: int, payload: WatchlistItemUpdate, db: Session = Depends(get_db)):
    item = db.get(WatchlistItem, item_id)
    if item is None:
        raise HTTPException(404, "Watchlist item not found")

    data = payload.model_dump(exclude_unset=True)
    if "enabled_patterns" in data and data["enabled_patterns"]:
        unknown = set(data["enabled_patterns"]) - set(all_pattern_keys())
        if unknown:
            raise HTTPException(422, f"Unknown pattern keys: {sorted(unknown)}")

    for field, value in data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def remove_stock(item_id: int, db: Session = Depends(get_db)):
    item = db.get(WatchlistItem, item_id)
    if item is None:
        raise HTTPException(404, "Watchlist item not found")
    db.delete(item)
    db.commit()
