"""SQLAlchemy async engine, session factory and declarative base."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

_DATA_DIR = Path(os.environ.get("UPBAIN_DATA_DIR", Path(__file__).resolve().parent.parent.parent.parent / "data"))
_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{_DATA_DIR / 'upbain.db'}",
)

engine: AsyncEngine = create_async_engine(
    DB_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {},
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency: yields a database session."""
    async with SessionLocal() as session:
        yield session
