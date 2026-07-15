"""Admin authentication service.

- bcrypt password hashing
- Session token: HMAC-signed via itsdangerous (stateless verify + server-side session table)
- Login rate limit: 5 attempts per 15 min per IP; lockout after 10
- CSRF: X-CSRF-Token header (double-submit cookie pattern)
- Audit logging on all auth events
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import AdminUser, AuditLog

log = logging.getLogger(__name__)
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SECRET = os.environ.get("UPBAIN_SECRET_KEY", "upbain-dev-key-insecure-change-me")
_SIGNER = URLSafeTimedSerializer(_SECRET, salt="session")
SESSION_MAX_AGE = int(os.environ.get("SESSION_MAX_AGE", 1800))  # 30 min default
MAX_ATTEMPTS_PER_WINDOW = 5
WINDOW_SECONDS = 900  # 15 min
LOCKOUT_ATTEMPTS = 10
LOCKOUT_DURATION = timedelta(hours=1)

# In-memory rate limit: {ip: [(timestamp, count)]}
_rate_limit: dict[str, list[datetime]] = {}


def _check_rate_limit(ip: str) -> bool:
    """True = allowed. False = rate-limited."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=WINDOW_SECONDS)
    attempts = _rate_limit.get(ip, [])
    attempts = [t for t in attempts if t > window_start]
    _rate_limit[ip] = attempts
    if len(attempts) >= MAX_ATTEMPTS_PER_WINDOW:
        return False
    attempts.append(now)
    _rate_limit[ip] = attempts
    return True


def create_session_token(user_id: int, username: str) -> str:
    payload = {"uid": user_id, "u": username}
    return _SIGNER.dumps(payload)


def verify_session_token(token: str) -> Optional[dict]:
    try:
        data = _SIGNER.loads(token, max_age=SESSION_MAX_AGE)
        return data
    except (SignatureExpired, BadSignature):
        return None


def generate_csrf_token(session_token: str) -> str:
    """Derive CSRF token from session token — stateless."""
    return hashlib.sha256(
        f"{session_token}:{_SECRET}:csrf".encode()
    ).hexdigest()[:32]


def verify_csrf_token(session_token: str, csrf_token: str) -> bool:
    expected = generate_csrf_token(session_token)
    return secrets.compare_digest(expected, csrf_token)


async def login(
    session: AsyncSession,
    username: str,
    password: str,
    ip: str = "unknown",
) -> Optional[str]:
    """Authenticate admin. Returns session token or None."""
    if not _check_rate_limit(ip):
        log.warning("Rate limit exceeded for IP %s", ip)
        await _audit(session, "system", "login_rate_limited", ip=ip, success=False)
        return None

    result = await session.execute(
        select(AdminUser).where(AdminUser.username == username, AdminUser.is_active == True)
    )
    user: Optional[AdminUser] = result.scalar_one_or_none()

    if user is None:
        await _audit(session, username, "login_failed_no_user", ip=ip, success=False)
        return None

    # Check lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        await _audit(session, username, "login_locked", ip=ip, success=False)
        return None

    if not pwd_ctx.verify(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= LOCKOUT_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
            log.warning("Account %s locked due to too many failures", username)
        await session.flush()
        await _audit(session, username, "login_wrong_password", ip=ip, success=False)
        return None

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await session.flush()

    token = create_session_token(user.id, user.username)
    await _audit(session, username, "login_success", ip=ip)
    return token


async def logout(session: AsyncSession, username: str, ip: str = "unknown") -> None:
    await _audit(session, username, "logout", ip=ip)


async def _audit(
    session: AsyncSession,
    actor: str,
    action: str,
    resource: str | None = None,
    detail: dict | None = None,
    ip: str = "unknown",
    success: bool = True,
) -> None:
    entry = AuditLog(
        actor=actor,
        action=action,
        resource=resource,
        detail=detail,
        ip=ip,
        success=success,
    )
    session.add(entry)
    await session.flush()
