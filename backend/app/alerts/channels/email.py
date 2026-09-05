"""Email notification channel via SMTP (stdlib smtplib - no extra dependency)."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from app.alerts.channels.base import NotificationChannel
from app.alerts.formatter import AlertData, render_summary, render_text
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import NotificationStatus

logger = get_logger(__name__)


class EmailChannel(NotificationChannel):
    channel_type = "email"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.smtp_host and s.alert_email_from and s.alert_email_to)

    def send(self, alert: AlertData) -> tuple[NotificationStatus, str | None, str | None]:
        if not self.is_configured():
            return NotificationStatus.SKIPPED, "SMTP not configured (see .env.example)", None

        settings = get_settings()
        body = render_text(alert)
        message = MIMEText(body, "plain")
        message["Subject"] = f"[{alert.classification.upper()}] {render_summary(alert)}"
        message["From"] = settings.alert_email_from
        message["To"] = settings.alert_email_to

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.alert_email_from, [settings.alert_email_to], message.as_string())
            return NotificationStatus.SENT, None, body
        except Exception as exc:
            logger.warning("Email notification failed for %s: %s", alert.symbol, exc)
            return NotificationStatus.FAILED, str(exc), body
