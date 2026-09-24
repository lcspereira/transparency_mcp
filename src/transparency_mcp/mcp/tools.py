"""MCP tools exposed to the LLM client.

Each tool is a thin façade that:
1. resolves the shared HTTP client from the FastMCP lifespan (DIP),
2. looks up a fetcher by name in the registry (OCP — no edits here to add a source),
3. delegates work to fetchers or the analysis service (SRP).

All tools are read-only and open-world (they hit external government APIs).
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..adapters import all_source_infos, available_sources, build_fetcher
from ..analysis import analysis_service
from ..config import get_settings
from ..domain.enums import Country, Metric
from ..domain.models import AnalysisResult, FetchParams, Record, SourceInfo
from ..domain.ports import HttpClientPort
from .server import mcp


def _http_from_context(ctx: Context | None) -> HttpClientPort:
    """Resolve the shared aiohttp client stored in the FastMCP lifespan state.

    The lifespan yields a dict ``{"http": AioHttpHttpClient, "settings": ...}``
    which FastMCP exposes via ``ctx.request_context.lifespan_context``. When
    that isn't available (e.g. some test setups) we fall back to a fresh client.
    """
    state = None
    if ctx is not None:
        try:
            state = ctx.request_context.lifespan_context
        except AttributeError:
            state = None
    http = None
    if isinstance(state, dict):
        http = state.get("http")
    elif state is not None:
        http = getattr(state, "http", None)
    if http is None:
        from ..adapters.http_client import AioHttpHttpClient

        http = AioHttpHttpClient()
    return http  # type: ignore[return-value]


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
    tags={"catalog"},
)
def list_sources(
    country: str | None = Field(
        None, description="Filter by ISO-3166 alpha-2 country code, e.g. 'US'."
    ),
    format: str | None = Field(
        None, description="Filter by source format: 'rest', 'csv', 'json', 'html'."
    ),
) -> list[SourceInfo]:
    """List registered government transparency data sources.

    Returns the catalog of available fetchers, optionally filtered by country
    and/or format. Each entry describes the source and the fields available
    for analysis. Use this first to discover what you can analyze.
    """
    infos = all_source_infos()
    if country:
        try:
            wanted = Country(country.upper())
        except ValueError:
            wanted = None
        infos = (
            [i for i in infos if i.country is not None and i.country == wanted] if wanted else infos
        )
    if format:
        infos = [i for i in infos if i.format.value == format.lower()]
    return infos


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
    tags={"fetch"},
)
async def fetch_data(
    source: str = Field(
        ..., description="Source name from list_sources, e.g. 'usaspending-agencies'."
    ),
    limit: int = Field(100, ge=1, le=10_000, description="Maximum records to return."),
    filters: dict[str, Any] | None = Field(
        None, description="Source-specific filters, e.g. {'record_date': 'gte:2024-01-01'}."
    ),
    ctx: Context | None = None,
) -> list[Record]:
    """Fetch raw transparency records from a registered source.

    Returns normalized ``Record`` objects. Each record's ``fields`` dict
    carries all source-specific columns, while ``entity``, ``value`` and
    ``date`` hold the common normalized fields when available.
    """
    _ensure_known(source)
    params = FetchParams(limit=limit, filters=filters or {})
    http = _http_from_context(ctx)  # type: ignore[arg-type]
    fetcher = build_fetcher(source, http)
    dataset = await fetcher.fetch(params)
    return dataset.records


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
    tags={"analyze"},
)
async def analyze(
    source: str = Field(..., description="Source name to analyze."),
    metric: Literal["top_n", "sum", "average", "count", "trend"] = Field(
        ..., description="Analysis metric to compute."
    ),
    field: str = Field(
        ...,
        description=(
            "Numeric field to analyze. Use a value from the source's `fields` "
            "(e.g. 'outlay_amount', 'tot_pub_debt_out_amt'). Use 'value' for the "
            "normalized primary value."
        ),
    ),
    by: str | None = Field(
        None,
        description=(
            "Optional grouping field (e.g. 'agency_name', 'record_fiscal_year', "
            "'entity'). When omitted, aggregates across all records."
        ),
    ),
    top_n: int = Field(10, ge=1, le=100, description="Number of results for the 'top_n' metric."),
    limit: int = Field(1000, ge=1, le=10_000, description="Max records to fetch before analyzing."),
    filters: dict[str, Any] | None = Field(None, description="Source-specific filters."),
    ctx: Context | None = None,
) -> AnalysisResult:
    """Fetch records from a source and compute an aggregate metric.

    First fetches up to ``limit`` records from ``source`` (same semantics as
    ``fetch_data``), then computes ``metric`` over the chosen ``field``,
    optionally grouped ``by`` another field.

    Metrics:
      - top_n: highest-N groups by summed field (needs ``by``)
      - sum: total of field, optionally grouped by
      - average: mean of field, optionally grouped by
      - count: number of records, optionally grouped by
      - trend: chronological series of field values (uses record dates)
    """
    _ensure_known(source)
    _ = Metric(metric)  # validate early
    params = FetchParams(limit=limit, filters=filters or {})
    http = _http_from_context(ctx)  # type: ignore[arg-type]
    fetcher = build_fetcher(source, http)
    dataset = await fetcher.fetch(params)
    return analysis_service.analyze(dataset, metric, field, by=by, top_n=top_n)


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    tags={"catalog"},
)
def source_schema(name: str = Field(..., description="Source name.")) -> dict[str, Any]:
    """Return the field schema and sample parameters for a single source."""
    _ensure_known(name)
    infos = {i.name: i for i in all_source_infos()}
    info = infos[name]
    return {
        "name": info.name,
        "title": info.title,
        "country": info.country.value,
        "format": info.format.value,
        "kind": info.kind.value,
        "description": info.description,
        "fields": info.fields,
        "sample_params": info.sample_params,
    }


def _ensure_known(source: str) -> None:
    if source not in available_sources():
        raise ValueError(
            f"Unknown source {source!r}. Call `list_sources` first. "
            f"Available: {available_sources()}"
        )


# Silence unused import warnings for symbols re-exported for convenience.
__all__ = [
    "list_sources",
    "fetch_data",
    "analyze",
    "source_schema",
    "available_sources",
    "get_settings",
]
