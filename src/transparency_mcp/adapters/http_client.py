"""aiohttp-backed HTTP client provider.

Implements ``HttpClientPort`` from the domain layer. The client session is
created lazily and must be closed via ``close()`` (the MCP lifespan takes care
of that). Keeping HTTP I/O in a single component makes it trivial to mock in
tests and enforces the Clean Architecture boundary: no other module imports
``aiohttp`` directly.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from ..config import get_settings
from ..domain.ports import HttpClientPort


class AioHttpHttpClient(HttpClientPort):
    """Concrete ``HttpClientPort`` backed by a single shared ``aiohttp.ClientSession``."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            settings = get_settings()
            timeout = aiohttp.ClientTimeout(total=settings.http_timeout)
            headers = {"User-Agent": settings.http_user_agent, "Accept": "application/json, text/*"}
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        session = await self._ensure_session()
        async with session.get(url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None
