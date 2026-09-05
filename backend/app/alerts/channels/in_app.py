"""
In-app channel: the "delivery" is simply that the Signal already exists in
the database and is served by the REST API / dashboard - there's nothing
external to call, so this always succeeds once a Signal row exists.
"""
from __future__ import annotations

from app.alerts.channels.base import NotificationChannel
from app.alerts.formatter import AlertData, render_text
from app.models.enums import NotificationStatus


class InAppChannel(NotificationChannel):
    channel_type = "in_app"

    def is_configured(self) -> bool:
        return True

    def send(self, alert: AlertData) -> tuple[NotificationStatus, str | None, str | None]:
        return NotificationStatus.SENT, None, render_text(alert)
