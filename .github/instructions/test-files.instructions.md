---
applyTo: "tests/**/*.py"
---

## Test Conventions

- Framework: `pytest` + `pytest-anyio` (NOT pytest-asyncio)
- Async test marker: `@pytest.mark.anyio`
- Fixtures in `tests/conftest.py`
- Test file naming: `test_{module}.py` (mirrors `core/{module}.py`)

### Required Fixtures (in conftest.py)

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value="msg-id")
    redis.xread = AsyncMock(return_value=[])
    return redis

@pytest.fixture
def mock_pg_pool():
    """Mock PostgreSQL connection pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    return pool

@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock()
    return client
```

### Stub Tests Are Acceptable

For the initial scaffold, test bodies can be stubs:

```python
@pytest.mark.anyio
async def test_event_bus_publish(mock_redis):
    """Test that publishing an event writes to Redis Streams."""
    # TODO: implement
    pass
```

The test must have the correct signature, marker, and fixtures — the body can be `pass`.
