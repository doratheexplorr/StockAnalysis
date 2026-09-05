from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AlertHistory(Base, TimestampMixin):
    """Record of every attempted notification delivery for a signal.

    One row per (signal, channel) delivery attempt. Kept even on failure so
    the Settings/alert-history UI can show delivery problems (e.g. bad SMTP
    creds) without them being silently swallowed.
    """

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)

    channel: Mapped[str] = mapped_column(String(20))  # NotificationChannelType value
    status: Mapped[str] = mapped_column(String(20))  # NotificationStatus value
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    signal = relationship("Signal", back_populates="alert_history")
