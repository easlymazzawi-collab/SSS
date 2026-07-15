"""MTProto adapter using Telethon.

Wraps Telethon behind a clean interface.
For testing, use FakeMTProtoAdapter instead.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

_DATA_DIR = Path(os.environ.get("UPBAIN_DATA_DIR", Path(__file__).resolve().parents[4] / "data"))
_SESSION_DIR = _DATA_DIR / "sessions"
_SESSION_DIR.mkdir(parents=True, exist_ok=True)


class MTProtoAdapter:
    """Telethon-backed MTProto client adapter.
    
    Lifecycle: call connect() once; share instance across the app.
    """

    def __init__(self, api_id: int, api_hash: str, session_name: str = "userbot") -> None:
        from telethon import TelegramClient
        self._session_path = str(_SESSION_DIR / session_name)
        self._client = TelegramClient(self._session_path, api_id, api_hash)
        self._connected = False

    async def connect(self) -> None:
        await self._client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        if self._connected:
            await self._client.disconnect()
            self._connected = False

    async def is_user_authorized(self) -> bool:
        return await self._client.is_user_authorized()

    async def send_code(self, phone: str) -> str:
        """Returns phone_code_hash to be stored server-side."""
        result = await self._client.send_code_request(phone)
        return result.phone_code_hash

    async def sign_in(self, phone: str, code: str, phone_code_hash: str) -> dict:
        """Returns user info dict or raises SessionPasswordNeededError."""
        from telethon.tl.types import User
        user = await self._client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        return _user_to_dict(user)

    async def sign_in_2fa(self, password: str) -> dict:
        from telethon.tl.types import User
        user = await self._client.sign_in(password=password)
        return _user_to_dict(user)

    async def sign_out(self) -> None:
        await self._client.log_out()
        self._connected = False

    async def get_me(self) -> Optional[dict]:
        me = await self._client.get_me()
        if me is None:
            return None
        return _user_to_dict(me)

    async def get_entity(self, peer: Any) -> Any:
        return await self._client.get_entity(peer)

    async def iter_messages(self, entity: Any, **kwargs):
        return self._client.iter_messages(entity, **kwargs)

    async def forward_messages(self, from_peer: Any, ids: list[int], to_peer: Any, top_msg_id: int | None = None) -> list:
        from telethon.tl.functions.messages import ForwardMessagesRequest
        kwargs = dict(from_peer=from_peer, id=ids, to_peer=to_peer, random_id=[])
        if top_msg_id:
            kwargs["top_msg_id"] = top_msg_id
        return await self._client(ForwardMessagesRequest(**kwargs))

    async def edit_message(self, entity: Any, msg_id: int, text: str, formatting_entities=None) -> None:
        await self._client.edit_message(entity, msg_id, text=text, formatting_entities=formatting_entities)

    async def get_channel_info(self, peer: Any) -> dict:
        entity = await self._client.get_entity(peer)
        return _entity_to_dict(entity)

    async def check_channel_liveness(self, chat_id: int) -> str:
        """Returns: alive | dead | no_access | unknown"""
        try:
            from telethon.errors import (
                ChannelInvalidError,
                ChannelPrivateError,
                PeerIdInvalidError,
            )
            entity = await self._client.get_entity(chat_id)
            return "alive"
        except (ChannelInvalidError, PeerIdInvalidError):
            return "dead"
        except ChannelPrivateError:
            return "no_access"
        except Exception:
            return "unknown"

    async def invoke(self, request: Any) -> Any:
        return await self._client(request)


def _user_to_dict(user) -> dict:
    return {
        "id": user.id,
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "username": getattr(user, "username", None),
        "phone": getattr(user, "phone", None),
    }


def _entity_to_dict(entity) -> dict:
    return {
        "id": getattr(entity, "id", None),
        "title": getattr(entity, "title", None),
        "username": getattr(entity, "username", None),
    }


# ---------------------------------------------------------------------------
# Singleton management
# ---------------------------------------------------------------------------

_instance: Optional[MTProtoAdapter] = None


def get_adapter() -> Optional[MTProtoAdapter]:
    return _instance


async def create_adapter(api_id: int, api_hash: str, session_name: str = "userbot") -> MTProtoAdapter:
    global _instance
    if _instance is not None:
        await _instance.disconnect()
    _instance = MTProtoAdapter(api_id, api_hash, session_name)
    await _instance.connect()
    return _instance


async def destroy_adapter() -> None:
    global _instance
    if _instance is not None:
        await _instance.disconnect()
        _instance = None
