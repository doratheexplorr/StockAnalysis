"""
Structured logging setup.

Uses stdlib `logging` with an optional JSON formatter (python-json-logger).
Every module gets its own logger via `get_logger(__name__)` so log lines are
traceable to their origin. The scheduler pipeline wraps each per-symbol unit
of work so one bad symbol/provider failure is logged and swallowed rather
than crashing the whole polling loop (see app.scheduler.pipeline).
"""
from __future__ import annotations

import logging
import sys

from app.core.config import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)

    if settings.log_json:
        try:
            from pythonjsonlogger import jsonlogger

            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
        except ImportError:  # pragma: no cover - fallback if dep missing
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    handler.setFormatter(formatter)
    root.handlers = [handler]
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
