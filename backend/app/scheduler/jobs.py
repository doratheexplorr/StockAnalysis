"""
APScheduler wiring: one recurring job per monitored timeframe. Each job run
iterates every enabled watchlist item subscribed to that timeframe and
processes it through the pipeline with per-symbol error isolation - a
single bad symbol, provider timeout, or unexpected exception is logged and
skipped rather than aborting the whole cycle or crashing the process
(spec section 17).
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.database import session_scope
from app.core.logging import get_logger
from app.market_data.factory import get_market_data_provider
from app.models.enums import Timeframe
from app.models.watchlist import WatchlistItem
from app.news.factory import get_news_provider
from app.scheduler.pipeline import process_symbol_timeframe

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def _item_subscribes_to(item: WatchlistItem, timeframe: str, default_timeframes: list[str]) -> bool:
    tfs = item.timeframes or default_timeframes
    return timeframe in tfs


def run_polling_cycle(timeframe: str) -> dict:
    """Runs one polling pass for `timeframe` across the whole watchlist.
    Returns a small summary dict (useful for tests and the /status endpoint).
    """
    settings = get_settings()
    default_timeframes = [tf.strip() for tf in settings.default_timeframes.split(",") if tf.strip()]
    market_data = get_market_data_provider()
    news_provider = get_news_provider()

    processed, signals_emitted, errors = 0, 0, 0

    with session_scope() as db:
        items = db.query(WatchlistItem).filter_by(enabled=True).all()
        for item in items:
            if not _item_subscribes_to(item, timeframe, default_timeframes):
                continue
            processed += 1
            try:
                result = process_symbol_timeframe(db, item, timeframe, market_data, news_provider)
                if result.signal is not None and result.reason == "alert_emitted":
                    signals_emitted += 1
                logger.info("Processed %s/%s: %s", item.symbol, timeframe, result.reason)
            except Exception:
                # A single symbol failing (bad data, provider hiccup, unexpected
                # bug) must never take down the whole monitoring service.
                errors += 1
                logger.exception("Unhandled error processing %s/%s - continuing with next symbol", item.symbol, timeframe)

    summary = {"timeframe": timeframe, "processed": processed, "signals_emitted": signals_emitted, "errors": errors}
    logger.info("Polling cycle complete: %s", summary)
    return summary


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")

    if settings.polling_enabled:
        for tf in Timeframe:
            interval = settings.poll_interval_seconds_daily if tf == Timeframe.D1 else settings.poll_interval_seconds_intraday
            scheduler.add_job(
                run_polling_cycle,
                "interval",
                seconds=interval,
                args=[tf.value],
                id=f"poll_{tf.value}",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=interval,
            )
        scheduler.start()
        logger.info("Scheduler started with jobs for timeframes: %s", [tf.value for tf in Timeframe])
    else:
        logger.info("Polling disabled via POLLING_ENABLED=false; scheduler not started")

    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
