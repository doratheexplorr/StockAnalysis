"""Import every model module so `Base.metadata` sees all tables.

Anything added to app/models/*.py must be imported here (or from a module
imported here) or it will silently be missing from `init_db()` /
alembic autogenerate.
"""
from app.models.user import User  # noqa: F401
from app.models.watchlist import Watchlist, WatchlistItem  # noqa: F401
from app.models.detection import CandlestickDetection  # noqa: F401
from app.models.indicator_snapshot import IndicatorSnapshot  # noqa: F401
from app.models.signal import Signal  # noqa: F401
from app.models.alert import AlertHistory  # noqa: F401
from app.models.news_cache import NewsCacheItem  # noqa: F401
from app.models.config import SystemConfiguration, NotificationPreference  # noqa: F401
