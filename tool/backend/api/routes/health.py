"""Health endpoint — real status, never mock."""
from __future__ import annotations

import platform
import time
from datetime import datetime, timezone
from typing import Optional

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ...database.base import get_db
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.time()


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Returns real system and component health. Never returns mock state."""
    db_ok = await _check_db(db)
    tg_connected = _check_telegram()

    return ApiResponse.success({
        "backend_alive": True,
        "db_ready": db_ok,
        "worker_ready": _check_worker(),
        "telegram_connected": tg_connected["connected"],
        "telegram_username": tg_connected["username"],
        "degraded": not db_ok,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "machine": _machine_stats(),
    })


async def _check_db(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_worker() -> bool:
    from ...services import job_queue
    task = job_queue._worker_task
    return task is not None and not task.done()


def _check_telegram() -> dict:
    from ...telegram.adapters import mtproto
    adapter = mtproto.get_adapter()
    if adapter is None:
        return {"connected": False, "username": None}
    try:
        return {"connected": adapter._connected, "username": None}
    except Exception:
        return {"connected": False, "username": None}


def _machine_stats() -> dict:
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_pct": cpu,
            "ram_used_mb": round(mem.used / 1024 / 1024, 1),
            "ram_total_mb": round(mem.total / 1024 / 1024, 1),
            "disk_used_gb": round(disk.used / 1024**3, 2),
            "disk_total_gb": round(disk.total / 1024**3, 2),
        }
    except Exception:
        return {}
