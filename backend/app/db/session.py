"""Database session and connection management."""

import logging
import time
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.exc import OperationalError, DatabaseError

from backend.app.core.config import settings
from backend.app.db.models import Base

logger = logging.getLogger(__name__)

# Determine if running with SQLite (for tests) or PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}
pool_kwargs = {} if is_sqlite else {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **pool_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def _create_sqlite_fallback() -> None:
    """Seamlessly reconfigure database engine to use local SQLite when PostgreSQL is offline."""
    global engine, SessionLocal, is_sqlite
    logger.info("Activating seamless local SQLite database fallback (lenny_growth_local.db)...")
    is_sqlite = True
    engine = create_engine(
        "sqlite:///./lenny_growth_local.db",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    logger.info("Local SQLite database initialized successfully.")


def get_db() -> Generator[SQLAlchemySession, None, None]:
    """FastAPI dependency yielding a scoped database session with seamless fallback."""
    global engine, SessionLocal
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
    except Exception as err:
        logger.warning("Database connection error before route (%s). Activating local SQLite fallback.", err)
        _create_sqlite_fallback()
        db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    """Execute a simple query to verify database reachability."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as err:
        logger.warning("Database ping failed: %s", err)
        return False


def init_db(max_retries: int = 5, initial_backoff: float = 1.0) -> None:
    """Create tables with exponential backoff retry.
    Falls back to local SQLite if PostgreSQL is unreachable."""
    global engine, SessionLocal
    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Initializing database tables (attempt %d/%d)...", attempt, max_retries)
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully.")
            return
        except (OperationalError, DatabaseError) as err:
            if attempt == max_retries:
                if not is_sqlite:
                    logger.warning(
                        "PostgreSQL is offline (%s). Seamlessly activating local SQLite persistence fallback.",
                        err,
                    )
                    _create_sqlite_fallback()
                    return
                logger.error("Max database initialization retries (%d) reached: %s", max_retries, err)
                raise
            logger.warning(
                "Database initialization attempt %d failed (%s). Retrying in %.1fs...",
                attempt,
                err,
                backoff,
            )
            time.sleep(backoff)
            backoff *= 2
