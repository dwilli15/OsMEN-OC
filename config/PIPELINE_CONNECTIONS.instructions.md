# Config Pipeline Connections

Operator reference for pipeline, credential, and runtime config wiring inside `config/`.

`[CFG-PIPELINES]`
Primary pipeline routing lives in `config/pipelines.yaml`.
Each pipeline defines:
- trigger source (`cron` or `event`)
- trigger value (`schedule` or Redis stream)
- ordered steps (`agent`, `tool`, optional `parameters`, optional `depends_on`)

Runtime consumer:
- `core/pipelines/runner.py`

`[CFG-AGENTS]`
Per-agent runtime settings live in `config/agents.yaml`.
These settings are not secrets by themselves, but many entries are secret-backed via `${ENV_VAR}` interpolation.

Current credential-connected entries include:
- `daily_brief.llm_api_key -> ${ZAI_API_KEY}`
- `knowledge_librarian.llm_api_key -> ${ZAI_API_KEY}`
- `focus_guardrails.llm_api_key -> ${ZAI_API_KEY}`
- `research.llm_api_key -> ${ZAI_API_KEY}`
- `media_organization.plex_library_root -> ${PLEX_LIBRARY_ROOT}`
- `media_organization.download_staging -> ${DOWNLOAD_STAGING_DIR}`
- `taskwarrior_sync.google_calendar_credentials -> ${GOOGLE_CALENDAR_CREDENTIALS_PATH}`

`[CFG-SECRETS-REGISTRY]`
Secret metadata source of truth lives in `config/secrets-registry.yaml`.
This file must contain metadata only, never values.

For each secret-bearing integration, track:
- where the secret lives (`env`, `sops`, `podman`, `keyring`, `openclaw`)
- who requires it (`required_by`)
- how it is provisioned (`auth_flow`, `podman_name`, `env_var`, `openclaw_ref`)

`[CFG-GOOGLE-OAUTH]`
Google OAuth wiring currently spans four config surfaces:
1. `config/secrets-registry.yaml -> google_oauth_tokens`
2. `config/secrets/oauth-tokens.template.yaml`
3. `config/agents.yaml -> taskwarrior_sync.google_calendar_credentials`
4. local runtime env file `~/.config/osmen/env -> GOOGLE_CALENDAR_CREDENTIALS_PATH`

Important distinction:
- `GOOGLE_CALENDAR_CREDENTIALS_PATH` points to the OAuth client credentials JSON used by runtime integrations.
- live refresh/access tokens are not committed and are not stored in repo config.
- live tokens belong in the provider keyring (`gog`) plus local SOPS backup only.

`[CFG-OAUTH-TEMPLATE]`
Committed token templates live in `config/secrets/*.template.yaml`.
These files exist only to show expected structure and key names.
They must never contain plaintext values, copied browser redirects, refresh tokens, access tokens, or client secrets.

`[CFG-LOCAL-ONLY]`
Live encrypted backups live outside the repo:
- `~/.config/osmen/secrets/*.enc.yaml`

Repo config stays public-safe by following this split:
- repo: placeholders and metadata only
- local env: runtime paths and non-committed values
- local SOPS: encrypted backups
- provider keyring / Podman secrets: active runtime secret stores

`[CFG-SEARCH-TAGS]`
Search these tags when resuming config work:
- `[CFG-PIPELINES]`
- `[CFG-AGENTS]`
- `[CFG-SECRETS-REGISTRY]`
- `[CFG-GOOGLE-OAUTH]`
- `[CFG-OAUTH-TEMPLATE]`
- `[CFG-LOCAL-ONLY]`