"""Create all tables and seed default admin user on first run."""
from __future__ import annotations

import logging
import os

from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import Base, SessionLocal, engine
from .models import AdminUser, ForumConfig, SecretEntry

log = logging.getLogger(__name__)
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def init_db() -> None:
    """Create tables and seed default admin."""
    async with engine.begin() as conn:
        # Enable WAL for SQLite
        if "sqlite" in str(engine.url):
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=5000"))
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await _seed_admin(session)
        await _seed_forum_config(session)
        await session.commit()

    log.info("Database initialized.")


async def _seed_admin(session: AsyncSession) -> None:
    result = await session.execute(select(AdminUser))
    if result.scalars().first() is not None:
        return  # already seeded

    default_password = os.environ.get("UPBAIN_ADMIN_PASSWORD", "changeme")
    if default_password == "changeme":
        log.warning(
            "Using default admin password 'changeme'. "
            "Set UPBAIN_ADMIN_PASSWORD environment variable before production use."
        )

    user = AdminUser(
        username="admin",
        password_hash=pwd_ctx.hash(default_password),
        role="admin",
    )
    session.add(user)
    log.info("Seeded default admin user 'admin'.")


async def _seed_forum_config(session: AsyncSession) -> None:
    result = await session.execute(select(ForumConfig))
    if result.scalars().first() is not None:
        return
    session.add(ForumConfig())
