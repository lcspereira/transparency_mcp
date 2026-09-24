"""Adapters layer: I/O-bound fetchers and the HTTP client.

Importing this package imports all registered fetchers so they self-register
in the global registry. The MCP and analysis layers depend only on the
registry + ports, never on concrete fetcher classes.
"""

# Importing the modules below registers the fetchers via the @register_fetcher
# decorator at import time.
from . import (
    csv_fetcher,  # noqa: F401
    html_table_fetcher,  # noqa: F401
    rest_json_fetcher,  # noqa: F401
)
from .base_fetcher import AbstractFetcher
from .http_client import AioHttpHttpClient
from .registry import all_source_infos, available_sources, build_fetcher, register_fetcher

__all__ = [
    "AbstractFetcher",
    "AioHttpHttpClient",
    "available_sources",
    "all_source_infos",
    "build_fetcher",
    "register_fetcher",
]
