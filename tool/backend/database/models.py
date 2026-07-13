"""SQLAlchemy ORM models for UpBain."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(256), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ---------------------------------------------------------------------------
# Secrets / Credentials
# ---------------------------------------------------------------------------

class SecretEntry(Base):
    """Encrypted secret store. Values are AES-GCM encrypted blobs."""
    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    encrypted_value: Mapped[bytes | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# Telegram Identity
# ---------------------------------------------------------------------------

class UserbotSession(Base):
    """Tracks userbot login state. One active session at a time."""
    __tablename__ = "userbot_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="disconnected", nullable=False
    )  # disconnected | pending_code | pending_2fa | connected | error
    session_name: Mapped[str] = mapped_column(String(128), default="userbot", nullable=False)
    me_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # getMe result (no secret)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class BotCredential(Base):
    """Bot token + validated bot info. Token stored in SecretEntry."""
    __tablename__ = "bot_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_key: Mapped[str] = mapped_column(String(128), nullable=False)  # ref to secrets.key
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    modules: Mapped[list["BotModule"]] = relationship(back_populates="bot", cascade="all, delete-orphan")


class BotModule(Base):
    __tablename__ = "bot_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot_credentials.id"), nullable=False)
    module_name: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bot: Mapped["BotCredential"] = relationship(back_populates="modules")
    __table_args__ = (UniqueConstraint("bot_id", "module_name"),)


# ---------------------------------------------------------------------------
# Channels / Registry
# ---------------------------------------------------------------------------

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_forum: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    liveness: Mapped[str] = mapped_column(
        String(32), default="unknown", nullable=False
    )  # alive | dead | no_access | unknown
    liveness_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class AdsSource(Base):
    """Source channels for ads content."""
    __tablename__ = "ads_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------------
# Topic Mappings
# ---------------------------------------------------------------------------

class TopicMapping(Base):
    """Source topic → destination config for auto-forwarding."""
    __tablename__ = "topic_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ads_mode: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    # normal | xdone | zdone
    media_sort: Mapped[str] = mapped_column(String(32), default="chronological", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    destinations: Mapped[list["MappingDestination"]] = relationship(
        back_populates="mapping", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("source_chat_id", "source_topic_id", name="uq_mapping_source"),
    )


class MappingDestination(Base):
    __tablename__ = "mapping_destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mapping_id: Mapped[int] = mapped_column(ForeignKey("topic_mappings.id"), nullable=False)
    dest_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dest_topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bot_secret_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rr_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    mapping: Mapped["TopicMapping"] = relationship(back_populates="destinations")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    waiting_flood = "waiting_flood"
    cancelling = "cancelling"
    cancelled = "cancelled"
    succeeded = "succeeded"
    partially_failed = "partially_failed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=JobStatus.queued.value, nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    lock_key: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["JobItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    events: Mapped[list["JobEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobItemStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed_permanent = "failed_permanent"
    failed_transient = "failed_transient"
    skipped = "skipped"


class JobItem(Base):
    """Individual message/album unit within a job."""
    __tablename__ = "job_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    item_ref: Mapped[dict] = mapped_column(JSON, nullable=False)
    # e.g. {"msg_ids": [101, 102], "topic_key": "vitamin"}
    status: Mapped[str] = mapped_column(String(32), default=JobItemStatus.pending.value, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="items", foreign_keys=[job_id])

    __table_args__ = (Index("ix_job_items_job_status", "job_id", "status"),)


class JobEvent(Base):
    """Append-only event log for SSE streaming."""
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # progress | flood_wait | cancelled | succeeded | failed | heartbeat
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    job: Mapped["Job"] = relationship(back_populates="events")


# ---------------------------------------------------------------------------
# Forum / Admin Bot
# ---------------------------------------------------------------------------

class ForumConfig(Base):
    __tablename__ = "forum_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    forum_chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    root_topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_pin: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_archive: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ForumTopic(Base):
    __tablename__ = "forum_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    forum_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mapping_id: Mapped[int | None] = mapped_column(ForeignKey("topic_mappings.id"), nullable=True)
    progress_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_msg_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("forum_chat_id", "topic_id"),)


# ---------------------------------------------------------------------------
# File Links / Share
# ---------------------------------------------------------------------------

class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    src_chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    src_msg_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = unlimited
    allow_forward: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    protect_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    origin_bot_secret_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ViewCode(Base):
    __tablename__ = "view_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    min_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # run_mapping | broadcast | backup | custom
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cron_expr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # null = one-shot
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Bangkok", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------------
# Bot Users
# ---------------------------------------------------------------------------

class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot_credentials.id"), nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("bot_id", "telegram_user_id"),)


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ok", nullable=False)
    # ok | failed | deleted
