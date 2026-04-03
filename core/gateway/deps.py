"""FastAPI dependency injection stubs.

These providers are injected into route handlers via ``Depends()``.
All clients are initialized once at startup (stored in ``app.state``) and
retrieved here without re-allocating on every request.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request


def get_mcp_registry(request: Request) -> dict[str, Any]:
    """Return the MCP tool registry stored in app state.

    Populated during the ``lifespan`` startup phase in ``app.py``.
    """
    return request.app.state.mcp_registry  # type: ignore[no-any-return]


MCPRegistry = Annotated[dict[str, Any], Depends(get_mcp_registry)]
