# Core Pipeline Connections

Operator reference for pipeline execution, env resolution, setup writes, and secret verification inside `core/`.

`[CORE-PIPELINE-RUNNER]`
`core/pipelines/runner.py` loads `config/pipelines.yaml`, resolves triggers, and dispatches pipeline steps.

Key behavior:
- cron pipelines are evaluated in-process
- event pipelines subscribe to Redis stream keys
- steps run through the approval gate before tool execution
- completion/audit behavior is handled by the runner and related gateway components

`[CORE-CONFIG-LOADER]`
`core/utils/config.py` is the config interpolation boundary.
It resolves `${ENV_VAR}` placeholders from the process environment.

Connection rule:
- if a value in `config/*.yaml` references `${SOME_VAR}`
- then `SOME_VAR` must be present in the runtime environment before the config is loaded

`[CORE-SETUP-WRITES]`
`core/setup/wizard.py` writes operator-provided runtime values to:
- `~/.config/osmen/env`
- `config/openclaw.yaml`

Current wizard-managed env values include:
- `ZAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `OPENCLAW_WS_URL`
- `PLEX_LIBRARY_ROOT`
- `DOWNLOAD_STAGING_DIR`
- `POSTGRES_DSN`
- `REDIS_URL`

If a new pipeline or agent depends on an env var, update the wizard or document why that variable is managed elsewhere.

`[CORE-SECRETS-CUSTODIAN]`
`core/secrets/custodian.py` audits the active secret stores against `config/secrets-registry.yaml`.

Audit surfaces include:
- env file presence and permissions
- missing env-backed keys
- missing Podman secrets
- missing local SOPS encrypted files

Use the custodian to verify that repo metadata and local runtime stores still agree.

`[CORE-GOOGLE-OAUTH]`
Google OAuth is intentionally split across runtime boundaries:
- provider client credentials JSON: local file path referenced by `GOOGLE_CALENDAR_CREDENTIALS_PATH`
- active tokens: `gog` keyring state under `~/.config/gogcli/`
- encrypted backup: `~/.config/osmen/secrets/oauth-tokens.enc.yaml`
- repo template: `config/secrets/oauth-tokens.template.yaml`

No code in `core/` should expect live Google tokens to exist in committed YAML.

`[CORE-SEARCH-TAGS]`
Search these tags when tracing runtime wiring:
- `[CORE-PIPELINE-RUNNER]`
- `[CORE-CONFIG-LOADER]`
- `[CORE-SETUP-WRITES]`
- `[CORE-SECRETS-CUSTODIAN]`
- `[CORE-GOOGLE-OAUTH]`