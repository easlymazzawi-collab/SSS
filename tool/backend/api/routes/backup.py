"""Backup, restore and data management routes."""
from __future__ import annotations

import hashlib
import io
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.base import get_db, DB_URL
from ...database.models import BackupRecord
from ..deps import require_csrf, get_current_user
from ..schemas.common import ApiResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/backup", tags=["backup"])

_DATA_DIR = Path(os.environ.get("UPBAIN_DATA_DIR", Path(__file__).resolve().parents[4] / "data"))
_BACKUP_DIR = _DATA_DIR / "backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Session files are EXCLUDED from backup
_EXCLUDE_PATTERNS = {".session", ".session-journal"}


def _is_safe_path(zip_path: str) -> bool:
    """Reject paths with traversal or absolute paths."""
    p = Path(zip_path)
    return not p.is_absolute() and ".." not in p.parts


@router.post("/run-now", response_model=ApiResponse)
async def backup_now(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    """Create a backup zip (excludes session files)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"upbain_backup_{ts}.zip"
    dest = _BACKUP_DIR / filename

    # Collect files to backup (exclude sessions)
    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # DB file
            db_path = _DATA_DIR / "upbain.db"
            if db_path.exists():
                zf.write(db_path, "upbain.db")

            # Config files (json/txt but not sessions)
            for f in _DATA_DIR.rglob("*"):
                if f.is_file() and not any(f.name.endswith(p) for p in _EXCLUDE_PATTERNS):
                    rel = f.relative_to(_DATA_DIR)
                    zf.write(f, str(rel))

        buf.seek(0)
        data = buf.read()
        dest.write_bytes(data)

        sha256 = hashlib.sha256(data).hexdigest()
        record = BackupRecord(
            filename=filename,
            size_bytes=len(data),
            sha256=sha256,
            status="ok",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        return ApiResponse.success({
            "filename": filename,
            "size_bytes": len(data),
            "sha256": sha256[:16] + "...",
            "path": str(dest),
        })
    except Exception as e:
        log.exception("Backup failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ApiResponse)
async def list_backups(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(50)
    )
    records = result.scalars().all()
    return ApiResponse.success([
        {
            "id": r.id,
            "filename": r.filename,
            "size_bytes": r.size_bytes,
            "sha256_prefix": r.sha256[:16] + "..." if r.sha256 else None,
            "created_at": r.created_at.isoformat(),
            "status": r.status,
        }
        for r in records
    ])


@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    _user: dict = Depends(get_current_user),
):
    """Download a backup file. Validates path to prevent traversal."""
    # Sanitize filename
    safe_name = Path(filename).name  # strips any directory components
    if not safe_name.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = _BACKUP_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(path, media_type="application/zip", filename=safe_name)


@router.post("/restore")
async def restore_backup(
    file: UploadFile,
    _user: dict = Depends(require_csrf),
):
    """Restore from uploaded backup zip. Validates entries for zip-slip."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Must upload a .zip file")

    MAX_SIZE = 100 * 1024 * 1024  # 100 MB
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for entry in zf.infolist():
                if not _is_safe_path(entry.filename):
                    raise HTTPException(status_code=400, detail=f"Unsafe path in zip: {entry.filename}")
                if entry.file_size > 50 * 1024 * 1024:
                    raise HTTPException(status_code=400, detail="Zip entry too large (zip bomb check)")

            # Extract to data dir (overwrite)
            for entry in zf.infolist():
                if entry.filename.endswith(".session"):
                    continue  # Never restore session files
                target = _DATA_DIR / entry.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(entry.filename))

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")

    return ApiResponse.success({"restored": True})
