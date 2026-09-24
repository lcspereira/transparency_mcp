"""Port definitions (abstract interfaces) for the framework.

This is the contract between the domain/analysis layer and the I/O adapters.
Anything in ``adapters/`` must satisfy these protocols; nothing outside
``adapters/`` may import ``aiohttp`` or ``bs4``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .models import Dataset, FetchParams, SourceInfo


@runtime_checkable
class FetcherPort(Protocol):
    """Contract every transparency fetcher must implement.

    A fetcher is responsible for (a) describing itself, (b) fetching raw bytes,
    (c) parsing them into rows, and (d) normalizing rows into domain Records.
    Concrete adapters extend ``AbstractFetcher`` (Template Method) to get the
    pipeline wired for free.
    """

    name: str

    def info(self) -> SourceInfo:
        """Return the catalog entry describing this source."""
        ...

    async def fetch(self, params: FetchParams) -> Dataset:
        """Fetch and normalize records into a Dataset."""
        ...


class HttpClientPort(Protocol):
    """Minimal HTTP client contract used by fetchers."""

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        """Perform an HTTP GET and return the raw response body."""
        ...

    async def close(self) -> None: ...
