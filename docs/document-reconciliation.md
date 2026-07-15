# Document Reconciliation — UpBain

Date: 2026-07-13  
Sources: tong-hop-phuong-phap-code.md, bao-cao-doi-chieu-upbain.md, ma-tran-nut-index.csv

## Conflicts Resolved

| Conflict | Original | Resolution | Evidence |
|---|---|---|---|
| Telethon vs Pyrogram | v30 uses Pyrogram (archived) | Telethon 1.37 as primary MTProto client | ADR-002; Pyrogram README states "no longer maintained" |
| Flask/thread vs async backend | Tool 3 uses Flask + threading | FastAPI async | ADR-001; avoids thread-per-session and event loop bridge |
| Thread-per-session vs asyncio | Tool 3: `threading.Thread` per session | `asyncio.create_task` + job queue | ADR-001 |
| File state + SQLite dual-write | Tool 3: dual persistence | DB-only (SQLite is source of truth); file export on demand | ADR-003 |
| topic_map.txt vs DB source of truth | v30 reads from txt | DB is truth; txt is export-only via "Sinh topic_map.txt" button | implemented |
| Fail-open membership | `except Exception: return True` | Fail-closed for sensitive content; audit on error | threat-model.md T3 |
| `2*(attempt+1)` called exponential | Tool 3 doc says "exponential backoff" | Corrected to `2**attempt` (true exponential) in job worker | jobs/run_mapping.py |
| Threshold 60/120/86400 | Multiple defaults | All thresholds configurable; no hardcoded rate | auth_service.py |
| min_id checkpoint may duplicate | Tool 3.7: simple min_id | job_items table tracks per-item status; idempotency key | models.py, job_queue.py |
| Entity passthrough when text changes | Tool 1: "passthrough entities" | Passthrough only if text unchanged; insert/cut → transform offset | documented in services |
| Numeric token "unique" | Tool 3.5: "difficult to guess" | CSPRNG + UNIQUE constraint + collision retry | secret_store.py |
| WAL "enough for multiple threads" | Tool 3.6: WAL + check_same_thread=False | Proper session scoping via async_sessionmaker per request | database/base.py |
| Bot token in browser | index.html:8201 — localStorage | Secret store server-side; fingerprint only to browser | P0 fixed |
| Auth fail-open | index.html:8981 — boot without auth | Fail-closed: 401 on all protected routes without session | auth.py, deps.py |
| DOM XSS via innerHTML | index.html:11392 — phone in innerHTML | textContent throughout frontend | frontend/src/ |
| `adsChannels()` undefined | index.html:9909 | Not implemented; file-to-link deferred | deferred |
| Badge DOM mismatch | index.html:12333 — JS finds wrong IDs | Frontend rebuilt; IDs match | frontend rebuilt |
| API_BASE dual origin | http://127.0.0.1:8000 + /api/... | Single origin /api/... | api/client.js |
| Handler generic + handler real conflict | relogin_userbot, save_admin_bot_invite_forum | Separate explicit handlers; no generic catch-all | telegram.py |
| Optimistic save false-success | mappings PUT ignores destinations | DB-confirmed save with full destination stack | mappings.py |
| Dead channel vs no_access | v30: ChannelPrivate = dead | Classified as no_access; not auto-deleted | channels.py, models.py |
| ChannelPrivate not auto-delete | "4.11 liveness classification" | `check_channel_liveness` returns alive/dead/no_access/unknown; only dead is marked dead | channels.py |

## Methods from tong-hop-phuong-phap-code.md

| Method | Status | Implementation |
|---|---|---|
| Message entity preservation | Preserved | Documented in services; utf16 offset logic |
| Batch forwarding ForwardMessagesRequest | Implemented | jobs/run_mapping.py |
| Token Bucket rate limiting | Implemented as job-level FloodWait | job_queue.py ctx.persist_flood_wait |
| Split retry for bad IDs | Implemented | jobs/run_mapping.py _forward_to_dest |
| FloodWait persist + retry | Implemented | job_queue.py persist_flood_wait; not_before in DB |
| SSE progress | Implemented | sse.py; job_events table; JobSSE client |
| Album debounce | Documented; requires Bot API handler | deferred to Phase 4 |
| File-to-link with token | Partial; schema in models.py | share_links table; server-side token |
| WAL mode SQLite | Implemented | database/base.py PRAGMA journal_mode=WAL |
| UPSERT | Used | SQLAlchemy merge patterns |
| Soft delete | Implemented | is_deleted/is_active columns |
| Resume from checkpoint | Implemented | job_items as checkpoint; min_id in payload |
| Dual persistence | Removed | DB only; no file state |
| Force-join gate | Deferred | Phase 4 |
| Backup rotation | Partial | backup.py; retention TODO |
| Login OTP/2FA multi-step | Implemented | telegram.py routes |
| Bounded concurrency Semaphore | In job worker | one job per lock_key |
| Round-robin persistent | Schema ready | MappingDestination.rr_index |
| Chatlist import | Deferred | Phase 5 |
| Error classification permanent/transient | Implemented | jobs/run_mapping.py _is_permanent |
| Global flood gate | Implemented | ctx.persist_flood_wait; coordinated via not_before |
| Ads interleaving divmod | Deferred | Phase 3 completion |

## P0 Bugs from bao-cao-doi-chieu-upbain.md — Status

| Bug | Status |
|---|---|
| Auth fail-open (L8981-8989) | FIXED — fail-closed, 401 on all protected routes |
| Bot token in localStorage/DOM (L8201-8239) | FIXED — secret store; fingerprint only |
| API hash in DOM hydrate (L11651-11661) | FIXED — never returned |
| DOM XSS phone/error innerHTML (L11392-11399) | FIXED — textContent in frontend |
| Response envelope mismatch (.running vs .data.enabled) | FIXED — unified envelope {ok,data} |
| adsChannels() undefined | DEFERRED — functionality not yet implemented |
| backendStatusBadge DOM missing | FIXED — frontend rebuilt with correct IDs |
| API_BASE dual origin | FIXED — single /api/... origin |
| Generic + specific handler conflict | FIXED — separate explicit handlers |
| Save mapping false-success | FIXED — DB-confirmed save with full destinations |
| Dynamic button not bound | FIXED — event delegation on container |
| Archive/file-link refresh only resets filter | DEFERRED — Phase 4 |
| Export user duplicate listener | DEFERRED — Phase 4 |
| Schedule only UI | DEFERRED — Phase 5 |

## Controls from ma-tran-nut-index.csv — Coverage

Total tracked: 86 static + dynamic buttons  
Implemented in new frontend: dashboard (3), channels (5), mappings (7), telegram (9), backup (5), logs (3), navigation (10)  
Deferred (clearly labeled in UI): archive, file-to-link, anti-flood simulator, audit/sandbox, bot users, admin forum, schedule  
Removed (dead/unreachable): Self-delete dynamic controls (D1-D5 — container not in HTML)

Status: Foundation + core runtime implemented. Phase 4-6 controls deferred with explicit UI labels.
