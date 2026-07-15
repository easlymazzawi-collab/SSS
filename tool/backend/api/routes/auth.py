"""Auth routes — fail-closed, CSRF protected."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.base import get_db
from ...services.auth_service import (
    generate_csrf_token,
    login,
    logout,
    verify_session_token,
)
from ..deps import get_current_user, require_csrf
from ..schemas.auth import AuthStatusResponse, LoginRequest, LoginResponse
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "upbain_session"
CSRF_COOKIE = "upbain_csrf"


@router.get("/status", response_model=ApiResponse[AuthStatusResponse])
async def auth_status(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return ApiResponse.success(AuthStatusResponse(authenticated=False))
    data = verify_session_token(token)
    if not data:
        return ApiResponse.success(AuthStatusResponse(authenticated=False))
    return ApiResponse.success(
        AuthStatusResponse(authenticated=True, username=data["u"], role="admin")
    )


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def do_login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    token = await login(db, body.username, body.password, ip)
    await db.commit()

    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or rate limited")

    csrf = generate_csrf_token(token)

    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=False,  # set True in production with HTTPS
        max_age=1800,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,  # must be readable by JS
        samesite="strict",
        secure=False,
        max_age=1800,
        path="/",
    )
    return ApiResponse.success(
        LoginResponse(username=body.username, role="admin", csrf_token=csrf)
    )


@router.post("/logout")
async def do_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await logout(db, user["u"])
    await db.commit()
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)
    return ApiResponse.success()
