"""Global fetcher registry.

Fetchers register themselves at import time via the ``@register_fetcher``
decorator. The registry decouples the MCP/analysis layer from concrete adapter
classes: tools look up sources by name without knowing their class, which is
what lets developers add a new source without editing MCP code (Open/Closed).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..domain.models import SourceInfo
from ..domain.ports import FetcherPort, HttpClientPort

# name -> factory(fetcher_http_client) -> FetcherPort
_Registry: dict[str, Callable[[HttpClientPort], FetcherPort]] = {}


def register_fetcher(
    name: str | None = None,
) -> Callable[[type], type]:
    """Class decorator that registers a fetcher in the global registry.

    Usage::

        @register_fetcher("usaspending-agencies")
        class USAspendingFetcher(AbstractFetcher):
            ...

    The class must accept an ``HttpClientPort`` as its constructor argument.
    """

    def decorator(cls: type) -> type:
        key = name or getattr(cls, "name", "") or cls.__name__
        if not key:
            raise ValueError(f"Cannot register fetcher {cls!r}: no name provided")
        if key in _Registry:
            raise ValueError(f"A fetcher named {key!r} is already registered")
        _Registry[key] = cls  # type: ignore[assignment]
        cls.name = key
        return cls

    return decorator


def available_sources() -> list[str]:
    """Return the sorted names of all registered fetchers."""
    return sorted(_Registry)


def get_fetcher_factory(name: str) -> Callable[[HttpClientPort], FetcherPort]:
    if name not in _Registry:
        raise KeyError(f"Unknown transparency source {name!r}. Available: {available_sources()}")
    return _Registry[name]  # type: ignore[return-value]


def build_fetcher(name: str, http: HttpClientPort) -> FetcherPort:
    """Instantiate a registered fetcher by name with the given HTTP client."""
    return get_fetcher_factory(name)(http)  # type: ignore[misc]


def all_source_infos() -> list[SourceInfo]:
    """Return ``SourceInfo`` for every registered fetcher, without I/O deps.

    Used to power the ``list_sources`` tool and the ``source://registry``
    resource. We construct a throwaway instance per fetcher only if needed; in
    practice ``info()`` is pure metadata and does not perform I/O.
    """
    infos: list[SourceInfo] = []
    for name, factory in _Registry.items():
        # ``info()`` must not require a live HTTP client. We pass a dummy since
        # well-behaved fetchers only store it, not use it in info().
        dummy: HttpClientPort = _DummyClient()  # type: ignore[abstract]
        try:
            infos.append(factory(dummy).info())  # type: ignore[misc]
        except Exception:  # pragma: no cover - defensive
            infos.append(
                SourceInfo(
                    name=name,
                    title=name,
                    country=_UNSET_COUNTRY,
                    format=_UNSET_FORMAT,
                    kind=_UNSET_KIND,
                )
            )
    return infos


# -- internals ----------------------------------------------------------------

from ..domain.enums import Country as _Country  # noqa: E402
from ..domain.enums import Format as _Format
from ..domain.enums import RecordKind as _Kind

_UNSET_COUNTRY = _Country.GENERIC
_UNSET_FORMAT = _Format.JSON
_UNSET_KIND = _Kind.GENERIC


class _DummyClient:  # pragma: no cover - only used for metadata introspection
    async def get(self, *a: Any, **k: Any) -> bytes:  # noqa: ANN002
        raise RuntimeError("DummyClient is metadata-only")

    async def close(self) -> None:
        return None
