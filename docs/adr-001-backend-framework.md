# ADR-001: Backend Framework and Database

**Status**: Accepted  
**Date**: 2026-07-13

## Context

The original index.html calls `http://127.0.0.1:8000` (absolute) and `/api/...` (relative) — two conflicting origins. The backend referenced does not exist. We need a real backend.

The methodology document describes Flask + thread-per-session + asyncio bridge. This creates problems:
- Thread-per-session does not scale and creates event-loop ownership issues
- No built-in OpenAPI; validation is manual
- Mixed sync/async requires `run_coroutine_threadsafe` everywhere

## Options Considered

### Option A: Flask + threading (current pattern in tong-hop-phuong-phap-code.md)
- Pros: Familiar, Tool 3 uses it
- Cons: No built-in OpenAPI; sync/async bridge is fragile; thread-per-session is a scalability anti-pattern; `check_same_thread=False` + WAL is not sufficient without proper connection management

### Option B: FastAPI + asyncio (selected)
- Pros: Built-in OpenAPI/Swagger; Pydantic validation; native async; single event loop; compatible with Telethon/aiogram async; SSE via `sse-starlette`
- Cons: Larger dependency; requires async SQLAlchemy

### Option C: Django
- Pros: Batteries included
- Cons: ORM is sync; async is bolted on; overkill for admin dashboard

## Decision

**FastAPI** with:
- SQLAlchemy 2.0 async engine + `aiosqlite`
- Alembic for versioned migrations
- `sse-starlette` for Server-Sent Events
- `passlib[bcrypt]` for password hashing
- `itsdangerous` for session signing
- Single event loop: Telethon and aiogram clients share the FastAPI event loop via background tasks

## Consequences

- All Telegram operations are async coroutines; no thread bridges
- Durable jobs run in the same process as background asyncio tasks (not separate worker process) for local-first simplicity; job state persisted in SQLite
- SSE streams from asyncio queues — no long-poll threads
- `API_BASE` issue fixed: frontend uses single relative `/api/...` origin; backend serves frontend static files in development via `StaticFiles`

---

# ADR-002: Telegram Library Selection

**Status**: Accepted  
**Date**: 2026-07-13

## Context

The v30 tool uses Pyrogram. Pyrogram is archived. We need to choose the MTProto client going forward.

## Decision Matrix

| Criterion | Weight | Telethon 1.37 | Hydrogram | Pyrofork |
|---|---|---|---|---|
| Maintained | 30% | ✅ Active | ✅ Small | ✅ Active |
| MIT License | 20% | ✅ MIT | ❌ LGPL | ❌ LGPL |
| Python 3.12 compat | 15% | ✅ Tested | ✅ | ✅ |
| Forum topic API | 10% | ✅ raw invoke | ✅ | ✅ |
| Async model | 10% | ✅ asyncio | ✅ | ✅ |
| Community/docs | 10% | ✅ Large | Small | Medium |
| Migration from Pyrogram | 5% | Medium | Low | Low |
| **Weighted Score** | | **~90%** | ~65% | ~65% |

## Decision

**Telethon 1.37** for MTProto operations, wrapped in `MTProtoAdapter` interface.  
**aiogram 3.x** for Bot API operations, wrapped in `BotAPIAdapter` interface.

Rationale:
- Telethon: MIT license, maintained at Codeberg, large community, full raw API access
- aiogram: MIT, fully async, Bot API parity, no mixing two frameworks

Both libraries are behind adapter interfaces so swapping is possible without changing business logic.

## Migration from Pyrogram v30

The v30 auto-xep tool (Pyrogram) is NOT migrated as part of this project. Its algorithmic patterns are preserved in the service layer:
- Interleaving (divmod)
- Persistent round-robin
- Global flood gate (adapted to asyncio)
- Liveness classification

The Pyrogram-specific API calls (`app.invoke`, `Client`) are replaced with Telethon equivalents in the service layer.

---

# ADR-003: Job Queue Design

**Status**: Accepted  
**Date**: 2026-07-13

## Context

Forward/broadcast operations can run for hours. They need:
- Durable state (survive process restart)
- Cancel/resume/retry
- FloodWait persist (not hold HTTP connection open)
- Per-job items with individual status

## Options

### Option A: Redis + ARQ
- Pros: Battle-tested; persistent
- Cons: Requires Redis daemon; not local-first

### Option B: SQLite-backed custom queue (selected)
- Pros: No external dependency; local-first; transactional with app DB
- Cons: Not distributed; polling-based

### Option C: Celery + SQLite broker
- Pros: Feature-rich
- Cons: Heavy; SQLite broker is not production-grade for Celery

## Decision

**SQLite-backed async job queue** with:

```
jobs table: id, type, status, payload (JSON), created_at, started_at, not_before, 
            error, result, idempotency_key, lock_key
job_items table: id, job_id, item_ref (JSON), status, error, attempt, processed_at
job_events table: id, job_id, timestamp, event_type, data (JSON)
```

**Job states**: `queued` → `running` → `waiting_flood` → `cancelling` → `cancelled` / `succeeded` / `partially_failed` / `failed`

**Worker**: single asyncio `Task` per job type; polls DB every 1s when idle; processes one job at a time per lock_key; respects `not_before` for FloodWait.

**SSE**: job events streamed via `job_events` → asyncio `Queue` per connection.

## Consequences

- Process restart is safe: worker picks up `running` jobs and resumes from last successful `job_items` checkpoint
- FloodWait is persisted as `not_before` timestamp; no HTTP connection held open
- Job idempotency: `idempotency_key` prevents duplicate scheduling
- Album as logical unit: album items stored as single `job_item` with array payload
