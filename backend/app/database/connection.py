"""
Async SQLAlchemy engine, session factory, and dependency injection.
Handles both PostgreSQL (asyncpg) and SQLite (aiosqlite) URLs.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect, text
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.config import settings


def _build_engine_kwargs(url: str) -> dict:
    """Return engine kwargs appropriate for the database backend."""
    kwargs: dict = {
        "echo": False,
    }
    if url.startswith("sqlite"):
        # SQLite doesn't support pool-based concurrency well in async mode
        kwargs["poolclass"] = NullPool
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL – use a proper connection pool
        kwargs["poolclass"] = AsyncAdaptedQueuePool
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
        kwargs["pool_pre_ping"] = True
    return kwargs


engine = create_async_engine(
    settings.DATABASE_URL,
    **_build_engine_kwargs(settings.DATABASE_URL),
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create ORM tables and apply small, backward-compatible schema upgrades."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_confirmed_at_if_missing)


def _add_confirmed_at_if_missing(connection) -> None:
    """Add the confirmation timestamp to databases created by earlier releases."""
    inspector = inspect(connection)
    if "voice_statements" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("voice_statements")}
    if "confirmed_at" in columns:
        return
    column_type = "DATETIME" if connection.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"
    connection.execute(text(f"ALTER TABLE voice_statements ADD COLUMN confirmed_at {column_type}"))
