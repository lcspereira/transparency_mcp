"""FastMCP server instance and lifespan wiring.

Defines the module-level ``mcp`` object used by ``tools.py`` and ``prompts.py``.
The lifespan opens and closes the shared ``aiohttp`` client session and ensures
the adapters package is imported so fetchers self-register before the first
request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from ..adapters import (
    AioHttpHttpClient,
    available_sources,  # noqa: F401 (import side-effects register fetchers)
)
from ..config import get_settings


@asynccontextmanager
async def lifespan(_app: FastMCP) -> AsyncIterator[dict]:
    http = AioHttpHttpClient()
    try:
        yield {"http": http, "settings": get_settings()}
    finally:
        await http.close()


mcp = FastMCP(
    name="transparency-mcp",
    instructions=(
        "MCP server to analyze government transparency data. Use `list_sources` "
        "to discover data sources, `fetch_data` to pull records, and `analyze` "
        "to compute aggregate metrics (top_n, sum, average, count, trend)."
    ),
    lifespan=lifespan,
    mask_error_details=False,
)

# Importing tools/prompts registers them on `mcp` via the @mcp.tool /
# @mcp.prompt decorators. Done at the bottom so `mcp` is defined first.
from . import (
    prompts,  # noqa: E402,F401
    tools,  # noqa: E402,F401
)
