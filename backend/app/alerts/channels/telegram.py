"""Telegram notification channel via the Bot API (plain HTTPS call, no SDK)."""
from __future__ import annotations

import httpx

from app.alerts.channels.base import NotificationChannel
from app.alerts.formatter import AlertData, render_text
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import NotificationStatus

logger = get_logger(__name__)


class TelegramChannel(NotificationChannel):
    channel_type = "telegram"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.telegram_bot_token and s.telegram_chat_id)

    def send(self, alert: AlertData) -> tuple[NotificationStatus, str | None, str | None]:
        if not self.is_configured():
            return NotificationStatus.SKIPPED, "Telegram bot token/chat id not configured (see .env.example)", None

        settings = get_settings()
        text = render_text(alert)
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        try:
            resp = httpx.post(
                url,
                json={"chat_id": settings.telegram_chat_id, "text": text},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "unknown Telegram API error"))
            return NotificationStatus.SENT, None, text
        except Exception as exc:
            logger.warning("Telegram notification failed for %s: %s", alert.symbol, exc)
            return NotificationStatus.FAILED, str(exc), text
