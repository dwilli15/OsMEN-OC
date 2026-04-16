---
applyTo: "config/**/*.yaml"
---

## Config YAML Conventions

- All configuration lives in `config/` — code reads config, never hardcodes values
- Use `${ENV_VAR}` syntax for values that must come from environment (resolved by `core/utils/config.py`)
- 2-space indentation
- Comments explaining non-obvious values
- Group related settings under descriptive keys

### Secret Config

<<<<<<< HEAD
Files in `config/secrets/` are public-safe templates only.

- Use `.template.yaml` for committed files that define expected keys and placeholder values.
- Store live SOPS-encrypted secret backups outside the repo at `~/.config/osmen/secrets/*.enc.yaml`.
- Runtime services should receive secrets from Podman secrets or `${ENV_VAR}` resolution, never from committed files.

When adding a new secret-bearing integration:

1. Update the committed template in `config/secrets/`.
2. Update the local encrypted file in `~/.config/osmen/secrets/`.
3. Update the Podman secret creation/rotation workflow.
4. Verify the repo still contains templates only.

Never put plaintext secrets in any repo config file.
=======
Files in `config/secrets/` use `.enc.yaml` extension (SOPS + age encrypted).

- `api-keys.enc.yaml` — LLM provider keys, service API keys
- `service-creds.enc.yaml` — database passwords, VPN credentials

Never put plaintext secrets in any config file. Use `${ENV_VAR}` or SOPS encryption.
>>>>>>> origin/main

### Config Loading Pattern

```python
from core.utils.config import load_config

config = load_config("config/llm/providers.yaml")
# Automatically resolves ${ZAI_API_KEY} from environment
```
