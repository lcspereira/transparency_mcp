"""Abstract fetcher base class (Template Method pattern).

Concrete fetchers override the small, format-specific hooks (``fetch_raw`` and
``parse``) and get the full ``fetch -> parse -> normalize -> Dataset`` pipeline
wired for free. This keeps new adapters tiny and consistent.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from ..config import get_settings
from ..domain.enums import Country, Format, RecordKind
from ..domain.models import Dataset, FetchParams, Record, SourceInfo
from ..domain.ports import HttpClientPort


class AbstractFetcher(ABC):
    """Base class for all transparency fetchers.

    Subclasses MUST set the class attributes ``name``, ``title``, ``country``,
    ``format``, ``kind`` and override ``fetch_raw`` + ``parse``. They SHOULD
    override ``normalize`` if the default dict->Record mapping isn't enough.
    """

    name: str = ""
    title: str = ""
    country: Country = Country.GENERIC
    format: Format = Format.JSON
    kind: RecordKind = RecordKind.GENERIC
    description: str = ""
    fields: list[str] = []
    sample_params: dict[str, Any] = {}

    def __init__(self, http: HttpClientPort) -> None:
        if not self.name:
            raise TypeError(f"{type(self).__name__} must define a non-empty 'name' attribute")
        self.http = http

    # -- public API --------------------------------------------------------

    def info(self) -> SourceInfo:
        return SourceInfo(
            name=self.name,
            title=self.title or self.name,
            country=self.country,
            format=self.format,
            kind=self.kind,
            description=self.description,
            fields=list(self.fields),
            sample_params=dict(self.sample_params),
        )

    async def fetch(self, params: FetchParams) -> Dataset:
        """Template Method: fetch raw bytes -> parse rows -> normalize -> Dataset."""
        raw = await self.fetch_raw(params)
        rows = self.parse(raw)
        records = [self.normalize(row) for row in rows[: params.limit]]
        records = [r for r in records if r is not None]
        return Dataset(source=self.name, records=records)

    # -- hooks for subclasses ---------------------------------------------

    async def fetch_raw(self, params: FetchParams) -> bytes:
        """Fetch the raw payload (bytes) from the source. Must be overridden."""
        raise NotImplementedError

    def parse(self, raw: bytes) -> list[dict[str, Any]]:
        """Parse raw bytes into a list of row dicts. Must be overridden."""
        raise NotImplementedError

    def normalize(self, row: dict[str, Any]) -> Record | None:
        """Map a raw row dict to a domain ``Record``.

        Default implementation builds a ``Record`` from common fields and dumps
        the full row into ``Record.fields`` so no data is lost. Override to
        refine the mapping for a given source.
        """
        settings_limit_hit = len(row) == 0
        if settings_limit_hit:
            return None
        return Record(
            source=self.name,
            kind=self.kind,
            country=self.country,
            entity=str(row.get("entity") or row.get("name") or row.get("agency_name") or ""),
            value=_coerce_float(
                row.get("value")
                or row.get("amount")
                or row.get("outlay_amount")
                or row.get("tot_pub_debt_out_amt")
            ),
            value_label=_guess_value_label(row),
            date=_coerce_date(row.get("date") or row.get("record_date")),
            fields=dict(row),
        )


# -- helpers ------------------------------------------------------------------


def _coerce_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN guard


def _guess_value_label(row: dict[str, Any]) -> str:
    for key in ("outlay_amount", "tot_pub_debt_out_amt", "amount", "value"):
        if key in row and row[key] not in (None, ""):
            return key
    return ""


def _coerce_date(v: Any):
    if v is None or v == "":
        return None
    from datetime import date as _date

    try:
        return _date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def default_limit() -> int:
    return get_settings().default_limit
