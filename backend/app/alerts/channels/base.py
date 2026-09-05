"""
Notification channel abstraction (spec section 7). Adding a new channel
(SMS, Discord, Slack, Push) means writing one class implementing `send()`
and registering it in app.alerts.notifier.CHANNEL_REGISTRY - nothing else
changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.alerts.formatter import AlertData
from app.models.enums import NotificationStatus


class NotificationChannel(ABC):
    channel_type: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this channel has the credentials/settings needed to send."""
        raise NotImplementedError

    @abstractmethod
    def send(self, alert: AlertData) -> tuple[NotificationStatus, str | None, str | None]:
        """Returns (status, error_message, rendered_message)."""
        raise NotImplementedError
