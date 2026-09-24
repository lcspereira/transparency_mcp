"""REST/JSON fetcher for USAspending.gov toptier agencies.

Source: https://api.usaspending.gov/api/v2/references/toptier_agencies/
No auth required. Returns federal agencies with outlay/obligation/budget
amounts for the active fiscal year.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

from ..config import get_settings
from ..domain.enums import Country, Format, RecordKind
from ..domain.models import FetchParams, Record
from ..domain.ports import HttpClientPort
from .base_fetcher import AbstractFetcher
from .registry import register_fetcher


@register_fetcher("usaspending-agencies")
class USAspendingFetcher(AbstractFetcher):
    title = "USAspending — Toptier Federal Agencies"
    country = Country.US
    format = Format.REST
    kind = RecordKind.SPENDING
    description = (
        "U.S. federal toptier agencies with outlay, obligation and budget "
        "authority amounts for the active fiscal year. No auth required."
    )
    fields = [
        "agency_id",
        "abbreviation",
        "agency_name",
        "active_fy",
        "active_fq",
        "outlay_amount",
        "obligated_amount",
        "budget_authority_amount",
        "percentage_of_total_budget_authority",
        "agency_slug",
    ]
    sample_params = {"limit": 100}

    _PATH = "/api/v2/references/toptier_agencies/"

    def __init__(self, http: HttpClientPort) -> None:
        super().__init__(http)
        self._base = get_settings().usaspending_base_url.rstrip("/") + "/"

    async def fetch_raw(self, params: FetchParams) -> bytes:
        url = urljoin(self._base, self._PATH.lstrip("/"))
        return await self.http.get(url)

    def parse(self, raw: bytes) -> list[dict[str, Any]]:
        payload = json.loads(raw)
        rows = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError(f"Unexpected USAspending payload shape: {type(rows)!r}")
        return [self._normalize_row(r) for r in rows if isinstance(r, dict)]

    def normalize(self, row: dict[str, Any]) -> Record | None:
        return Record(
            source=self.name,
            kind=self.kind,
            country=self.country,
            entity=str(row.get("agency_name") or row.get("abbreviation") or ""),
            value=_to_float(row.get("outlay_amount")),
            value_label="outlay_amount",
            date=None,
            fields={
                "agency_id": row.get("agency_id"),
                "abbreviation": row.get("abbreviation"),
                "agency_name": row.get("agency_name"),
                "active_fy": row.get("active_fy"),
                "active_fq": row.get("active_fq"),
                "outlay_amount": _to_float(row.get("outlay_amount")),
                "obligated_amount": _to_float(row.get("obligated_amount")),
                "budget_authority_amount": _to_float(row.get("budget_authority_amount")),
                "percentage_of_total_budget_authority": _to_float(
                    row.get("percentage_of_total_budget_authority")
                ),
                "agency_slug": row.get("agency_slug"),
            },
        )

    @staticmethod
    def _normalize_row(r: dict[str, Any]) -> dict[str, Any]:
        # Pass-through; normalization happens in normalize() to keep parse() format-only.
        return r


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN guard
