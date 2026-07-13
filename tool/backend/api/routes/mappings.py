"""Topic mapping routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.base import get_db
from ...database.models import MappingDestination, TopicMapping
from ..deps import get_current_user, require_csrf
from ..schemas.mappings import TopicMappingCreate, TopicMappingOut, TopicMappingUpdate
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/mappings", tags=["mappings"])


async def _get_mapping_with_destinations(session: AsyncSession, mapping_id: int) -> TopicMapping | None:
    result = await session.execute(
        select(TopicMapping)
        .options(selectinload(TopicMapping.destinations))
        .where(TopicMapping.id == mapping_id, TopicMapping.is_active == True)
    )
    return result.scalar_one_or_none()


@router.get("", response_model=ApiResponse[List[TopicMappingOut]])
async def list_mappings(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(TopicMapping)
        .options(selectinload(TopicMapping.destinations))
        .order_by(TopicMapping.created_at.desc())
    )
    mappings = result.scalars().all()
    return ApiResponse.success([TopicMappingOut.from_orm(m) for m in mappings])


@router.post("", response_model=ApiResponse[TopicMappingOut])
async def create_mapping(
    body: TopicMappingCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    # Check for duplicate source
    existing = await db.execute(
        select(TopicMapping).where(
            TopicMapping.source_chat_id == body.source_chat_id,
            TopicMapping.source_topic_id == body.source_topic_id,
            TopicMapping.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Mapping for this source already exists")

    mapping = TopicMapping(
        name=body.name,
        source_chat_id=body.source_chat_id,
        source_topic_id=body.source_topic_id,
        ads_mode=body.ads_mode,
        media_sort=body.media_sort,
    )
    db.add(mapping)
    await db.flush()

    for dest in body.destinations:
        d = MappingDestination(
            mapping_id=mapping.id,
            dest_chat_id=dest.dest_chat_id,
            dest_topic_id=dest.dest_topic_id,
            bot_secret_key=dest.bot_secret_key,
        )
        db.add(d)

    await db.commit()
    mapping = await _get_mapping_with_destinations(db, mapping.id)
    return ApiResponse.success(TopicMappingOut.from_orm(mapping))


@router.get("/{mapping_id}", response_model=ApiResponse[TopicMappingOut])
async def get_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    mapping = await _get_mapping_with_destinations(db, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return ApiResponse.success(TopicMappingOut.from_orm(mapping))


@router.put("/{mapping_id}", response_model=ApiResponse[TopicMappingOut])
async def update_mapping(
    mapping_id: int,
    body: TopicMappingUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    mapping = await _get_mapping_with_destinations(db, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    if body.name is not None:
        mapping.name = body.name
    if body.ads_mode is not None:
        mapping.ads_mode = body.ads_mode
    if body.media_sort is not None:
        mapping.media_sort = body.media_sort
    if body.is_active is not None:
        mapping.is_active = body.is_active

    if body.destinations is not None:
        # Replace all destinations using direct DELETE for reliability
        from sqlalchemy import delete as sa_delete
        await db.execute(
            sa_delete(MappingDestination).where(MappingDestination.mapping_id == mapping.id)
        )
        await db.flush()
        for dest in body.destinations:
            d = MappingDestination(
                mapping_id=mapping.id,
                dest_chat_id=dest.dest_chat_id,
                dest_topic_id=dest.dest_topic_id,
                bot_secret_key=dest.bot_secret_key,
            )
            db.add(d)

    await db.commit()
    # Expire cached relationships before re-fetching
    await db.close()
    mapping = await _get_mapping_with_destinations(db, mapping_id)
    return ApiResponse.success(TopicMappingOut.from_orm(mapping))


@router.delete("/{mapping_id}", response_model=ApiResponse)
async def delete_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    mapping = await _get_mapping_with_destinations(db, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    mapping.is_active = False
    await db.commit()
    return ApiResponse.success({"deleted": True})
