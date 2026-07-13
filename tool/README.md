# UpBain Control

Web admin dashboard for Telegram channel management. Local-first, single-admin application.

## Requirements

- Python 3.12+
- Node.js 22+ (for frontend build)

## Quick Start

```bash
# 1. Install backend dependencies
pip install -r tool/requirements.txt

# 2. Build frontend
cd tool/frontend && npm install && npm run build && cd ../..

# 3. Set secrets (required before production use)
export UPBAIN_ADMIN_PASSWORD=your_strong_password
export UPBAIN_SECRET_KEY=your_32_char_secret_key
export UPBAIN_DATA_DIR=/path/to/data  # defaults to tool/data/

# 4. Start server
cd tool && python run.py

# Server starts at http://127.0.0.1:8000
# API docs: http://127.0.0.1:8000/api/docs
```

## Default Credentials

On first start, admin user `admin` is created with password from `UPBAIN_ADMIN_PASSWORD` (default: `changeme`).

**Always change the default password before use.**

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `UPBAIN_ADMIN_PASSWORD` | `changeme` | Admin password (used only on first init) |
| `UPBAIN_SECRET_KEY` | (insecure dev key) | Key for session signing and secret encryption |
| `UPBAIN_DATA_DIR` | `./data` | Data directory for DB, backups, sessions |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/upbain.db` | Database URL |
| `PORT` | `8000` | HTTP port |
| `HOST` | `127.0.0.1` | Bind address |
| `CORS_ALLOWED_ORIGINS` | localhost:3000,8000 | Comma-separated CORS origins |
| `SESSION_MAX_AGE` | `1800` | Session timeout in seconds |

## Running Tests

```bash
cd tool && python -m pytest tests/ -v
```

## Development Mode (Frontend Hot Reload)

```bash
# Terminal 1: Start backend
cd tool && python run.py

# Terminal 2: Start frontend dev server with proxy
cd tool/frontend && npm run dev
# Frontend at http://localhost:3000
```

## Backup and Restore

```bash
# Create backup via API
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/backup/run-now \
  -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF"

# List backups
curl -s -b cookies.txt http://127.0.0.1:8000/api/backup/list

# Restore (UI)
# Go to Backup & Dữ liệu tab → Upload zip → Restore
```

## Security Notes

- Session cookie: HttpOnly, SameSite=Strict, 30-minute timeout
- CSRF: X-CSRF-Token header required on all state-changing requests
- Secrets (bot token, api_hash, session): AES-256-GCM encrypted in DB; never returned in API responses
- Login rate limit: 5 attempts per 15 min per IP; lockout after 10 failures
- `.session` files excluded from backups
- All Telegram data uses `textContent` — no XSS via `innerHTML`

## Architecture

```
tool/
├── backend/
│   ├── app.py              # FastAPI app factory
│   ├── api/
│   │   ├── routes/         # REST endpoints (auth, channels, mappings, runtime, SSE, telegram, backup)
│   │   ├── schemas/        # Pydantic request/response models
│   │   └── deps.py         # Auth/CSRF dependencies
│   ├── database/
│   │   ├── base.py         # SQLAlchemy async engine
│   │   ├── models.py       # ORM models
│   │   └── init_db.py      # Schema creation + seeding
│   ├── services/
│   │   ├── auth_service.py # Login, CSRF, rate limit, audit
│   │   ├── job_queue.py    # SQLite-backed async job queue
│   │   ├── log_stream.py   # SSE log streaming
│   │   └── secret_store.py # AES-GCM encrypted secrets
│   ├── telegram/
│   │   ├── adapters/       # Telethon MTProto adapter
│   │   └── fake/           # Fake adapters for testing
│   └── jobs/
│       └── run_mapping.py  # Forward job handler
├── frontend/
│   ├── src/
│   │   ├── api/            # API client + SSE client
│   │   ├── state/          # Reactive state store
│   │   ├── sections/       # Dashboard, channels, mappings, telegram, logs, backup
│   │   └── components/     # Toast, modal
│   └── index.html          # SPA entry point
├── tests/                  # Unit, integration, contract tests
├── docs/                   # Research ledger, ADRs, threat model
└── requirements.txt
```

## Live Telegram Tests

Live Telegram tests require setting:
```bash
export LIVE_TELEGRAM_TESTS=1
export TG_TEST_API_ID=your_api_id
export TG_TEST_API_HASH=your_api_hash
export TG_TEST_PHONE=+66812345678
export TG_TEST_ALLOWED_CHAT=-1001234567890  # allowlisted test chat only
```

**Never run live tests against production channels.**
**Do not paste credentials in chat or logs.**
