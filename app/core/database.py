import os
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import create_engine, event, Column, Integer, DateTime, func, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.engine import Engine
from app.core.config import settings
from app.core.logging import logger


# Engine configuration switchable between SQLite and MySQL
connect_args = {}
engine_kwargs = {
    "echo": False,
}

if settings.is_sqlite:
    # SQLite connection configuration
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    # Production MySQL / PostgreSQL connection pooling settings
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 3600
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)


# Enable SQLite Foreign Keys and WAL Mode for performance and integrity
if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DeclarativeBaseModel = declarative_base()


class Base(DeclarativeBaseModel):
    """
    Abstract base model providing standard ID, created_at, and updated_at
    timestamps compatible across SQLite and MySQL.
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session."""
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verifies that the database engine can successfully execute a query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database connection health check failed: {exc}")
        return False
