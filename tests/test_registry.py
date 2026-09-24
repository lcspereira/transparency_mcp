"""Tests for the fetcher registry and the @register_fetcher decorator."""

from __future__ import annotations

import pytest

from transparency_mcp.adapters import available_sources, build_fetcher
from transparency_mcp.adapters.base_fetcher import AbstractFetcher
from transparency_mcp.adapters.registry import (
    _Registry,
    all_source_infos,
    register_fetcher,
)
from transparency_mcp.domain.enums import Country, Format, RecordKind


def test_real_fetchers_are_registered():
    names = available_sources()
    assert "usaspending-agencies" in names
    assert "treasury-debt-to-penny" in names
    assert "ofac-sanctions-programs" in names


def test_all_source_infos_exposes_metadata():
    infos = {i.name: i for i in all_source_infos()}
    us = infos["usaspending-agencies"]
    assert us.country is Country.US
    assert us.format is Format.REST
    assert us.kind is RecordKind.SPENDING
    assert "outlay_amount" in us.fields


def test_duplicate_registration_is_rejected():
    class Dup(AbstractFetcher):
        async def fetch_raw(self, params):  # noqa: ANN001
            return b""

        def parse(self, raw):  # noqa: ANN001
            return []

    with pytest.raises(ValueError, match="already registered"):
        register_fetcher("usaspending-agencies")(Dup)


def test_custom_fetcher_registers_and_builds():
    class _Noop:
        async def get(self, *a, **k):  # noqa: ANN001
            return b""

        async def close(self):
            return None

    @register_fetcher("test-dummy")
    class Dummy(AbstractFetcher):
        title = "Dummy"
        country = Country.GENERIC
        format = Format.JSON
        kind = RecordKind.GENERIC

        async def fetch_raw(self, params):  # noqa: ANN001
            return b"[]"

        def parse(self, raw):  # noqa: ANN001
            return []

    assert "test-dummy" in available_sources()
    fetcher = build_fetcher("test-dummy", _Noop())
    assert fetcher.name == "test-dummy"
    # Clean up so the autouse fixture restore logic is happy.
    _Registry.pop("test-dummy", None)


def test_build_unknown_fetcher_raises():
    with pytest.raises(KeyError, match="Unknown transparency source"):
        build_fetcher("does-not-exist", None)  # type: ignore[arg-type]
