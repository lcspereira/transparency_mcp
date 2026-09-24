"""A fake ``HttpClientPort`` for tests — no network, no aiohttp mocking."""

from __future__ import annotations

from typing import Any

from transparency_mcp.domain.ports import HttpClientPort


class FakeHttpClient(HttpClientPort):
    """Returns canned bytes keyed by URL (before the query string)."""

    def __init__(self, mapping: dict[str, bytes] | None = None) -> None:
        self._mapping = mapping or {}
        self.calls: list[tuple[str, dict[str, Any] | None, dict[str, str] | None]] = []
        self.closed = False

    def register(self, url: str, body: bytes) -> None:
        self._mapping[url.split("?", maxsplit=1)[0]] = body

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        self.calls.append((url, params, headers))
        key = url.split("?", maxsplit=1)[0]
        if key in self._mapping:
            return self._mapping[key]
        raise KeyError(f"FakeHttpClient has no canned response for {url!r}")

    async def close(self) -> None:
        self.closed = True
