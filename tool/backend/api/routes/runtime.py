"""Runtime control — START/STOP/scan, no mock states."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.base import get_db
from ...database.models import Job, JobStatus, TopicMapping
from ...services import job_queue
from ..deps import get_current_user, require_csrf
from ..schemas.common import ApiResponse
from ..schemas.jobs import JobOut, RunMappingRequest

log = logging.getLogger(__name__)
router = APIRouter(prefix="/runtime", tags=["runtime"])

_runtime_enabled = False


@router.get("/status", response_model=ApiResponse)
async def runtime_status(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Returns real runtime state — never mocked."""
    # Active jobs
    result = await db.execute(
        select(Job).where(Job.status.in_(["queued", "running", "waiting_flood"]))
    )
    active = result.scalars().all()

    from ...telegram.adapters import mtproto as m
    adapter = m.get_adapter()
    tg_ok = adapter is not None and adapter._connected

    return ApiResponse.success({
        "enabled": _runtime_enabled,
        "active_jobs": len(active),
        "telegram_connected": tg_ok,
        "worker_running": job_queue._worker_task is not None and not job_queue._worker_task.done(),
    })


@router.post("/start", response_model=ApiResponse)
async def start_runtime(
    _user: dict = Depends(require_csrf),
):
    global _runtime_enabled
    _runtime_enabled = True
    await job_queue.start_worker()
    return ApiResponse.success({"enabled": True})


@router.post("/stop", response_model=ApiResponse)
async def stop_runtime(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    global _runtime_enabled
    _runtime_enabled = False
    # Cancel all queued/running jobs
    result = await db.execute(
        select(Job).where(Job.status.in_(["queued", "running"]))
    )
    jobs = result.scalars().all()
    for j in jobs:
        if j.status == "running":
            j.status = JobStatus.cancelling.value
        else:
            j.status = JobStatus.cancelled.value
    await db.commit()
    return ApiResponse.success({"enabled": False, "cancelled": len(jobs)})


@router.post("/emergency-stop", response_model=ApiResponse)
async def emergency_stop(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    """Immediately cancel all jobs and stop worker."""
    global _runtime_enabled
    _runtime_enabled = False
    await job_queue.stop_worker()
    result = await db.execute(
        select(Job).where(Job.status.in_(["queued", "running", "waiting_flood", "cancelling"]))
    )
    jobs = result.scalars().all()
    for j in jobs:
        j.status = JobStatus.cancelled.value
        j.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse.success({"stopped": True, "cancelled": len(jobs)})


@router.post("/run-mapping", response_model=ApiResponse[JobOut])
async def run_mapping(
    body: RunMappingRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    result = await db.execute(
        select(TopicMapping).where(TopicMapping.id == body.mapping_id, TopicMapping.is_active == True)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    job = await job_queue.enqueue(
        db,
        job_type="run_mapping",
        payload={
            "mapping_id": body.mapping_id,
            "dry_run": body.dry_run,
            "send_cap": body.send_cap,
        },
        idempotency_key=body.idempotency_key,
        lock_key=f"mapping_{body.mapping_id}",
    )
    if job is None:
        raise HTTPException(status_code=409, detail="Job already running for this mapping (idempotency)")

    await db.commit()
    await job_queue.start_worker()
    await db.refresh(job)
    return ApiResponse.success(JobOut.from_orm(job))


@router.post("/jobs/{job_id}/cancel", response_model=ApiResponse)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    ok = await job_queue.cancel_job(db, job_id)
    await db.commit()
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or already finished")
    return ApiResponse.success({"cancelled": True})


@router.get("/jobs", response_model=ApiResponse[list[JobOut]])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
    limit: int = 50,
):
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(min(limit, 200))
    )
    jobs = result.scalars().all()
    return ApiResponse.success([JobOut.from_orm(j) for j in jobs])


@router.get("/jobs/{job_id}", response_model=ApiResponse[JobOut])
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ApiResponse.success(JobOut.from_orm(job))
