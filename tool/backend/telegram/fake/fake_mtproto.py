"""Fake MTProto adapter for unit/integration tests.

Simulates Telethon behavior without real Telegram connection.
Supports: albums, entities, FloodWait injection, forum topics.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional


class FakeMessage:
    def __init__(
        self,
        msg_id: int,
        text: str = "",
        entities=None,
        grouped_id: int | None = None,
        topic_id: int | None = None,
    ):
        self.id = msg_id
        self.message = text
        self.entities = entities or []
        self.grouped_id = grouped_id
        self.reply_to = _FakeReplyTo(topic_id) if topic_id else None


class _FakeReplyTo:
    def __init__(self, topic_id: int):
        self.reply_to_top_id = topic_id
        self.forum_topic = True


class FakeMTProtoAdapter:
    """In-process fake adapter for testing."""

    def __init__(self):
        self._authorized = True
        self._me = {"id": 12345, "username": "fake_user", "first_name": "Fake", "phone": "+66000000000"}
        self._messages: dict[int, list[FakeMessage]] = {}  # chat_id → messages
        self._sent: list[dict] = []
        self.flood_wait_seconds: int = 0  # set to inject FloodWait

    async def connect(self): pass
    async def disconnect(self): pass

    async def is_user_authorized(self) -> bool:
        return self._authorized

    async def send_code(self, phone: str) -> str:
        return "fake_code_hash_123"

    async def sign_in(self, phone: str, code: str, phone_code_hash: str) -> dict:
        if code == "00000":
            raise Exception("SessionPasswordNeededError")
        self._authorized = True
        return self._me

    async def sign_in_2fa(self, password: str) -> dict:
        self._authorized = True
        return self._me

    async def sign_out(self) -> None:
        self._authorized = False

    async def get_me(self) -> Optional[dict]:
        if not self._authorized:
            return None
        return self._me

    def add_messages(self, chat_id: int, messages: list[FakeMessage]) -> None:
        self._messages.setdefault(chat_id, []).extend(messages)

    async def iter_messages(self, entity: Any, **kwargs):
        msgs = self._messages.get(entity if isinstance(entity, int) else 0, [])
        min_id = kwargs.get("min_id", 0)
        for m in sorted(msgs, key=lambda x: x.id):
            if m.id > min_id:
                yield m

    async def forward_messages(self, from_peer, ids, to_peer, top_msg_id=None):
        if self.flood_wait_seconds > 0:
            from telethon.errors import FloodWaitError
            raise FloodWaitError(request=None, capture=self.flood_wait_seconds)
        for msg_id in ids:
            self._sent.append({
                "from": from_peer,
                "to": to_peer,
                "msg_id": msg_id,
                "top_msg_id": top_msg_id,
            })
        return [{"id": i + 1000} for i in ids]

    async def edit_message(self, entity, msg_id, text, formatting_entities=None):
        pass

    async def get_channel_info(self, peer) -> dict:
        return {"id": peer if isinstance(peer, int) else 0, "title": "Fake Channel", "username": None}

    async def check_channel_liveness(self, chat_id: int) -> str:
        return "alive"

    async def invoke(self, request) -> Any:
        return None

    def get_sent(self) -> list[dict]:
        return list(self._sent)
