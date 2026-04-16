# Install Audit Findings — 2026-04-07

## Issues Found & Fixed

### 1. Python Binary Mismatch (FIXED)
- **Problem**: `python3` resolves to 3.14.3 on this system; Makefile enforces 3.13 in .venv
- **Fix**: Changed `python3 -m venv` → `python3.13 -m venv` in both Makefile and bootstrap.sh
- **Files**: `Makefile`, `scripts/bootstrap.sh`

### 2. Port Conflict: ChromaDB vs Gateway (FIXED)
- **Problem**: ChromaDB `PublishPort=127.0.0.1:8000:8000` collides with gateway `--port 8000`
- **Fix**: Changed gateway to `--port 8080` in Makefile `dev` target
- **File**: `Makefile`

### 3. Missing migrations/ Directory (FIXED)
- **Problem**: `core/audit/trail.py` expects `audit_trail` and `audit_archive` tables; no schema existed
- **Fix**: Created `migrations/001_initial_schema.sql` with full schema (audit_trail, audit_archive, schema_version, pgvector extension)
- **File**: `migrations/001_initial_schema.sql`

### 4. temp_1st_install/ Not in .gitignore (FIXED)
- **Fix**: Added `temp_1st_install/` to `.gitignore`
- **File**: `.gitignore`

## Verified OK (No Action Needed)

- All 8 agent manifests: valid schema, 32 tools, correct risk levels
- All core Python modules: fully implemented (no stubs), clean imports
- All quadlets: pinned images, health checks, ReadOnly, NoNewPrivileges
- All scripts: idempotent, pkexec, --dry-run support
- Config files: 8 ${ENV_VAR} references, all resolved by setup wizard
- Tests: ~90% coverage, stubs clearly marked, conftest.py complete
- Setup wizard: writes to ~/.config/osmen/env (chmod 600) + config/openclaw.yaml

## Port Allocation (Post-Fix)

| Service | Port | Binding |
|---------|------|---------|
| PostgreSQL | 5432 | 127.0.0.1 |
| Redis | 6379 | 127.0.0.1 |
| ChromaDB | 8000 | 127.0.0.1 |
| Gateway (uvicorn) | 8080 | 127.0.0.1 |
| OpenClaw WS bridge | 18789 | 127.0.0.1 |

## Environment Variables Required (8 total)

| Variable | Source | Required |
|----------|--------|----------|
| ZAI_API_KEY | Zhipu GLM API | Yes |
| TELEGRAM_BOT_TOKEN | @BotFather | Yes |
| TELEGRAM_CHAT_ID | Telegram group/chat | Yes |
| DISCORD_BOT_TOKEN | Discord Dev Portal | No |
| DISCORD_GUILD_ID | Discord server | No |
| PLEX_LIBRARY_ROOT | Local path | No (deferred) |
| DOWNLOAD_STAGING_DIR | Local path | No (deferred) |
| GOOGLE_CALENDAR_CREDENTIALS_PATH | Google OAuth JSON | No (deferred) |
