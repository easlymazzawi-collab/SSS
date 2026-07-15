from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobOut(BaseModel):
    id: int
    job_type: str
    status: str
    payload: dict
    progress: dict
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    not_before: Optional[datetime]

    class Config:
        from_attributes = True


class RunMappingRequest(BaseModel):
    mapping_id: int
    dry_run: bool = False
    send_cap: int = 500  # max messages per job run
    idempotency_key: Optional[str] = None


class BroadcastRequest(BaseModel):
    bot_secret_key: str
    chat_ids: list[int]
    text: str
    dry_run: bool = False
    send_cap: int = 100
    confirm: bool = False  # must be True for mass sends
