"""SQLite-backed durable async job queue.

- Polls DB every 1s when idle
- Respects not_before (FloodWait deadline)
- One job running per lock_key
- Resume from last successful job_item checkpoint after restart
- SSE via asyncio.Queue per job connection
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Coroutine, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.base import SessionLocal
from ..database.models import Job, JobEvent, JobItem, JobStatus

log = logging.getLogger(__name__)

# SSE listeners: job_id → set of asyncio.Queue
_sse_queues: dict[int, set[asyncio.Queue]] = {}

# Registered job handlers: job_type → async callable
_handlers: dict[str, Callable[..., Coroutine]] = {}

_worker_task: Optional[asyncio.Task] = None


def register_handler(job_type: str):
    """Decorator to register a job handler."""
    def decorator(fn: Callable):
        _handlers[job_type] = fn
        return fn
    return decorator


def subscribe_sse(job_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    _sse_queues.setdefault(job_id, set()).add(q)
    return q


def unsubscribe_sse(job_id: int, q: asyncio.Queue) -> None:
    if job_id in _sse_queues:
        _sse_queues[job_id].discard(q)


async def emit_event(job_id: int, event_type: str, data: dict) -> None:
    """Persist event to DB and broadcast to SSE subscribers."""
    async with SessionLocal() as session:
        event = JobEvent(job_id=job_id, event_type=event_type, data=data)
        session.add(event)
        await session.commit()

    payload = {"id": job_id, "type": event_type, "ts": datetime.now(timezone.utc).isoformat(), **data}
    for q in list(_sse_queues.get(job_id, set())):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def enqueue(
    session: AsyncSession,
    job_type: str,
    payload: dict,
    *,
    idempotency_key: Optional[str] = None,
    lock_key: Optional[str] = None,
    not_before: Optional[datetime] = None,
) -> Optional[Job]:
    """Create a job. Returns None if idempotency_key already exists."""
    if idempotency_key:
        existing = await session.execute(
            select(Job).where(Job.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            return None

    job = Job(
        job_type=job_type,
        payload=payload,
        idempotency_key=idempotency_key,
        lock_key=lock_key,
        not_before=not_before,
        status=JobStatus.queued.value,
    )
    session.add(job)
    await session.flush()
    return job


async def cancel_job(session: AsyncSession, job_id: int) -> bool:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return False
    if job.status in (JobStatus.succeeded.value, JobStatus.failed.value, JobStatus.cancelled.value):
        return False
    if job.status == JobStatus.running.value:
        job.status = JobStatus.cancelling.value
    else:
        job.status = JobStatus.cancelled.value
    await session.flush()
    await emit_event(job_id, "cancelled", {"status": job.status})
    return True


async def _run_worker_loop() -> None:
    log.info("Job worker started.")
    while True:
        try:
            await _pick_and_run()
        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Unexpected error in worker loop")
        await asyncio.sleep(1)


async def _pick_and_run() -> None:
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        # Pick one queued job that is not flood-waiting and lock_key not busy
        result = await session.execute(
            select(Job)
            .where(
                Job.status == JobStatus.queued.value,
            )
            .order_by(Job.created_at)
            .limit(20)
        )
        candidates = result.scalars().all()

        # Filter by not_before and lock_key
        running_locks_result = await session.execute(
            select(Job.lock_key).where(Job.status == JobStatus.running.value)
        )
        running_locks = {r for (r,) in running_locks_result if r}

        job: Optional[Job] = None
        for candidate in candidates:
            if candidate.not_before and candidate.not_before > now:
                continue
            if candidate.lock_key and candidate.lock_key in running_locks:
                continue
            job = candidate
            break

        if job is None:
            return

        job.status = JobStatus.running.value
        job.started_at = now
        await session.commit()
        job_id = job.id
        job_type = job.job_type
        payload = job.payload

    handler = _handlers.get(job_type)
    if handler is None:
        log.error("No handler for job type %s (job %d)", job_type, job_id)
        async with SessionLocal() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(status=JobStatus.failed.value, error=f"No handler for {job_type}")
            )
            await session.commit()
        return

    try:
        ctx = JobContext(job_id=job_id, payload=payload)
        await handler(ctx)
        async with SessionLocal() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            j = result.scalar_one()
            if j.status not in (JobStatus.cancelled.value, JobStatus.cancelling.value):
                # Check for partial failures
                items_result = await session.execute(
                    select(JobItem).where(
                        JobItem.job_id == job_id,
                        JobItem.status.in_(["failed_permanent", "failed_transient"]),
                    )
                )
                failed_items = items_result.scalars().all()
                if failed_items:
                    j.status = JobStatus.partially_failed.value
                else:
                    j.status = JobStatus.succeeded.value
            elif j.status == JobStatus.cancelling.value:
                j.status = JobStatus.cancelled.value
            j.finished_at = datetime.now(timezone.utc)
            await session.commit()
        await emit_event(job_id, "finished", {"status": JobStatus.succeeded.value})
    except asyncio.CancelledError:
        async with SessionLocal() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(status=JobStatus.cancelled.value, finished_at=datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception as exc:
        log.exception("Job %d failed", job_id)
        async with SessionLocal() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status=JobStatus.failed.value,
                    error=str(exc),
                    finished_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
        await emit_event(job_id, "failed", {"error": str(exc)})


class JobContext:
    """Passed to job handlers; provides progress reporting and cancellation check."""

    def __init__(self, job_id: int, payload: dict) -> None:
        self.job_id = job_id
        self.payload = payload
        self._cancelled = False

    async def is_cancelled(self) -> bool:
        async with SessionLocal() as session:
            result = await session.execute(select(Job).where(Job.id == self.job_id))
            job = result.scalar_one_or_none()
            if job and job.status in (JobStatus.cancelling.value, JobStatus.cancelled.value):
                self._cancelled = True
        return self._cancelled

    async def report_progress(self, done: int, total: int, msg: str = "") -> None:
        pct = round(done / max(total, 1) * 100, 1)
        await emit_event(self.job_id, "progress", {"done": done, "total": total, "pct": pct, "msg": msg})
        async with SessionLocal() as session:
            await session.execute(
                update(Job)
                .where(Job.id == self.job_id)
                .values(progress={"done": done, "total": total, "pct": pct})
            )
            await session.commit()

    async def persist_flood_wait(self, wait_seconds: int, source: str = "") -> None:
        """Store FloodWait deadline so worker respects it after restart."""
        from datetime import timedelta
        not_before = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds + 2)
        async with SessionLocal() as session:
            await session.execute(
                update(Job)
                .where(Job.id == self.job_id)
                .values(
                    status=JobStatus.queued.value,
                    not_before=not_before,
                )
            )
            await session.commit()
        await emit_event(
            self.job_id, "flood_wait",
            {"wait_seconds": wait_seconds, "not_before": not_before.isoformat(), "source": source}
        )


async def start_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_run_worker_loop())
    log.info("Job worker task created.")


async def stop_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    log.info("Job worker stopped.")
