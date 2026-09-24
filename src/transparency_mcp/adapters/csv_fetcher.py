"""CSV fetcher for U.S. Treasury Fiscal Data — Debt to the Penny.

Source:
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?format=csv
No auth required. Same endpoint returns JSON/XML via the ``format=`` param,
which makes it a good demonstration of a CSV-capable adapter.
"""

from __future__ import annotations

import csv
import io
from typing import Any
from urllib.parse import urlencode

from ..config import get_settings
from ..domain.enums import Country, Format, RecordKind
from ..domain.models import FetchParams, Record
from ..domain.ports import HttpClientPort
from .base_fetcher import AbstractFetcher
from .registry import register_fetcher


@register_fetcher("treasury-debt-to-penny")
class TreasuryCsvFetcher(AbstractFetcher):
    title = "U.S. Treasury Fiscal Data — Debt to the Penny (CSV)"
    country = Country.US
    format = Format.CSV
    kind = RecordKind.DEBT
    description = (
        "Daily U.S. public debt outstanding, held by the public and intragovernmental "
        "holdings, served as CSV by the Treasury Fiscal Data API. No auth required."
    )
    fields = [
        "record_date",
        "debt_held_public_amt",
        "intragov_hold_amt",
        "tot_pub_debt_out_amt",
        "record_fiscal_year",
    ]
    sample_params = {"filters": {"record_date": "gte:2024-01-01"}}

    _PATH = "/services/api/fiscal_service/v2/accounting/od/debt_to_penny"

    def __init__(self, http: HttpClientPort) -> None:
        super().__init__(http)
        self._base = get_settings().treasury_base_url.rstrip("/")

    async def fetch_raw(self, params: FetchParams) -> bytes:
        query: dict[str, Any] = {"format": "csv", "page[size]": str(params.limit)}
        # Translate generic filters into the Treasury filter syntax:
        #   {"record_date": "gte:2024-01-01"} -> filter=record_date:gte:2024-01-01
        filters = params.filters or {}
        date_filter = filters.get("record_date") or filters.get("filter")
        if date_filter:
            if not str(date_filter).startswith("record_date"):
                date_filter = (
                    f"record_date:{date_filter}"
                    if ":" in str(date_filter)
                    else f"record_date:gte:{date_filter}"
                )
            query["filter"] = str(date_filter)
        url = f"{self._base}{self._PATH}?{urlencode(query)}"
        return await self.http.get(url)

    def parse(self, raw: bytes) -> list[dict[str, Any]]:
        text = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for r in reader:
            if not r:
                continue
            # Skip rows where every value is empty (trailing blank lines).
            if all((v or "").strip() in ("", "null") for v in r.values()):
                continue
            rows.append({k: ("" if v == "null" else v) for k, v in r.items()})
        return rows

    def normalize(self, row: dict[str, Any]) -> Record | None:
        # A row where the only populated field is record_date and the debt is null
        # is uninformative; the parser already blanked nulls to "".
        total = _to_float(row.get("tot_pub_debt_out_amt"))
        if total is None:
            return None
        return Record(
            source=self.name,
            kind=self.kind,
            country=self.country,
            entity="U.S. Federal Debt",
            value=total,
            value_label="tot_pub_debt_out_amt",
            date=_parse_date(row.get("record_date")),
            fields={
                "record_date": row.get("record_date"),
                "debt_held_public_amt": _to_float(row.get("debt_held_public_amt")),
                "intragov_hold_amt": _to_float(row.get("intragov_hold_amt")),
                "tot_pub_debt_out_amt": total,
                "record_fiscal_year": row.get("record_fiscal_year"),
            },
        )


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _parse_date(v: Any):
    if not v:
        return None
    from datetime import date as _date

    try:
        return _date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None
