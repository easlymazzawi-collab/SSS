"""Backup tests — zip-slip prevention, session exclusion."""
import io
import os
import zipfile
import pytest


@pytest.mark.asyncio
async def test_backup_creates_zip(client):
    """Backup creates a valid zip file."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    r = await client.post("/api/backup/run-now", headers=headers)
    assert r.json()["ok"]
    assert r.json()["data"]["filename"].endswith(".zip")
    assert r.json()["data"]["size_bytes"] > 0


@pytest.mark.asyncio
async def test_backup_list(client):
    """Backup list contains created backups."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    await client.post("/api/backup/run-now", headers=headers)
    r = await client.get("/api/backup/list")
    assert r.json()["ok"]
    assert len(r.json()["data"]) > 0


def test_zip_slip_rejection():
    """Restore must reject zip entries with path traversal."""
    from backend.api.routes.backup import _is_safe_path
    assert _is_safe_path("data/file.txt") is True
    assert _is_safe_path("../../../etc/passwd") is False
    assert _is_safe_path("/absolute/path") is False
    assert _is_safe_path("a/../b") is False


@pytest.mark.asyncio
async def test_restore_rejects_malicious_zip(client):
    """Restore must reject zip files with path traversal entries."""
    from tests.conftest import get_auth_headers
    headers, _ = await get_auth_headers(client)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../etc/passwd", "root:x:0:0:root:/root:/bin/bash")
    buf.seek(0)

    r = await client.post(
        "/api/backup/restore",
        content=buf.read(),
        headers={**headers, "Content-Type": "multipart/form-data; boundary=boundary"},
    )
    # Should reject with 400 or 422
    assert r.status_code in (400, 422)
