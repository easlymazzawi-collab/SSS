"""Telegram identity routes — userbot login and bot credential management."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.base import get_db
from ...database.models import BotCredential, UserbotSession
from ...services.secret_store import SecretStore
from ..deps import get_current_user, require_csrf
from ..schemas.common import ApiResponse
from ..schemas.telegram import (
    BotCredentialOut,
    BotTokenRequest,
    Confirm2FARequest,
    ConfirmCodeRequest,
    SendCodeRequest,
    UserbotConfigRequest,
    UserbotStatusOut,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

# Server-side phone_code_hash storage (per session; never goes to browser)
_login_state: dict[str, Any] = {}  # "phone" → {phone_code_hash, expires_at}


def _mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return "***"
    return phone[:3] + "***" + phone[-2:]


# ---------------------------------------------------------------------------
# Userbot
# ---------------------------------------------------------------------------

@router.get("/userbot/status", response_model=ApiResponse[UserbotStatusOut])
async def userbot_status(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(UserbotSession).order_by(UserbotSession.id.desc()))
    session = result.scalars().first()
    if not session:
        return ApiResponse.success(UserbotStatusOut(status="disconnected"))

    from ...telegram.adapters import mtproto as m
    adapter = m.get_adapter()
    if adapter and adapter._connected:
        try:
            me = await adapter.get_me()
            if me:
                session.me_json = me
                session.status = "connected"
                await db.commit()
        except Exception:
            pass

    return ApiResponse.success(UserbotStatusOut(
        status=session.status,
        username=session.me_json.get("username") if session.me_json else None,
        first_name=session.me_json.get("first_name") if session.me_json else None,
        phone_masked=_mask_phone(session.phone) if session.phone else None,
        error_msg=session.error_msg,
    ))


@router.post("/userbot/config", response_model=ApiResponse)
async def save_userbot_config(
    body: UserbotConfigRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    """Save api_id/api_hash to secret store (never returned in responses)."""
    store = SecretStore(db)
    await store.set("userbot_api_id", str(body.api_id))
    await store.set("userbot_api_hash", body.api_hash)
    await db.commit()
    return ApiResponse.success({"configured": True})


@router.post("/userbot/send-code", response_model=ApiResponse)
async def send_login_code(
    body: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    """Send OTP to phone. phone_code_hash held server-side only."""
    store = SecretStore(db)
    api_id_str = await store.get("userbot_api_id")
    api_hash = await store.get("userbot_api_hash")

    if not api_id_str or not api_hash:
        raise HTTPException(status_code=400, detail="Configure api_id/api_hash first")

    from ...telegram.adapters.mtproto import create_adapter, get_adapter
    adapter = get_adapter()
    if adapter is None:
        try:
            adapter = await create_adapter(int(api_id_str), api_hash)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize Telegram client: {e}")

    try:
        phone_code_hash = await adapter.send_code(body.phone)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store hash server-side
    import time
    _login_state[body.phone] = {"phone_code_hash": phone_code_hash, "expires": time.time() + 300}

    # Update DB session
    result = await db.execute(select(UserbotSession))
    us = result.scalars().first()
    if not us:
        us = UserbotSession()
        db.add(us)
    us.phone = body.phone
    us.status = "pending_code"
    us.error_msg = None
    await db.commit()

    # Return only that code was sent — no hash to browser
    return ApiResponse.success({"sent": True, "phone_masked": _mask_phone(body.phone)})


@router.post("/userbot/confirm-code", response_model=ApiResponse)
async def confirm_login_code(
    body: ConfirmCodeRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    import time
    state = _login_state.get(body.phone)
    if not state or time.time() > state["expires"]:
        raise HTTPException(status_code=400, detail="Code expired or not requested")

    from ...telegram.adapters.mtproto import get_adapter
    adapter = get_adapter()
    if adapter is None:
        raise HTTPException(status_code=400, detail="No Telegram client initialized")

    try:
        from telethon.errors import SessionPasswordNeededError
        user = await adapter.sign_in(body.phone, body.code, state["phone_code_hash"])
        _login_state.pop(body.phone, None)

        result = await db.execute(select(UserbotSession))
        us = result.scalars().first()
        if us:
            us.status = "connected"
            us.me_json = user
        await db.commit()
        return ApiResponse.success({"logged_in": True, "need_2fa": False})

    except Exception as e:
        if "SessionPasswordNeeded" in type(e).__name__ or "password" in str(e).lower():
            result = await db.execute(select(UserbotSession))
            us = result.scalars().first()
            if us:
                us.status = "pending_2fa"
            await db.commit()
            return ApiResponse.success({"logged_in": False, "need_2fa": True})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/userbot/confirm-2fa", response_model=ApiResponse)
async def confirm_2fa(
    body: Confirm2FARequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    from ...telegram.adapters.mtproto import get_adapter
    adapter = get_adapter()
    if adapter is None:
        raise HTTPException(status_code=400, detail="No Telegram client initialized")

    try:
        user = await adapter.sign_in_2fa(body.password)
        result = await db.execute(select(UserbotSession))
        us = result.scalars().first()
        if us:
            us.status = "connected"
            us.me_json = user
        await db.commit()
        return ApiResponse.success({"logged_in": True})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/userbot/logout", response_model=ApiResponse)
async def logout_userbot(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    from ...telegram.adapters.mtproto import destroy_adapter, get_adapter
    adapter = get_adapter()
    if adapter:
        try:
            await adapter.sign_out()
        except Exception:
            pass
    await destroy_adapter()

    result = await db.execute(select(UserbotSession))
    us = result.scalars().first()
    if us:
        us.status = "disconnected"
        us.me_json = None
    await db.commit()
    return ApiResponse.success({"logged_out": True})


# ---------------------------------------------------------------------------
# Bot credentials
# ---------------------------------------------------------------------------

@router.get("/bots", response_model=ApiResponse[list[BotCredentialOut]])
async def list_bots(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(BotCredential).where(BotCredential.is_active == True)
    )
    bots = result.scalars().all()
    store = SecretStore(db)
    out = []
    for b in bots:
        status = await store.status(b.secret_key)
        out.append(BotCredentialOut(
            id=b.id,
            name=b.name,
            username=b.username,
            bot_id=b.bot_id,
            is_active=b.is_active,
            secret_key=b.secret_key,
            token_fingerprint=status.get("fingerprint"),
        ))
    return ApiResponse.success(out)


@router.post("/bots", response_model=ApiResponse[BotCredentialOut])
async def add_bot(
    body: BotTokenRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    secret_key = f"bot_token_{body.name.lower().replace(' ', '_')}"
    store = SecretStore(db)
    await store.set(secret_key, body.token)

    # Validate via getMe
    try:
        from aiogram import Bot
        bot = Bot(token=body.token)
        me = await bot.get_me()
        await bot.session.close()
        username = me.username
        bot_id = me.id
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Bot token validation failed: {e}")

    cred = BotCredential(
        name=body.name,
        secret_key=secret_key,
        username=username,
        bot_id=bot_id,
        validated_at=datetime.now(timezone.utc),
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)

    status = await store.status(secret_key)
    return ApiResponse.success(BotCredentialOut(
        id=cred.id,
        name=cred.name,
        username=cred.username,
        bot_id=cred.bot_id,
        is_active=cred.is_active,
        secret_key=cred.secret_key,
        token_fingerprint=status.get("fingerprint"),
    ))


@router.delete("/bots/{bot_id}", response_model=ApiResponse)
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_csrf),
):
    result = await db.execute(select(BotCredential).where(BotCredential.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    store = SecretStore(db)
    await store.delete(bot.secret_key)
    bot.is_active = False
    await db.commit()
    return ApiResponse.success({"deleted": True})
