"""Tests for the USAspending REST/JSON fetcher (HTTP port mocked)."""

from __future__ import annotations

import pytest

from tests.conftest import fixture_bytes  # type: ignore[import-not-found]
from tests.fake_http import FakeHttpClient
from transparency_mcp.adapters.rest_json_fetcher import USAspendingFetcher
from transparency_mcp.domain.models import FetchParams


@pytest.mark.asyncio
async def test_usaspending_parse_and_normalize():
    http = FakeHttpClient()
    http.register(
        "https://api.usaspending.gov/api/v2/references/toptier_agencies/",
        fixture_bytes("usaspending_agencies.json"),
    )
    fetcher = USAspendingFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=10))

    assert dataset.source == "usaspending-agencies"
    assert len(dataset.records) == 3
    dod = next(r for r in dataset.records if r.entity == "Department of Defense")
    assert dod.value == pytest.approx(543210987654.32)
    assert dod.value_label == "outlay_amount"
    assert dod.fields["abbreviation"] == "DOD"
    assert dod.fields["agency_slug"] == "department-of-defense"
    assert dod.kind is not None


@pytest.mark.asyncio
async def test_usaspending_limit_truncates():
    http = FakeHttpClient()
    http.register(
        "https://api.usaspending.gov/api/v2/references/toptier_agencies/",
        fixture_bytes("usaspending_agencies.json"),
    )
    fetcher = USAspendingFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=2))
    assert len(dataset.records) == 2


@pytest.mark.asyncio
async def test_usaspending_info_metadata():
    fetcher = USAspendingFetcher(FakeHttpClient())
    info = fetcher.info()
    assert info.name == "usaspending-agencies"
    assert "outlay_amount" in info.fields
