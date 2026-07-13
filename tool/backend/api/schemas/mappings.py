from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DestinationIn(BaseModel):
    dest_chat_id: int
    dest_topic_id: Optional[int] = None
    bot_secret_key: Optional[str] = None


class TopicMappingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    source_chat_id: int
    source_topic_id: Optional[int] = None
    ads_mode: str = Field(default="normal", pattern="^(normal|xdone|zdone)$")
    media_sort: str = Field(default="chronological", pattern="^(chronological|score)$")
    destinations: list[DestinationIn] = Field(default_factory=list)


class TopicMappingUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    ads_mode: Optional[str] = Field(None, pattern="^(normal|xdone|zdone)$")
    media_sort: Optional[str] = None
    is_active: Optional[bool] = None
    destinations: Optional[list[DestinationIn]] = None


class MappingDestinationOut(BaseModel):
    id: int
    dest_chat_id: int
    dest_topic_id: Optional[int]
    bot_secret_key: Optional[str] = None  # never return actual token
    rr_index: int
    is_active: bool

    class Config:
        from_attributes = True


class TopicMappingOut(BaseModel):
    id: int
    name: str
    source_chat_id: int
    source_topic_id: Optional[int]
    ads_mode: str
    media_sort: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    destinations: list[MappingDestinationOut]

    class Config:
        from_attributes = True
