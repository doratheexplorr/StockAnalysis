"""Shared FastAPI dependencies."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import get_db  # noqa: F401  (re-exported for router imports)
from app.models.user import DEFAULT_USER_ID, User
from app.models.watchlist import Watchlist


def get_current_user_id() -> int:
    """MVP is single-user (see README "Known limitations") - always returns
    the seeded default user. Swapping in real auth later only requires
    changing this function to read from a request-scoped session/JWT."""
    return DEFAULT_USER_ID


def get_or_create_default_watchlist(db: Session, user_id: int) -> Watchlist:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email="user@example.com", display_name="Default User")
        db.add(user)
        db.flush()

    watchlist = db.query(Watchlist).filter_by(user_id=user_id).first()
    if watchlist is None:
        watchlist = Watchlist(user_id=user_id, name="My Watchlist")
        db.add(watchlist)
        db.flush()
    return watchlist
