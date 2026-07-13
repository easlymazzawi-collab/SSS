"""Channel registry routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.base import get_db
from ...database.models import Channel
from ..deps import get_current_user, require_csrf
from ..schemas.channels import ChannelCreate, ChannelMetaUpdate, ChannelOut
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=ApiResponse[List[ChannelOut]])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Channel).where(Channel.is_deleted == False).order_by(Channel.created_at.desc())
    )
    channels = result.scalars().all()
    return ApiResponse.success([ChannelOut.from_orm(c) for c in channels])


@router.post("", response_model=ApiResponse[ChannelOut])
async def add_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    # Validate chat_id
    if not isinstance(body.chat_id, int) or body.chat_id == 0:
        raise HTTPException(status_code=422, detail="Invalid chat_id")

    existing = await db.execute(
        select(Channel).where(Channel.chat_id == body.chat_id, Channel.is_deleted == False)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Channel already exists")

    channel = Channel(
        chat_id=body.chat_id,
        username=body.username,
        title=body.title,
        liveness="unknown",
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return ApiResponse.success(ChannelOut.from_orm(channel))


@router.get("/{channel_id}", response_model=ApiResponse[ChannelOut])
async def get_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ApiResponse.success(ChannelOut.from_orm(channel))


@router.patch("/{channel_id}/meta", response_model=ApiResponse[ChannelOut])
async def update_channel_meta(
    channel_id: int,
    body: ChannelMetaUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    update_data = body.model_dump(exclude_none=True)
    for k, v in update_data.items():
        setattr(channel, k, v)
    await db.commit()
    await db.refresh(channel)
    return ApiResponse.success(ChannelOut.from_orm(channel))


@router.post("/{channel_id}/check-liveness", response_model=ApiResponse)
async def check_channel_liveness(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    from ...telegram.adapters import mtproto as m
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    adapter = m.get_adapter()
    if adapter is None:
        channel.liveness = "unknown"
    else:
        liveness = await adapter.check_channel_liveness(channel.chat_id)
        channel.liveness = liveness
        channel.liveness_checked_at = datetime.now(timezone.utc)

    await db.commit()
    return ApiResponse.success({"chat_id": channel.chat_id, "liveness": channel.liveness})


@router.post("/check-dead", response_model=ApiResponse)
async def check_dead_channels(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    """Check liveness for a list of chat IDs."""
    from ...telegram.adapters import mtproto as m
    chat_ids: list[int] = body.get("chat_ids", [])
    adapter = m.get_adapter()
    results = {}
    for cid in chat_ids[:50]:  # max 50 at once
        if adapter:
            liveness = await adapter.check_channel_liveness(cid)
        else:
            liveness = "unknown"
        results[cid] = liveness
        # Update DB
        r = await db.execute(select(Channel).where(Channel.chat_id == cid, Channel.is_deleted == False))
        ch = r.scalar_one_or_none()
        if ch:
            ch.liveness = liveness
            ch.liveness_checked_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse.success(results)


@router.delete("/{channel_id}", response_model=ApiResponse)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_deleted = True
    await db.commit()
    return ApiResponse.success({"deleted": True})
