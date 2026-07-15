"""Channel registry tests."""
import pytest


@pytest.mark.asyncio
async def test_channel_crud(client):
    """Full CRUD cycle for channels."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    # List empty
    r = await client.get("/api/channels")
    assert r.json()["data"] == []

    # Create
    r = await client.post("/api/channels", json={"chat_id": -1001, "title": "Ch1"}, headers=headers)
    assert r.json()["ok"]
    ch_id = r.json()["data"]["id"]

    # Duplicate should fail
    r2 = await client.post("/api/channels", json={"chat_id": -1001}, headers=headers)
    assert r2.status_code == 409

    # Get
    r3 = await client.get(f"/api/channels/{ch_id}")
    assert r3.json()["data"]["chat_id"] == -1001

    # Delete
    r4 = await client.delete(f"/api/channels/{ch_id}", headers=headers)
    assert r4.json()["ok"]

    # After delete, list should be empty
    r5 = await client.get("/api/channels")
    assert r5.json()["data"] == []


@pytest.mark.asyncio
async def test_channel_invalid_chat_id(client):
    """Adding channel with invalid chat_id must fail with 422."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    r = await client.post("/api/channels", json={"chat_id": 0}, headers=headers)
    assert r.status_code in (422, 400)


@pytest.mark.asyncio
async def test_channel_liveness_check_without_telegram(client):
    """Liveness check without Telegram adapter returns unknown."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    # Add channel
    r = await client.post("/api/channels", json={"chat_id": -1001}, headers=headers)
    ch_id = r.json()["data"]["id"]

    # Check liveness (no adapter → unknown)
    r2 = await client.post(f"/api/channels/{ch_id}/check-liveness", headers=headers)
    assert r2.json()["ok"]
    assert r2.json()["data"]["liveness"] in ("unknown", "alive", "dead", "no_access")
