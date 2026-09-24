"""Domain value objects and entities.

These models are the lingua franca of the framework: every fetcher, regardless of
country/platform/format, must produce ``Record`` objects. The MCP layer and the
analyzer only ever talk in terms of these domain types, never in raw dicts.
"""

from datetime import date as date_type
from typing import Any

from pydantic import BaseModel, Field

from .enums import Country, Format, RecordKind


class SourceInfo(BaseModel):
    """Catalog entry describing a registered transparency source."""

    name: str = Field(..., description="Unique fetcher key, e.g. 'usaspending-agencies'.")
    title: str = Field(..., description="Human-readable title.")
    country: Country = Field(..., description="Country the data belongs to.")
    format: Format = Field(..., description="Physical format of the source.")
    kind: RecordKind = Field(..., description="Semantic kind of records produced.")
    description: str = Field("", description="Short description of the source.")
    fields: list[str] = Field(default_factory=list, description="Available record fields.")
    sample_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Example filter params the source understands.",
    )


class Record(BaseModel):
    """A single normalized transparency record.

    All fetchers map their raw rows into this shape. ``fields`` carries any
    source-specific values that don't map to the common attributes, so no
    information is lost while keeping a stable contract.
    """

    source: str = Field(..., description="Name of the fetcher that produced this record.")
    kind: RecordKind
    country: Country
    entity: str = Field("", description="Primary subject of the record (agency, program, ...).")
    value: float | None = Field(None, description="Primary monetary/numeric value, if any.")
    value_label: str = Field("", description="Human label for `value` (e.g. 'outlay').")
    date: date_type | None = None
    fields: dict[str, Any] = Field(
        default_factory=dict, description="All source-specific fields, keyed by column name."
    )


class FetchParams(BaseModel):
    """Parameters passed to a fetcher invocation."""

    limit: int = Field(100, ge=1, le=10_000, description="Maximum records to return.")
    filters: dict[str, Any] = Field(default_factory=dict, description="Source-specific filters.")
    offset: int = Field(0, ge=0, description="Pagination offset, if supported.")


class AnalysisResult(BaseModel):
    """Output of an analysis operation over a dataset."""

    metric: str
    field: str
    by: str | None = None
    total_records: int
    result: Any
    notes: str = ""


class Dataset(BaseModel):
    """A collection of records from a single source, ready for analysis."""

    source: str
    records: list[Record]

    @property
    def size(self) -> int:
        return len(self.records)
