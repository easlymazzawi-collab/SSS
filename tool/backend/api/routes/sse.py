"""Server-Sent Events route with reconnect, heartbeat and Last-Event-ID support."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ...services import job_queue
from ..deps import get_current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/sse", tags=["sse"])

HEARTBEAT_INTERVAL = 15  # seconds


@router.get("/jobs/{job_id}")
async def job_sse(
    job_id: int,
    request: Request,
    last_event_id: str | None = None,
    _user: dict = Depends(get_current_user),
):
    """Stream job events as SSE.

    - Replays missed events via Last-Event-ID
    - Sends heartbeat every 15s
    - Reconnect-safe: client uses Last-Event-ID to resume
    - Secret-free: no tokens or API hashes in payload
    """
    q = job_queue.subscribe_sse(job_id)

    # Replay missed events if Last-Event-ID provided
    if last_event_id:
        await _replay_missed(job_id, int(last_event_id), q)

    async def generator() -> AsyncGenerator[dict, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL)
                    event_id = str(event.get("event_id", ""))
                    # Redact any secret-looking fields
                    safe = _redact(event)
                    yield {
                        "id": event_id,
                        "event": event.get("type", "message"),
                        "data": json.dumps(safe),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "{}"}
        finally:
            job_queue.unsubscribe_sse(job_id, q)

    return EventSourceResponse(generator())


async def _replay_missed(job_id: int, last_id: int, q: asyncio.Queue) -> None:
    """Load events from DB after last_id and put them in the queue."""
    from ...database.base import SessionLocal
    from ...database.models import JobEvent
    from sqlalchemy import select

    async with SessionLocal() as session:
        result = await session.execute(
            select(JobEvent)
            .where(JobEvent.job_id == job_id, JobEvent.id > last_id)
            .order_by(JobEvent.id)
            .limit(500)
        )
        events = result.scalars().all()
        for ev in events:
            payload = {"id": job_id, "type": ev.event_type, "ts": ev.created_at.isoformat(), "event_id": ev.id, **ev.data}
            try:
                q.put_nowait(_redact(payload))
            except asyncio.QueueFull:
                break


def _redact(event: dict) -> dict:
    """Remove any secret-looking keys from SSE payload."""
    sensitive = {"token", "api_hash", "api_id", "session", "password", "otp", "phone_code_hash"}
    return {k: v for k, v in event.items() if k.lower() not in sensitive}


@router.get("/logs")
async def realtime_logs(
    request: Request,
    _user: dict = Depends(get_current_user),
):
    """Stream application log entries as SSE."""
    from ...services.log_stream import subscribe_logs, unsubscribe_logs
    q = subscribe_logs()

    async def generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL)
                    yield {"event": "log", "data": json.dumps(entry)}
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "{}"}
        finally:
            unsubscribe_logs(q)

    return EventSourceResponse(generator())
