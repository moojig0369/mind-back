"""
Infrastructure database connection and session management.
Async SQLAlchemy with Supabase PostgreSQL.
"""

from functools import lru_cache
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from app.core.settings import get_settings


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self._engine = None
        self._session_maker = None
    
    def init(self, database_url: str):
        """Initialize database engine and session maker."""
        self._engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    @property
    def engine(self):
        if self._engine is None:
            raise RuntimeError("Database not initialized")
        return self._engine
    
    @property
    def session_maker(self):
        if self._session_maker is None:
            raise RuntimeError("Database not initialized")
        return self._session_maker
    
    async def close(self):
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()


# Global database instance
db = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes to get DB session."""
    session = db.session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def init_database(database_url: str):
    """Initialize database connection from settings."""
    # Database URL should already be properly formatted
    # If it's a Supabase URL, convert to PostgreSQL async URL
    if "supabase.co" in database_url and not database_url.startswith("postgresql"):
        # This case should not happen if using Settings.database_url
        # But handle it for backward compatibility
        db_host = database_url.replace("https://", "").replace(".supabase.co", "")
        settings = get_settings()
        database_url = (
            f"postgresql+asyncpg://postgres:{settings.supabase_key}@"
            f"{db_host}.pooler.supabase.com:6543/postgres"
        )
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
    
    db.init(database_url)
