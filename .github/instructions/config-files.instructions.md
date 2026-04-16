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


### Config Loading Pattern

```python
from core.utils.config import load_config

config = load_config("config/llm/providers.yaml")
# Automatically resolves ${ZAI_API_KEY} from environment
```
