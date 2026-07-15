# PRD — UpBain Control

Version: 1.0-phase1  
Date: 2026-07-13

## Product Summary

UpBain is a local-first web admin dashboard for managing Telegram channels, forward mappings, and bot operations. It replaces a 526KB monolith `index.html` with a structured, tested, maintainable application.

## Architecture Decisions

- Backend: FastAPI + SQLAlchemy async + Alembic (ADR-001)
- MTProto: Telethon 1.37 (ADR-002)  
- Bot API: aiogram 3.x (ADR-002)
- Job queue: SQLite-backed async (ADR-003)
- Frontend: Modular ES modules + Vite build

## Phase Status

### Phase 0 ✅ Evidence Package
- [x] Research ledger (docs/research-ledger.md)
- [x] Document reconciliation (docs/document-reconciliation.md)
- [x] Threat model (docs/threat-model.md)
- [x] ADRs (docs/adr-001-backend-framework.md)
- [ ] UI control matrix (docs/ui-control-matrix.csv) — in progress

### Phase 1 ✅ Foundation
- [x] Source tree and build pipeline (tool/ with Vite frontend)
- [x] Backend health/config/DB/migrations (FastAPI + SQLAlchemy + init_db)
- [x] Single API client/origin/response contract ({ok, data, error})
- [x] Admin auth end-to-end, fail-closed (bcrypt + HMAC session + CSRF)
- [x] Removed mock live states (health returns real system state)
- [x] Security headers (CSP, X-Frame-Options, X-Content-Type-Options)
- [x] Audit logging

### Phase 2 ✅ Telegram Identity  
- [x] Secret store (AES-256-GCM encrypted)
- [x] Userbot phone → OTP → 2FA flow (server-side phone_code_hash)
- [x] Bot token set/rotate/validate (getMe validation)
- [x] Fake adapter for testing

### Phase 3 🔄 Core Runtime (Partial)
- [x] Channel registry (CRUD, liveness check)
- [x] Topic mappings (full CRUD with destination stack)
- [x] Durable job queue (queued/running/waiting_flood/cancelled/succeeded/failed)
- [x] Job cancel/FloodWait persist/SSE
- [x] Run mapping job (forward with batch/split/retry)
- [ ] Ads interleaving (divmod algorithm) — deferred
- [ ] Round-robin destination selection — deferred
- [ ] Forum topic forwarding — deferred

### Phase 4 🔲 Bot Operations (Deferred)
- [ ] Bot users/modules/force-join
- [ ] Archive
- [ ] File/share/view-codes
- [ ] Broadcast
- [ ] Forum admin/topic progress/invite

### Phase 5 🔲 Operations (Deferred)
- [ ] Scheduler
- [ ] Backup rotation/integrity check
- [ ] Dead/no-access channel classification
- [ ] Chatlist/folder sync
- [ ] Migration from localStorage/file state

### Phase 6 🔲 Hardening (Deferred)
- [ ] Responsive/accessibility audit
- [ ] Dependency/license/security scan
- [ ] Deploy/rollback/runbook

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pyrogram v30 migration needed | High | Medium | Telethon adapter wraps all calls; v30 tool not migrated (separate concern) |
| Telegram FloodWait on mass send | High | Medium | Persisted not_before; job re-queues after FloodWait; per-method limits |
| Session string exposure | Low | Critical | AES-GCM encrypted; excluded from backups |
| Album partial send on crash | Medium | Medium | job_items checkpoint; idempotency key; reconciliation on restart |
| Live Telegram tests without credentials | High | Low | Documented blocker; fake adapter tests pass; live gate = LIVE_TELEGRAM_TESTS=1 |

## Known Limitations

1. **Live Telegram tests** not run — no credentials available in this environment. All Telegram-dependent tests use FakeMTProtoAdapter. Documented as blocker.

2. **Phase 4-6 features** deferred but scaffolded: archive, file-to-link, bot users, scheduler, broadcast, forum admin.

3. **v30 Pyrogram tool** migration not included in scope — it runs independently. Its algorithmic patterns (interleaving, round-robin) are implemented in the service layer.

4. **Backup rotation** (keep N days, delete old) not yet scheduled — manual backup works; scheduler deferred to Phase 5.

5. **Pydantic V2 deprecation warnings** for `from_orm` → `model_validate` — functional, not breaking; should be updated to V2 style before production.
