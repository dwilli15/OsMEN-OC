# Scripts Pipeline Connections

Operator reference for script-level deployment and credential handling entry points inside `scripts/`.

`[SCRIPT-QUADLETS]`
`scripts/deploy_quadlets.sh` deploys Quadlet unit files from `quadlets/` into `~/.config/containers/systemd/`.

This script connects:
- repo unit definitions
- user systemd registration
- later runtime secret injection through Quadlet `Secret=` mappings

It does not create secrets itself.
It assumes required Podman secrets already exist when services are started.

`[SCRIPT-CREDENTIAL-KIT]`
`scripts/secrets/export_credential_kit.sh` exports decrypted local SOPS backups plus Podman secrets into a plaintext offline kit.

This script is intentionally high-risk and must be treated as an offline recovery/export path only.

Rules:
- output is plaintext
- store offline only
- remove stale exports
- never commit the generated files

`[SCRIPT-GOOGLE-OAUTH]`
Google OAuth provisioning is a local operator workflow, not a committed script.

Current local flow:
1. download client credentials JSON locally
2. register it with `gog auth credentials set`
3. run `gog auth add ...`
4. keep active tokens in the `gog` keyring
5. capture backup material into local SOPS
6. remove plaintext downloads after backup is verified

Current plaintext client credentials path in use:
- `/home/dwill/Downloads/credentials.json`

That file is temporary and must not be copied into the repo.

`[SCRIPT-SEARCH-TAGS]`
Search these tags when resuming script-side secret work:
- `[SCRIPT-QUADLETS]`
- `[SCRIPT-CREDENTIAL-KIT]`
- `[SCRIPT-GOOGLE-OAUTH]`