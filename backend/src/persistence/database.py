"""Lazy SQLAlchemy access to the MySQL source-of-truth database."""
from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator
from urllib.parse import quote_plus


class DatabaseUnavailable(RuntimeError):
    """Raised when relational persistence is not configured or reachable."""


def database_url() -> str:
    """Return an environment-only MySQL URL; no credentials are hard-coded."""
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    password = os.getenv("MYSQL_PASSWORD")
    if not password:
        raise DatabaseUnavailable("MYSQL_PASSWORD or DATABASE_URL is not configured.")

    user = quote_plus(os.getenv("MYSQL_USER", "patent_app"))
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "patent_intelligence")
    return f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{database}?charset=utf8mb4"


@lru_cache(maxsize=1)
def get_engine():
    try:
        from sqlalchemy import create_engine
    except ModuleNotFoundError as exc:
        raise DatabaseUnavailable("SQLAlchemy is not installed. Install backend/requirements.txt.") from exc
    return create_engine(database_url(), pool_pre_ping=True, pool_recycle=1800, future=True)


@contextmanager
def session_scope() -> Iterator[object]:
    """Yield a transaction and commit or roll it back atomically."""
    try:
        from sqlalchemy.orm import Session
    except ModuleNotFoundError as exc:
        raise DatabaseUnavailable("SQLAlchemy is not installed. Install backend/requirements.txt.") from exc

    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_database() -> None:
    """Fail fast with a useful message when the configured MySQL service is down."""
    try:
        from sqlalchemy import text
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        raise DatabaseUnavailable(f"MySQL is unavailable: {exc}") from exc
