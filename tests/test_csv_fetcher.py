"""Tests for the Treasury Fiscal Data CSV fetcher (HTTP port mocked)."""

from __future__ import annotations

import pytest

from tests.conftest import fixture_bytes  # type: ignore[import-not-found]
from tests.fake_http import FakeHttpClient
from transparency_mcp.adapters.csv_fetcher import TreasuryCsvFetcher
from transparency_mcp.domain.models import FetchParams


@pytest.mark.asyncio
async def test_treasury_csv_parse_and_normalize():
    http = FakeHttpClient()
    http.register(
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
        fixture_bytes("treasury_debt.csv"),
    )
    fetcher = TreasuryCsvFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=100))

    assert dataset.source == "treasury-debt-to-penny"
    assert len(dataset.records) == 4
    first = dataset.records[0]
    assert first.entity == "U.S. Federal Debt"
    assert first.value == pytest.approx(33_350_000_000_000.00)
    assert first.value_label == "tot_pub_debt_out_amt"
    assert first.date is not None
    assert first.date.isoformat() == "2024-01-02"
    assert first.fields["record_fiscal_year"] == "2024"


@pytest.mark.asyncio
async def test_treasury_csv_date_filter_translates_to_query():
    http = FakeHttpClient()
    http.register(
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
        fixture_bytes("treasury_debt.csv"),
    )
    fetcher = TreasuryCsvFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=100, filters={"record_date": "gte:2024-01-01"}))
    # Confirm the filter was encoded into the request URL.
    called_url = http.calls[0][0]
    assert (
        "filter=record_date%3Agte%3A2024-01-01" in called_url
        or "filter=record_date:gte:2024-01-01" in called_url
    )
    assert len(dataset.records) == 4


@pytest.mark.asyncio
async def test_treasury_csv_skips_rows_without_total():
    csv_with_null = (
        b'"record_date","debt_held_public_amt","intragov_hold_amt","tot_pub_debt_out_amt","record_fiscal_year"\n'
        b'"2024-01-02","1.0","2.0","3.0","2024"\n'
        b'"2024-01-03","null","null","null","2024"\n'
    )
    http = FakeHttpClient()
    http.register(
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
        csv_with_null,
    )
    fetcher = TreasuryCsvFetcher(http)
    dataset = await fetcher.fetch(FetchParams(limit=100))
    assert len(dataset.records) == 1
    assert dataset.records[0].value == 3.0
