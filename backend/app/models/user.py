from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

DEFAULT_USER_ID = 1


class User(Base, TimestampMixin):
    """Minimal user record.

    The MVP runs as a single-user local application (per README "Known
    limitations") but is modeled with a Users table from the start so
    multi-user auth can be added later without a schema migration for
    every downstream table (watchlists, preferences, etc. all carry a
    user_id).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="Default User")

    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship(
        "NotificationPreference", back_populates="user", cascade="all, delete-orphan"
    )
