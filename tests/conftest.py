"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

import transparency_mcp.adapters as adapters_pkg
from transparency_mcp.adapters import AioHttpHttpClient
from transparency_mcp.adapters.registry import _Registry  # type: ignore[attr-defined]

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_registry():
    """Snapshot/restore the global fetcher registry around each test.

    The @register_fetcher decorator mutates a module-level dict at import time;
    tests that register throwaway fetchers must not pollute other tests.
    """
    saved = dict(_Registry)
    # Re-import the adapters package so the three real fetchers are registered
    # even if a prior test cleared the registry.
    yield
    _Registry.clear()
    _Registry.update(saved)
    # touch adapters_pkg to keep the import "used"
    assert adapters_pkg is not None


@pytest.fixture
def http_client():
    """A fresh AioHttpHttpClient whose session is created lazily (mocked in tests)."""
    return AioHttpHttpClient()


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()
