---
applyTo: "core/**/*.py"
---

## Python Module Conventions

- All modules in `core/` are part of the `core` package (importable via `import core.events.bus`)
- Every `__init__.py` should export the public API of its subpackage
- Use `from __future__ import annotations` at top of every file
- Pydantic models for all data structures that cross module boundaries
- Use `@dataclass` for internal-only structures
- Async functions for all I/O operations (database, HTTP, Redis, file system)
- Sync wrappers only at CLI entry points

## Error Handling

- Custom exception hierarchy rooted at `core.utils.exceptions.OsMENError`
- Never catch bare `Exception` — catch specific types
- Log errors with `loguru` before re-raising
- Return structured error responses from gateway (JSON with `error`, `detail`, `correlation_id`)

## Dependency Injection

- Use `core/gateway/deps.py` for FastAPI dependency injection
- Redis, PostgreSQL, ChromaDB clients initialized once, injected via `Depends()`
- Config loaded once at startup via `core/utils/config.py`, injected to modules that need it

## Testing

- Test files mirror source structure: `core/events/bus.py` → `tests/test_events.py`
- Use `@pytest.mark.anyio` for async tests
- Fixtures in `tests/conftest.py`: mock Redis, test PG database, ephemeral ChromaDB
- Stub implementations are acceptable — use `pass` body with correct signature and return type
