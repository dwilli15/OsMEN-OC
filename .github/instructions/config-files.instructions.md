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

Files in `config/secrets/` use `.enc.yaml` extension (SOPS + age encrypted).

- `api-keys.enc.yaml` — LLM provider keys, service API keys
- `service-creds.enc.yaml` — database passwords, VPN credentials

Never put plaintext secrets in any config file. Use `${ENV_VAR}` or SOPS encryption.

### Config Loading Pattern

```python
from core.utils.config import load_config

config = load_config("config/llm/providers.yaml")
# Automatically resolves ${ZAI_API_KEY} from environment
```
