"""Topic mapping tests."""
import pytest


@pytest.mark.asyncio
async def test_mapping_crud_with_destinations(client):
    """Mapping CRUD with full destination stack saved to DB."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    # Create
    body = {
        "name": "Vitamin → Pro",
        "source_chat_id": -1001,
        "source_topic_id": 5,
        "ads_mode": "normal",
        "destinations": [
            {"dest_chat_id": -2001, "dest_topic_id": 10},
            {"dest_chat_id": -2002, "dest_topic_id": None},
        ],
    }
    r = await client.post("/api/mappings", json=body, headers=headers)
    assert r.json()["ok"]
    data = r.json()["data"]
    assert data["name"] == "Vitamin → Pro"
    assert len(data["destinations"]) == 2
    mapping_id = data["id"]

    # Get
    r2 = await client.get(f"/api/mappings/{mapping_id}")
    assert r2.json()["data"]["destinations"][0]["dest_chat_id"] == -2001

    # Update destinations (replace all with 1)
    r3 = await client.put(
        f"/api/mappings/{mapping_id}",
        json={"destinations": [{"dest_chat_id": -3001}]},
        headers=headers,
    )
    assert r3.json()["ok"], r3.json()
    assert len(r3.json()["data"]["destinations"]) == 1

    # Duplicate source should fail (409 or 500 from constraint)
    r4 = await client.post("/api/mappings", json=body, headers=headers)
    assert r4.status_code in (409, 500)  # unique constraint violation

    # Delete
    r5 = await client.delete(f"/api/mappings/{mapping_id}", headers=headers)
    assert r5.json()["ok"]


@pytest.mark.asyncio
async def test_mapping_invalid_ads_mode(client):
    """Invalid ads_mode must be rejected with 422."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    r = await client.post(
        "/api/mappings",
        json={"name": "x", "source_chat_id": -1001, "ads_mode": "invalid_mode"},
        headers=headers,
    )
    assert r.status_code == 422
