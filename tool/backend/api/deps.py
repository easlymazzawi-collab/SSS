"""FastAPI dependencies for auth, CSRF and role checks."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from ..services.auth_service import verify_csrf_token, verify_session_token

SESSION_COOKIE = "upbain_session"
CSRF_HEADER = "X-CSRF-Token"


def get_session_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def get_current_user(request: Request) -> dict:
    """Fail-closed: raises 401 if no valid session."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    data = verify_session_token(token)
    if data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return data


def require_csrf(request: Request, user: dict = Depends(get_current_user)) -> dict:
    """Require valid CSRF token on state-changing requests."""
    token = request.cookies.get(SESSION_COOKIE)
    csrf = request.headers.get(CSRF_HEADER)
    if not csrf:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")
    if not verify_csrf_token(token, csrf):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")
    return user


def require_role(role: str):
    """Dependency factory for role-based access control."""
    def _check(user: dict = Depends(require_csrf)) -> dict:
        user_role = user.get("role", "viewer")
        roles = ["viewer", "operator", "admin"]
        if roles.index(user_role) < roles.index(role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires role: {role}")
        return user
    return _check
