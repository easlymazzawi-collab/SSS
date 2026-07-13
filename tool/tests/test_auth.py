"""Auth endpoint tests — covering P0 security requirements."""
import pytest


@pytest.mark.asyncio
async def test_auth_status_unauthenticated(client):
    """Auth status returns authenticated=False without session."""
    r = await client.get("/api/auth/status")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["data"]["authenticated"] is False


@pytest.mark.asyncio
async def test_channels_fail_closed_without_auth(client):
    """Channels endpoint must return 401 without valid session."""
    r = await client.get("/api/channels")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_success(client):
    """Login with correct credentials returns session and CSRF token."""
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["data"]["username"] == "admin"
    assert "csrf_token" in data["data"]
    # Session cookie must be HttpOnly
    cookies = r.headers.get("set-cookie", "")
    assert "HttpOnly" in cookies
    assert "SameSite=strict" in cookies.lower() or "samesite=strict" in cookies.lower()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Wrong password returns 401, not 500."""
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_csrf_protection(client):
    """State-changing requests without CSRF token must return 403."""
    # Login first
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert r.status_code == 200

    # Try POST without CSRF header — must fail
    r2 = await client.post("/api/channels", json={"chat_id": -1001})
    assert r2.status_code == 403
    assert "CSRF" in r2.json().get("detail", "")


@pytest.mark.asyncio
async def test_csrf_with_valid_token(client):
    """POST with valid CSRF token must succeed."""
    from tests.conftest import get_auth_headers
    headers, csrf = await get_auth_headers(client)

    r = await client.post(
        "/api/channels",
        json={"chat_id": -1001234567890, "title": "Test"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    assert data["data"]["chat_id"] == -1001234567890


@pytest.mark.asyncio
async def test_health_returns_real_state(client):
    """Health endpoint must never return mock state."""
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"]
    h = data["data"]
    assert "backend_alive" in h
    assert "db_ready" in h
    assert "worker_ready" in h
    assert "telegram_connected" in h
    assert h["backend_alive"] is True
    # No fake "Ready" / "Armed" strings
    assert "Ready" not in str(h)
    assert "Armed" not in str(h)
    assert "Realtime local" not in str(h)


@pytest.mark.asyncio
async def test_logout(client):
    """Logout clears session and subsequent requests return 401."""
    from tests.conftest import get_auth_headers
    headers, csrf = await get_auth_headers(client)

    r_logout = await client.post("/api/auth/logout", headers=headers)
    assert r_logout.status_code == 200

    # After logout: channels must be 401
    r_channels = await client.get("/api/channels")
    assert r_channels.status_code == 401
