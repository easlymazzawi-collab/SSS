"""Unified response envelope for all API endpoints.

ALL endpoints return {ok: bool, data: Any, error: str|None}.
Frontend reads .data — never raw JSON.
"""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    ok: bool
    data: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def success(cls, data: T | None = None) -> "ApiResponse[T]":
        return cls(ok=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse[None]":
        return cls(ok=False, error=error)


class PaginatedResponse(BaseModel, Generic[T]):
    ok: bool = True
    data: list[T]
    total: int
    page: int
    per_page: int
    error: Optional[str] = None
