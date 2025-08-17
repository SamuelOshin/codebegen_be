# Database connection and session management
"""
SQLAlchemy engine setup, session factory, and dependency injection.
Handles database connections and session lifecycle.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, AsyncGenerator

from app.core.config import settings
from app.models.base import Base

# Create sync engine and session factory (for migrations)
sync_engine = create_engine(
    settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"),
    # PostgreSQL specific settings
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Create async engine and session factory (for app)
async_engine = create_async_engine(
    settings.async_database_url,
    # PostgreSQL specific settings
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session (sync)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_session() -> AsyncSession:
    """Get a new database session for background tasks"""
    return AsyncSessionLocal()


def create_tables():
    """Create all tables (for development/testing)"""
    Base.metadata.create_all(bind=sync_engine)


def drop_tables():
    """Drop all tables (for testing)"""
    Base.metadata.drop_all(bind=sync_engine)

__all__ = [
    "sync_engine",
    "SessionLocal",
    "async_engine",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "get_db_session",
    "create_tables",
    "drop_tables",
    "Base",
]

