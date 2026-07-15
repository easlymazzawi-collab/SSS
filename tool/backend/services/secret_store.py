"""AES-256-GCM encrypted secret store backed by the database.

Secrets (bot tokens, api_hash, session strings) are encrypted before
being written to the DB. The encryption key is derived from
UPBAIN_SECRET_KEY env var. The DB never stores plaintext secrets.

Only status/fingerprint is returned to callers outside this module.
"""
from __future__ import annotations

import hashlib
import logging
import os
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import SecretEntry

log = logging.getLogger(__name__)

_KEY_ENV = "UPBAIN_SECRET_KEY"
_NONCE_SIZE = 12  # bytes for AES-GCM


def _get_key() -> bytes:
    raw = os.environ.get(_KEY_ENV, "")
    if not raw:
        log.warning(
            "UPBAIN_SECRET_KEY not set; using insecure development key. "
            "Set this variable before production use."
        )
        raw = "upbain-dev-key-insecure-change-me"
    # Derive 32-byte key from env value
    return hashlib.sha256(raw.encode()).digest()


def _encrypt(value: str) -> str:
    key = _get_key()
    nonce = os.urandom(_NONCE_SIZE)
    ct = AESGCM(key).encrypt(nonce, value.encode(), None)
    return b64encode(nonce + ct).decode()


def _decrypt(blob: str) -> str:
    key = _get_key()
    raw = b64decode(blob)
    nonce, ct = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()


def _fingerprint(value: str) -> str:
    """Return last 4 chars + length for display. Never returns full secret."""
    if len(value) <= 4:
        return "****"
    return f"...{value[-4:]}"


class SecretStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set(self, key: str, value: str) -> None:
        """Encrypt and store a secret. Updates if key exists."""
        blob = _encrypt(value)
        fp = _fingerprint(value)

        result = await self._session.execute(
            select(SecretEntry).where(SecretEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            entry = SecretEntry(key=key, encrypted_value=blob, fingerprint=fp)
            self._session.add(entry)
        else:
            entry.encrypted_value = blob
            entry.fingerprint = fp
        await self._session.flush()

    async def get(self, key: str) -> str | None:
        """Decrypt and return secret value. Returns None if not found."""
        result = await self._session.execute(
            select(SecretEntry).where(SecretEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        if entry is None or not entry.encrypted_value:
            return None
        try:
            return _decrypt(entry.encrypted_value)
        except Exception:
            log.exception("Failed to decrypt secret %s", key)
            return None

    async def status(self, key: str) -> dict:
        """Return {configured: bool, fingerprint: str|None} — no plaintext."""
        result = await self._session.execute(
            select(SecretEntry).where(SecretEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        if entry is None or not entry.encrypted_value:
            return {"configured": False, "fingerprint": None}
        return {"configured": True, "fingerprint": entry.fingerprint}

    async def delete(self, key: str) -> bool:
        result = await self._session.execute(
            select(SecretEntry).where(SecretEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        await self._session.delete(entry)
        await self._session.flush()
        return True
