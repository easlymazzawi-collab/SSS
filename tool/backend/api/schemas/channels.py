from datetime import datetime
from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    chat_id: int = Field(description="Telegram chat ID (negative for supergroups/channels)")
    username: str | None = None
    title: str | None = None


class ChannelOut(BaseModel):
    id: int
    chat_id: int
    username: str | None
    title: str | None
    photo_url: str | None
    member_count: int | None
    is_forum: bool
    liveness: str
    liveness_checked_at: datetime | None
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelMetaUpdate(BaseModel):
    title: str | None = None
    username: str | None = None
    photo_url: str | None = None
    member_count: int | None = None
    is_forum: bool | None = None
