"""Job queue tests — cancel, resume, FloodWait persist."""
import asyncio
import pytest


@pytest.mark.asyncio
async def test_job_enqueue_and_cancel(db):
    """Enqueue a job and cancel it."""
    from backend.services.job_queue import enqueue, cancel_job
    from backend.database.models import Job, JobStatus

    # Enqueue
    job = await enqueue(db, "test_job", {"x": 1}, idempotency_key="test-idem-1")
    assert job is not None
    await db.commit()

    # Cancel
    ok = await cancel_job(db, job.id)
    await db.commit()
    assert ok

    await db.refresh(job)
    assert job.status == JobStatus.cancelled.value


@pytest.mark.asyncio
async def test_job_idempotency(db):
    """Same idempotency key should not create duplicate job."""
    from backend.services.job_queue import enqueue

    j1 = await enqueue(db, "test_job", {}, idempotency_key="unique-key")
    await db.commit()
    j2 = await enqueue(db, "test_job", {}, idempotency_key="unique-key")
    await db.commit()

    assert j1 is not None
    assert j2 is None  # duplicate rejected


@pytest.mark.asyncio
async def test_job_flood_wait_persist(db):
    """FloodWait persists not_before timestamp."""
    from backend.services.job_queue import enqueue, JobContext
    from backend.database.models import Job
    from backend.database.base import SessionLocal
    from sqlalchemy import select

    job = await enqueue(db, "flood_test", {})
    await db.commit()
    job_id = job.id

    ctx = JobContext(job_id=job_id, payload={})
    await ctx.persist_flood_wait(60, source="test")

    # Use a fresh session to avoid cache
    async with SessionLocal() as fresh:
        result = await fresh.execute(select(Job).where(Job.id == job_id))
        j = result.scalar_one()
        assert j.not_before is not None


@pytest.mark.asyncio
async def test_secret_store_encrypt_decrypt(db):
    """Secret store encrypts and never stores plaintext."""
    from backend.services.secret_store import SecretStore
    from backend.database.models import SecretEntry
    from sqlalchemy import select

    store = SecretStore(db)
    await store.set("test_secret", "my_super_secret_value")
    await db.commit()

    # Value is encrypted in DB (not plaintext)
    result = await db.execute(select(SecretEntry).where(SecretEntry.key == "test_secret"))
    entry = result.scalar_one()
    assert "my_super_secret_value" not in str(entry.encrypted_value)

    # Decrypt returns original
    val = await store.get("test_secret")
    assert val == "my_super_secret_value"

    # Status returns fingerprint only
    status = await store.status("test_secret")
    assert status["configured"] is True
    assert status["fingerprint"] is not None
    assert "my_super_secret" not in status["fingerprint"]

    # Delete
    ok = await store.delete("test_secret")
    assert ok
    val2 = await store.get("test_secret")
    assert val2 is None


@pytest.mark.asyncio
async def test_fake_mtproto_album_and_flood():
    """Fake MTProto adapter simulates album and FloodWait injection."""
    from backend.telegram.fake.fake_mtproto import FakeMTProtoAdapter, FakeMessage

    adapter = FakeMTProtoAdapter()
    assert await adapter.is_user_authorized()

    # Add messages
    adapter.add_messages(123, [
        FakeMessage(1, "msg 1"),
        FakeMessage(2, "msg 2"),
        FakeMessage(3, "msg 3"),
    ])

    collected = []
    async for msg in adapter.iter_messages(123, min_id=0):
        collected.append(msg.id)
    assert collected == [1, 2, 3]

    # Forward without flood
    result = await adapter.forward_messages(123, [1, 2], 456)
    assert len(result) == 2
    assert len(adapter.get_sent()) == 2

    # Test flood wait injection
    from telethon.errors import FloodWaitError
    adapter.flood_wait_seconds = 30
    with pytest.raises(FloodWaitError):
        await adapter.forward_messages(123, [3], 456)
