"""Pytest configuration and shared fixtures."""
import asyncio
import os
import pytest
import pytest_asyncio

# Use in-memory SQLite for tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("UPBAIN_SECRET_KEY", "test-key-insecure")
os.environ.setdefault("UPBAIN_ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("UPBAIN_DATA_DIR", "/tmp/upbain-test")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db():
    """Fresh in-memory DB per test."""
    from backend.database.base import Base, engine, SessionLocal
    from backend.database.init_db import init_db
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await init_db()
    
    async with SessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client():
    """HTTPX async test client for FastAPI."""
    from httpx import AsyncClient, ASGITransport
    from backend.app import app
    from backend.database.base import Base, engine
    from backend.database.init_db import init_db

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_auth_headers(client) -> tuple[dict, str]:
    """Login and return (cookie_dict, csrf_token)."""
    # Clear rate limit for tests
    import backend.services.auth_service as auth_svc
    auth_svc._rate_limit.clear()
    
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["ok"]
    csrf = data["data"]["csrf_token"]
    return {"X-CSRF-Token": csrf}, csrf
