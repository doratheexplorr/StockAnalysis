"""FastAPI application entrypoint.

Layering (see README "Architecture"):
    Frontend -> REST API (this module + app.api.routers.*) -> Analysis/Signal
    Engine (app.scoring, app.patterns, app.indicators) -> Market Data Layer
    (app.market_data) -> Database (app.models)

The scheduler (app.scheduler.jobs) that continuously polls the watchlist
runs in the same process as the API for the MVP (started/stopped via the
lifespan hook below) - see README "Known limitations" for why a separate
worker process is the natural next step for real production deployment.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import alerts, market_data, settings as settings_router, signals, status, watchlist
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger
from app.scheduler.jobs import start_scheduler, stop_scheduler

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    init_db()
    logger.info("%s starting up (env=%s, provider=%s)", settings.app_name, settings.environment, settings.market_data_provider)
    if settings.environment != "test":
        start_scheduler()
    yield
    stop_scheduler()
    logger.info("%s shutting down", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    origins = [o.strip() for o in settings.api_cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(watchlist.router)
    app.include_router(signals.router)
    app.include_router(alerts.router)
    app.include_router(settings_router.router)
    app.include_router(status.router)
    app.include_router(market_data.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
