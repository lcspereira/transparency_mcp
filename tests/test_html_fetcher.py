"""Tests for the OFAC HTML table-scraping fetcher (HTTP port mocked)."""

from __future__ import annotations

import pytest

from tests.conftest import fixture_bytes  # type: ignore[import-not-found]
from tests.fake_http import FakeHttpClient
from transparency_mcp.adapters.html_table_fetcher import OfacSanctionsHtmlFetcher
from transparency_mcp.domain.models import FetchParams


@pytest.mark.asyncio
async def test_ofac_html_parse_and_normalize():
    http = FakeHttpClient()
    http.register(
        "https://ofac.treasury.gov/sanctions-programs-and-country-information",
        fixture_bytes("ofac_sanctions.html"),
    )
    fetcher = OfacSanctionsHtmlFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=100))

    assert dataset.source == "ofac-sanctions-programs"
    assert len(dataset.records) == 3
    belarus = next(r for r in dataset.records if r.entity == "Belarus Sanctions")
    assert belarus.fields["program"] == "Belarus Sanctions"
    assert belarus.fields["url"] == "/sanctions-programs-and-country-information/belarus-sanctions"
    assert belarus.date is not None
    assert belarus.date.isoformat() == "2026-07-23"


@pytest.mark.asyncio
async def test_ofac_html_program_filter_passes_query_param():
    http = FakeHttpClient()
    http.register(
        "https://ofac.treasury.gov/sanctions-programs-and-country-information",
        fixture_bytes("ofac_sanctions.html"),
    )
    fetcher = OfacSanctionsHtmlFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=100, filters={"program": "Belarus"}))
    called_url = http.calls[0][0]
    assert "?filter=Belarus" in called_url
    # The fixture returns all 3 (no real server-side filtering on the mock).
    assert len(dataset.records) == 3


@pytest.mark.asyncio
async def test_ofac_html_handles_missing_table():
    http = FakeHttpClient()
    http.register(
        "https://ofac.treasury.gov/sanctions-programs-and-country-information",
        b"<html><body><p>no table here</p></body></html>",
    )
    fetcher = OfacSanctionsHtmlFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=100))
    assert dataset.records == []
