# Research Ledger — UpBain

Accessed: 2026-07-13 (all sources)

## Assumptions Log

| # | Assumption | Rationale | Reversible? |
|---|---|---|---|
| A1 | Local-first, single admin, SQLite default | Prompt states "local-first for one admin" | Yes — swap to PostgreSQL via config |
| A2 | Telethon as MTProto client | Pyrogram archived; Telethon maintained at Codeberg MIT | Yes — behind adapter interface |
| A3 | aiogram 3.x as Bot API client | Fully async, MIT, actively maintained | Yes — behind adapter interface |
| A4 | FastAPI as web framework | Async, OpenAPI built-in, Pydantic validation | Yes — framework swap is invasive but backend is modular |
| A5 | SQLAlchemy async + Alembic for migrations | Industry standard, versioned migrations | Yes |
| A6 | Custom SQLite-backed job queue | No Redis dependency for local-first; can swap to ARQ+Redis | Yes |
| A7 | bcrypt for password hashing | Standard, passlib wrapper | No (would require rehash) |
| A8 | `Asia/Bangkok` default timezone | Stated in prompt | Yes — configurable |
| A9 | Session tokens: signed HMAC via itsdangerous | Secure, no DB query per request (stateless verify) | Yes |
| A10 | File-to-link uses server-side storage, not Telegram CDN | Complies with Bot Platform Terms §5.2(e) | Yes |

---

## Official Telegram Sources

### 1. Telegram Bot API
- **URL**: https://core.telegram.org/bots/api
- **Type**: Official spec
- **Version**: Checked 2026-07-13 (latest release)
- **License**: N/A (documentation)
- **Key findings**:
  - `copyMessages` / `forwardMessages` accept 1–100 IDs per call
  - Rate: 1 msg/sec per chat, 30 msgs/sec globally per bot (conservative; real FloodWait is dynamic)
  - File IDs are bot-specific; cannot reuse across bots
  - `getChatMember` for membership check
  - Forum topics: `message_thread_id` parameter
- **Decision**: Use for Bot API adapter; do NOT use Bot API file URLs as public CDN

### 2. Telegram Bots FAQ
- **URL**: https://core.telegram.org/bots/faq
- **Type**: Official FAQ
- **Key findings**:
  - "My bot is hitting limits, how do I avoid this?" — no global safe rate; handle 429 and respect `retry_after`
  - "Can I use Telegram files as a storage?" — explicitly NO
  - Broadcast: queue messages, respect 429, use `retry_after`
- **Decision**: No hardcoded GLOBAL_RATE; handle server-returned FloodWait/429

### 3. Bot Platform Developer Terms
- **URL**: https://telegram.org/tos/bot-developers
- **Type**: Legal/Terms
- **Key findings**:
  - §5.2(e): Must not use Bot Platform as "cloud storage sites, file hosting services, or similar"
  - Anti-spam, anti-abuse requirements
  - Cannot bypass rate limits or moderation
  - Cannot act on behalf of user without knowledge
- **Decision**: File-to-link uses our own object storage (local filesystem with presigned tokens); Telegram only delivers within Telegram

### 4. Telegram API Terms
- **URL**: https://core.telegram.org/api/terms
- **Type**: Legal/Terms
- **Key findings**:
  - Consent requirements for automation
  - Privacy obligations
  - Anti-abuse: no fake views/subscribers, no spam
  - Userbot login only for account owner
- **Decision**: Userbot login flow is admin-only, requires direct OTP entry; no storing OTP

### 5. User Authorization (MTProto)
- **URL**: https://core.telegram.org/api/auth
- **Type**: Official spec
- **Key findings**:
  - Phone → `auth.sendCode` → `phone_code_hash` → `auth.signIn` → optional SRP 2FA
  - `phone_code_hash` must be kept server-side between steps
  - Session persists after successful sign-in
- **Decision**: Multi-step login state held server-side; OTP never persisted, expires with session

### 6. Forum Topics (MTProto)
- **URL**: https://core.telegram.org/api/forum
- **Type**: Official spec
- **Key findings**:
  - `reply_to.forum_topic=true` + `top_msg_id` for topic messages
  - `channels.createForumTopic`, `channels.editForumTopic`
  - Bot must be admin to create/manage topics
- **Decision**: Forum operations in both MTProto (scan/clone) and Bot API (create/edit when bot is admin)

### 7. Message Entities
- **URL**: https://core.telegram.org/api/entities
- **Type**: Official spec
- **Key findings**:
  - Offsets/lengths are UTF-16 code units
  - `MessageEntityCustomEmoji` carries `custom_emoji_id`
  - Entity passthrough only valid if text is unchanged; any insert/cut must transform offsets
- **Decision**: UTF-16 offset math in caption editor; entity passthrough only when text unchanged

### 8. Obtaining API ID
- **URL**: https://core.telegram.org/api/obtaining_api_id
- **Type**: Official guide
- **Key findings**:
  - `api_id` and `api_hash` are per-application credentials
  - Must not use test credentials in production
  - Each user must create their own app
- **Decision**: api_id/api_hash stored in server secret store; never in browser

### 9. Mini App Validation
- **URL**: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
- **Type**: Official spec
- **Key findings**:
  - `initData` must be verified via HMAC-SHA256 with bot token as key
  - `auth_date` must be checked for freshness (max 24h)
  - Never trust `initDataUnsafe`
- **Decision**: Backend validates initData if Mini App is ever added; currently not in scope

### 10. FloodWait / 420 Errors
- **URL**: https://core.telegram.org/api/errors#420-flood
- **Type**: Official spec
- **Key findings**:
  - FLOOD_WAIT_X: wait X seconds before retrying
  - Per-method, per-account limits; no global constant
  - Persisting `not_before` is required for durable job queue
- **Decision**: Jobs persist FloodWait deadline in DB; worker checks `not_before` before picking

---

## Upstream Libraries

### Telethon (Codeberg — primary source)
- **URL**: https://codeberg.org/Lonami/Telethon
- **Author**: Lonami
- **Type**: Upstream code
- **Version**: 1.37.0 (pinned)
- **License**: MIT
- **Maintenance**: Active at Codeberg; GitHub mirror is archived redirect
- **Capability**: MTProto full; async; Python 3.7+; `iter_messages`, `ForwardMessagesRequest`, `formatting_entities`, raw API invoke
- **Risks**: v1 maintenance mode (no major new features); TL layer updates still happen
- **Decision**: Primary MTProto adapter; pin to 1.37.0; wrap in adapter interface

### Pyrogram (GitHub — ARCHIVED)
- **URL**: https://github.com/pyrogram/pyrogram
- **Type**: Upstream code (archived)
- **License**: LGPL-3.0
- **Maintenance**: README explicitly states "no longer maintained"
- **Decision**: Do NOT use for new code; migrate existing v30 tool patterns to Telethon adapter

### Hydrogram
- **URL**: https://github.com/hydrogram/hydrogram
- **Type**: Upstream code (Pyrogram fork)
- **License**: LGPL-3.0
- **Maintenance**: Active, small community
- **Decision**: Candidate if Telethon migration proves impossible; LGPL requires consideration for distribution

### Pyrofork
- **URL**: https://github.com/Mayuri-Chan/pyrofork
- **Type**: Upstream code (Pyrogram fork)
- **License**: LGPL-3.0
- **Decision**: Short-term bridge if needed; not primary choice

### aiogram 3.x
- **URL**: https://github.com/aiogram/aiogram
- **Type**: Upstream code
- **License**: MIT
- **Maintenance**: Active, Bot API parity
- **Version**: 3.20.0 (pinned)
- **Capability**: Fully async, all Bot API methods, FSM, middleware
- **Decision**: Primary Bot API adapter

### python-telegram-bot
- **URL**: https://github.com/python-telegram-bot/python-telegram-bot
- **Type**: Upstream code
- **License**: LGPL-3.0 (note: dual GPL/LGPL in repo)
- **Decision**: Not chosen; LGPL concern + would mix two bot frameworks

### TDLib
- **URL**: https://github.com/tdlib/td
- **License**: BSL-1.0
- **Decision**: Not chosen; native library complexity exceeds need

---

## Security / Architecture Sources

### OWASP Session Management Cheat Sheet
- **URL**: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- **Type**: Security reference
- **Decision**: HttpOnly, Secure, SameSite=Strict cookies; 30-minute session timeout; fixed-size random token

### OWASP CSRF Prevention
- **URL**: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- **Type**: Security reference
- **Decision**: Double-submit cookie pattern + custom header for state-changing API calls

---

## Decision Matrix: Library Selection

| Criterion | Telethon 1.37 | Pyrogram (archived) | Hydrogram | Pyrofork |
|---|---|---|---|---|
| MTProto capability | Full | Full | Full | Full |
| Async | ✅ | ✅ | ✅ | ✅ |
| Maintenance | Active (bugfix) | ❌ Archived | Active (small) | Active |
| License | MIT ✅ | LGPL-3.0 | LGPL-3.0 | LGPL-3.0 |
| Python 3.12 | ✅ | Uncertain | ✅ | ✅ |
| Forum topics | ✅ raw API | Via raw API | Via raw API | Via raw API |
| Migration cost | Low (adapt v30) | N/A | Medium | Medium |
| **Decision** | **✅ PRIMARY** | ❌ | Reserve | Reserve |

| Criterion | aiogram 3.x | python-telegram-bot |
|---|---|---|
| Bot API | Full | Full |
| Async | ✅ | Partial (v20+) |
| License | MIT ✅ | LGPL-3.0 |
| Maintenance | Active | Active |
| **Decision** | **✅ PRIMARY** | ❌ |

| Criterion | FastAPI | Flask |
|---|---|---|
| OpenAPI | Built-in ✅ | Manual/plugin |
| Async | Native | Thread-based |
| Validation | Pydantic ✅ | Manual |
| **Decision** | **✅ PRIMARY** | ❌ |

| Criterion | SQLAlchemy async + Alembic | Raw sqlite3 |
|---|---|---|
| Migrations | Versioned ✅ | Manual |
| Type-safe | ✅ | No |
| Multi-DB | ✅ | No |
| **Decision** | **✅ PRIMARY** | ❌ |
