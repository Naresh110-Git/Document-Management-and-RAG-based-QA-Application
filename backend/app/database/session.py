"""Async SQLAlchemy engine and session helpers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    # Pool sizing options are not compatible with all dialects (e.g. SQLite memory).
    # Only pass them when using a production-ready DB (Postgres). For tests using
    # in-memory SQLite, these kwargs cause errors, so guard them.
    **({
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
    } if settings.database_url and settings.database_url.startswith("postgresql") else {}),
)

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
