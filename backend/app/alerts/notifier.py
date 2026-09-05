"""
Dispatches a scored signal to every enabled, configured notification
channel and records the outcome in `AlertHistory` - independent of the
analysis/scoring engine (spec section 10 "Notification Service should be
independent of the analysis engine") so a notification failure can never
affect signal generation, and vice versa.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.alerts.channels.base import NotificationChannel
from app.alerts.channels.email import EmailChannel
from app.alerts.channels.in_app import InAppChannel
from app.alerts.channels.telegram import TelegramChannel
from app.alerts.formatter import AlertData
from app.core.logging import get_logger
from app.models.alert import AlertHistory
from app.models.enums import NotificationChannelType, NotificationStatus
from app.models.signal import Signal

logger = get_logger(__name__)

CHANNEL_REGISTRY: dict[str, NotificationChannel] = {
    NotificationChannelType.IN_APP.value: InAppChannel(),
    NotificationChannelType.EMAIL.value: EmailChannel(),
    NotificationChannelType.TELEGRAM.value: TelegramChannel(),
    # SMS / Discord / Slack / Push: add an adapter + one entry here (spec section 7)
}


def dispatch_signal(
    db: Session, signal: Signal, alert: AlertData, enabled_channels: list[str]
) -> list[AlertHistory]:
    records: list[AlertHistory] = []
    for channel_key in enabled_channels:
        channel = CHANNEL_REGISTRY.get(channel_key)
        if channel is None:
            logger.warning("Unknown notification channel '%s' requested for signal %s", channel_key, signal.id)
            continue
        try:
            status, error, rendered = channel.send(alert)
        except Exception as exc:  # a single channel failing must never affect the others or the signal itself
            logger.exception("Notification channel '%s' raised unexpectedly", channel_key)
            status, error, rendered = NotificationStatus.FAILED, str(exc), None

        record = AlertHistory(
            signal_id=signal.id,
            channel=channel_key,
            status=status.value,
            sent_at=dt.datetime.now(dt.timezone.utc) if status == NotificationStatus.SENT else None,
            error_message=error,
            rendered_message=rendered,
        )
        db.add(record)
        records.append(record)

    db.commit()
    return records
