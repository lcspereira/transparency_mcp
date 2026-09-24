"""End-to-end style tests of the MCP tools using an in-process FastMCP Client.

We register a fake fetcher that returns canned records without any network
I/O, then call the real ``list_sources``/``fetch_data``/``analyze`` tools
through the MCP protocol via FastMCP's Client. This validates the full
delivery wiring (lifespan DI, registry lookup, tool schemas, analysis
delegation) without hitting real government APIs.
"""

from __future__ import annotations

import pytest
from fastmcp import Client

from transparency_mcp.adapters.base_fetcher import AbstractFetcher
from transparency_mcp.adapters.registry import (  # type: ignore[attr-defined]
    _Registry,
    register_fetcher,
)
from transparency_mcp.domain.enums import Country, Format, RecordKind
from transparency_mcp.domain.models import FetchParams, Record
from transparency_mcp.domain.ports import HttpClientPort
from transparency_mcp.mcp.server import mcp


class _StaticHttp(HttpClientPort):
    """HTTP client that returns canned fixture bytes for known URLs."""

    def __init__(self, mapping: dict[str, bytes]) -> None:
        self._mapping = mapping
        self.closed = False

    async def get(self, url, *, params=None, headers=None):  # noqa: ANN001
        # Normalize URL to before the query string for fixture lookup.
        key = url.split("?")[0]
        if key in self._mapping:
            return self._mapping[key]
        # USAspending base + path
        return self._mapping.get(url, b"")

    async def close(self) -> None:
        self.closed = True


class _FakeFetcher(AbstractFetcher):
    title = "Fake Source"
    country = Country.US
    format = Format.JSON
    kind = RecordKind.SPENDING
    fields = ["agency_name", "outlay_amount"]
    sample_params = {"limit": 100}

    async def fetch_raw(self, params: FetchParams) -> bytes:  # noqa: ANN001
        return b"[]"

    def parse(self, raw: bytes) -> list[dict]:  # noqa: ANN001
        return []

    async def fetch(self, params: FetchParams):
        # Bypass I/O entirely: return a fixed dataset.
        from transparency_mcp.domain.models import Dataset

        records = [
            Record(
                source=self.name,
                kind=self.kind,
                country=self.country,
                entity="A",
                value=100.0,
                value_label="outlay_amount",
                fields={"agency_name": "A", "outlay_amount": 100.0},
            ),
            Record(
                source=self.name,
                kind=self.kind,
                country=self.country,
                entity="B",
                value=300.0,
                value_label="outlay_amount",
                fields={"agency_name": "B", "outlay_amount": 300.0},
            ),
        ]
        return Dataset(source=self.name, records=records[: params.limit])


@pytest.fixture
def fake_fetcher():
    """Register a throwaway fake fetcher for the duration of the test."""
    name = "fake-source"

    @register_fetcher(name)
    class Fake(_FakeFetcher):
        pass

    yield name
    _Registry.pop(name, None)


@pytest.mark.asyncio
async def test_list_sources_returns_real_and_fake(fake_fetcher):
    async with Client(mcp) as client:
        result = await client.call_tool("list_sources", {"country": "US"})
    names = (
        {item["name"] for item in result.structured_content.get("result", [])}
        if isinstance(result.structured_content, dict)
        else set()
    )
    # Fallback: parse text content if structured_content shape differs
    if not names:
        import json

        text = result.content[0].text if result.content else "[]"
        parsed = json.loads(text)
        names = {i.get("name") for i in parsed}
    assert "usaspending-agencies" in names
    assert fake_fetcher in names


@pytest.mark.asyncio
async def test_fetch_data_via_mcp(fake_fetcher):
    async with Client(mcp) as client:
        result = await client.call_tool("fetch_data", {"source": fake_fetcher, "limit": 10})
    import json

    text = result.content[0].text if result.content else "[]"
    records = json.loads(text)
    assert len(records) == 2
    assert {r["entity"] for r in records} == {"A", "B"}


@pytest.mark.asyncio
async def test_analyze_via_mcp(fake_fetcher):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "analyze",
            {
                "source": fake_fetcher,
                "metric": "top_n",
                "field": "outlay_amount",
                "by": "agency_name",
                "top_n": 5,
            },
        )
    import json

    text = result.content[0].text if result.content else "{}"
    parsed = json.loads(text)
    assert parsed["metric"] == "top_n"
    assert parsed["result"][0] == {"key": "B", "value": 300.0}
    assert parsed["result"][1] == {"key": "A", "value": 100.0}


@pytest.mark.asyncio
async def test_source_schema_via_mcp(fake_fetcher):
    async with Client(mcp) as client:
        result = await client.call_tool("source_schema", {"name": fake_fetcher})
    import json

    parsed = json.loads(result.content[0].text)
    assert parsed["name"] == fake_fetcher
    assert "outlay_amount" in parsed["fields"]


@pytest.mark.asyncio
async def test_fetch_data_unknown_source_raises():
    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool("fetch_data", {"source": "no-such-source", "limit": 1})
