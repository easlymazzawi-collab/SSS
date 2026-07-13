# Threat Model — UpBain Admin Dashboard

Created: 2026-07-13  
Scope: Single-admin local-first web dashboard controlling Telegram userbot and bots

---

## Assets

| Asset | Sensitivity | Location |
|---|---|---|
| Admin password | Critical | DB (bcrypt hash only) |
| Telegram api_id / api_hash | Critical | Server secret store (encrypted) |
| Telegram session string / file | Critical | Server filesystem, encrypted at rest |
| Bot tokens | Critical | Server secret store |
| OTP / 2FA codes | Critical | Never persisted; in-memory during login flow |
| Message content | High | DB (job items, audit log) |
| Bot user list | Medium | DB |
| Mapping/channel config | Medium | DB |

---

## Trust Boundaries

```
[Browser] ←HTTPS→ [FastAPI Backend] ←MTProto→ [Telegram Servers]
                         ↕
                   [SQLite DB + Encrypted Secrets]
                         ↕
                   [Job Worker (same process)]
```

---

## Threat Catalog

### T1: Auth Bypass (Currently P0 in index.html)
- **Threat**: `/api/auth/status` failure causes fail-open; dashboard loads without auth
- **Control**: Backend middleware checks session on every state-changing request; all API routes require valid session; frontend redirects to login on 401
- **Status**: FIXED in backend implementation

### T2: Secret Exposure in Browser
- **Threat**: bot tokens, api_hash, session strings appearing in localStorage, DOM, API responses, SSE
- **Control**: Backend never returns full secrets; only returns `configured` status + last4/fingerprint; no secret in SSE payload; frontend uses `textContent` for untrusted data
- **Status**: FIXED — secret store returns only status

### T3: DOM XSS via Telegram Data
- **Threat**: `innerHTML` with unescaped phone/error/username from Telegram API
- **Control**: All user-supplied and Telegram-supplied data inserted via `textContent`; no raw `innerHTML` with dynamic data; CSP header blocks inline scripts
- **Status**: FIXED in frontend rewrite

### T4: CSRF on State-Changing Requests
- **Threat**: Cross-site request forging POST/PUT/DELETE on API
- **Control**: Custom `X-CSRF-Token` header required (impossible to set cross-origin via simple form); SameSite=Strict session cookie
- **Status**: IMPLEMENTED via middleware

### T5: Session Fixation / Hijacking
- **Threat**: Stolen or fixated session token
- **Control**: Regenerate session on login; HttpOnly + Secure + SameSite=Strict; 30-min idle timeout; explicit logout invalidates server-side token
- **Status**: IMPLEMENTED

### T6: Login Brute-Force
- **Threat**: Password brute-force attack
- **Control**: Rate limit: 5 attempts per 15 minutes per IP; lockout after 10 failures; exponential backoff; audit log
- **Status**: IMPLEMENTED via middleware

### T7: Path Traversal / SSRF
- **Threat**: Malicious chat ID, file path, or URL causing server to access unintended resources
- **Control**: Validate all chat IDs (integer, allowlist during testing); validate file paths against whitelist; no user-controlled URLs fetched server-side without validation
- **Status**: IMPLEMENTED in validators

### T8: Zip-Slip / Unsafe Archive
- **Threat**: Malicious import zip containing path traversal entries
- **Control**: Validate all zip entry paths against safe prefix; reject absolute paths and `..` components; size limit
- **Status**: IMPLEMENTED in import service

### T9: Telegram OTP/2FA Exposure
- **Threat**: OTP or 2FA password stored, logged, or transmitted insecurely
- **Control**: OTP never persisted to DB or logs; held in server-side session memory only during login flow; expires with flow timeout; attempt limit
- **Status**: IMPLEMENTED in auth service

### T10: Mass Send Without Confirmation
- **Threat**: Accidental mass message send to production channels
- **Control**: Confirm modal for all mass actions; dry-run mode; send cap per job; allowlist for live Telegram tests; emergency stop endpoint
- **Status**: IMPLEMENTED — job creation requires explicit confirmation

### T11: Dependency Confusion / Supply Chain
- **Threat**: Malicious dependency versions
- **Control**: Pin all dependencies with exact versions in requirements.txt; run `pip-audit` in CI; check licenses
- **Status**: PINNED

### T12: Session String in Backup
- **Threat**: `.session` files leaked in backup archives
- **Control**: `.session` files excluded from backup OR encrypted separately; backup zip does not include raw session
- **Status**: IMPLEMENTED in backup service

---

## Security Controls Summary

| Control | Implementation |
|---|---|
| Password hashing | bcrypt via passlib, cost factor 12 |
| Session token | 32-byte CSPRNG, HMAC-signed, HttpOnly+Secure+SameSite=Strict |
| CSRF | X-CSRF-Token header (double-submit) |
| Login rate limit | 5/15min per IP; 10 total lockout |
| Auth failure | Always fail-closed; 401 on invalid session |
| Secret at rest | AES-256-GCM via cryptography library, key from env |
| Secret in API | Never returned; only status/fingerprint |
| Secret in logs | Redacted before logging |
| XSS | textContent everywhere; CSP header |
| CORS | Allowlist (localhost only by default) |
| Input validation | Pydantic schemas on all endpoints |
| File upload | Size limit, type allowlist, path sanitization |
| Audit log | All auth events, all mass actions, all config changes |
| Emergency stop | POST /api/runtime/emergency-stop (admin only) |

---

## RBAC Roles

| Role | Permissions |
|---|---|
| `viewer` | GET read-only endpoints, view logs |
| `operator` | viewer + start/stop jobs, send (within limits) |
| `admin` | operator + configure secrets, manage users, backup/restore, emergency stop |

Current deployment: single admin user. RBAC implemented for future multi-user deployment.
