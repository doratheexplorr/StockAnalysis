from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class SystemConfiguration(Base, TimestampMixin):
    """Generic key/value store for runtime-editable configuration.

    Deliberately schemaless (JSON value) so new config knobs (scoring
    weights, thresholds, enabled patterns/timeframes...) can be added
    without a migration. See app.scoring.config for the keys this table is
    expected to hold and their defaults/validation.
    """

    __tablename__ = "system_configuration"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class NotificationPreference(Base, TimestampMixin):
    """Per-user, per-channel notification configuration.

    Channel-specific secrets (SMTP password, Telegram bot token) live in
    environment variables (app.core.config.Settings), never here - this
    table only stores which channels are enabled and non-secret per-channel
    overrides (e.g. a specific Telegram chat_id if different from the
    global default).
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "channel", name="uq_user_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))  # NotificationChannelType value
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # non-secret overrides only

    user = relationship("User", back_populates="notification_preferences")
