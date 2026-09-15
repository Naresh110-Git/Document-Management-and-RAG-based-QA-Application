"""Async SQLAlchemy engine and session helpers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

from sqlalchemy import event
from sqlalchemy.pool import NullPool

settings = get_settings()

is_sqlite = bool(settings.database_url and "sqlite" in settings.database_url)

engine_kwargs = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {"timeout": 60, "check_same_thread": False}
elif settings.database_url and settings.database_url.startswith("postgresql"):
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=60000")
            cursor.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        finally:
            cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session with rollback on errors."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
