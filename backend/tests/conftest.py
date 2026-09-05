from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine, init_db


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    init_db()
    yield


@pytest.fixture()
def db():
    """A clean database session for each test: every table is emptied
    before the test runs so tests don't leak state into each other, while
    still using a real (file-based) SQLite engine so behaviour matches
    production SQLAlchemy semantics (unlike pure in-memory mocks)."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
