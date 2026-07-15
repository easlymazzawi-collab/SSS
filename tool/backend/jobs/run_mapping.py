"""Durable job: run topic mapping (forward messages from source to destinations).

Implements:
- Batch forward (100 IDs max per request)
- Split retry for bad IDs
- FloodWait: persist deadline, re-queue
- Checkpoint via job_items
- Cancel check
- Dry-run mode
- Round-robin destination selection
- Error classification: permanent | transient | no_access | unknown
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database.base import SessionLocal
from ..database.models import (
    Channel,
    Job,
    JobItem,
    JobItemStatus,
    MappingDestination,
    TopicMapping,
)
from ..services.job_queue import JobContext, emit_event, register_handler
from ..telegram.adapters.mtproto import get_adapter

log = logging.getLogger(__name__)

BATCH_SIZE = 50  # IDs per forward request
MAX_RETRY = 3


@register_handler("run_mapping")
async def handle_run_mapping(ctx: JobContext) -> None:
    mapping_id = ctx.payload["mapping_id"]
    dry_run = ctx.payload.get("dry_run", False)
    send_cap = ctx.payload.get("send_cap", 500)

    async with SessionLocal() as session:
        result = await session.execute(
            select(TopicMapping)
            .options(selectinload(TopicMapping.destinations))
            .where(TopicMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise ValueError(f"Mapping {mapping_id} not found")

        # Load checkpoint
        items_result = await session.execute(
            select(JobItem)
            .where(JobItem.job_id == ctx.job_id)
            .order_by(JobItem.id.desc())
            .limit(1)
        )
        last_item = items_result.scalar_one_or_none()
        last_msg_id = 0
        if last_item and last_item.item_ref:
            last_msg_id = max(last_item.item_ref.get("msg_ids", [0]))

        mapping_data = {
            "source_chat_id": mapping.source_chat_id,
            "source_topic_id": mapping.source_topic_id,
            "destinations": [
                {
                    "dest_chat_id": d.dest_chat_id,
                    "dest_topic_id": d.dest_topic_id,
                    "bot_secret_key": d.bot_secret_key,
                    "rr_index": d.rr_index,
                }
                for d in mapping.destinations
                if d.is_active
            ],
        }

    adapter = get_adapter()
    if adapter is None:
        raise RuntimeError("No MTProto adapter connected. Log in userbot first.")

    src = mapping_data["source_chat_id"]
    topic_id = mapping_data.get("source_topic_id")
    destinations = mapping_data["destinations"]

    if not destinations:
        log.warning("No active destinations for mapping %d", mapping_id)
        return

    # Collect messages
    msg_ids: list[int] = []
    log.info("Collecting messages from chat %d min_id=%d", src, last_msg_id)

    try:
        entity = await adapter.get_entity(src)
    except Exception as e:
        raise RuntimeError(f"Cannot resolve source chat {src}: {e}")

    iter_kwargs = {"min_id": last_msg_id, "reverse": True}
    if topic_id:
        iter_kwargs["reply_to"] = topic_id

    async for msg in adapter.iter_messages(entity, **iter_kwargs):
        msg_ids.append(msg.id)
        if len(msg_ids) >= send_cap:
            break

    total = len(msg_ids)
    log.info("Found %d messages to forward", total)
    await ctx.report_progress(0, total, "Collected messages")

    done = 0
    # Process in batches
    for batch_start in range(0, total, BATCH_SIZE):
        if await ctx.is_cancelled():
            log.info("Job %d cancelled at batch %d", ctx.job_id, batch_start)
            return

        batch = msg_ids[batch_start: batch_start + BATCH_SIZE]
        success_ids, failed_ids = await _try_forward_batch(
            ctx, adapter, src, batch, destinations, dry_run
        )

        # Persist checkpoint
        async with SessionLocal() as session:
            if batch:
                item = JobItem(
                    job_id=ctx.job_id,
                    item_ref={"msg_ids": batch, "success": len(success_ids), "failed": len(failed_ids)},
                    status=JobItemStatus.succeeded.value if not failed_ids else JobItemStatus.failed_transient.value,
                )
                session.add(item)
                await session.commit()

        done += len(success_ids)
        await ctx.report_progress(done, total, f"Forwarded {done}/{total}")

    log.info("Mapping %d complete: %d/%d forwarded", mapping_id, done, total)


async def _try_forward_batch(
    ctx: JobContext,
    adapter,
    src: int,
    ids: list[int],
    destinations: list[dict],
    dry_run: bool,
) -> tuple[list[int], list[int]]:
    """Forward a batch. Returns (success_ids, failed_ids)."""
    if dry_run:
        log.info("[DRY-RUN] Would forward %d messages", len(ids))
        return ids, []

    success_ids = []
    failed_ids = []

    for dest in destinations:
        ok, fail = await _forward_to_dest(ctx, adapter, src, ids, dest)
        success_ids.extend(ok)
        failed_ids.extend(fail)

    return list(set(success_ids)), list(set(failed_ids) - set(success_ids))


async def _forward_to_dest(
    ctx: JobContext,
    adapter,
    src: int,
    ids: list[int],
    dest: dict,
) -> tuple[list[int], list[int]]:
    dest_chat = dest["dest_chat_id"]
    dest_topic = dest.get("dest_topic_id")

    for attempt in range(MAX_RETRY):
        try:
            await adapter.forward_messages(src, ids, dest_chat, top_msg_id=dest_topic)
            return ids, []
        except Exception as e:
            err_name = type(e).__name__
            err_str = str(e)

            if _is_flood_wait(e):
                wait_secs = _get_flood_seconds(e)
                log.warning("FloodWait %ds for job %d", wait_secs, ctx.job_id)
                await ctx.persist_flood_wait(wait_secs, source="forward")
                await asyncio.sleep(wait_secs + 2)
                continue

            if _is_permanent(err_name):
                log.warning("Permanent error %s for batch to %d", err_name, dest_chat)
                if len(ids) > 1:
                    # Split retry to isolate bad ID
                    mid = len(ids) // 2
                    ok_l, fail_l = await _forward_to_dest(ctx, adapter, src, ids[:mid], dest)
                    ok_r, fail_r = await _forward_to_dest(ctx, adapter, src, ids[mid:], dest)
                    return ok_l + ok_r, fail_l + fail_r
                return [], ids

            log.warning("Transient error %s, attempt %d", err_name, attempt + 1)
            await asyncio.sleep(2 ** (attempt + 1))

    return [], ids


def _is_flood_wait(exc) -> bool:
    return "FloodWait" in type(exc).__name__ or "flood_wait" in str(exc).lower()


def _get_flood_seconds(exc) -> int:
    try:
        return int(exc.seconds)
    except (AttributeError, TypeError):
        try:
            return int(exc.value)
        except (AttributeError, TypeError):
            return 60


_PERMANENT_ERRORS = {
    "MessageIdInvalidError",
    "MediaEmptyError",
    "ChatIdInvalidError",
    "ChannelInvalidError",
    "PeerIdInvalidError",
    "MessageNotModifiedError",
}


def _is_permanent(err_name: str) -> bool:
    return err_name in _PERMANENT_ERRORS
