"""HTML table-scraping fetcher for the OFAC Sanctions Programs list.

Source: https://ofac.treasury.gov/sanctions-programs-and-country-information
No auth required. The page is server-rendered (Drupal 10) with a real
``<table>`` containing one row per active sanctions program and its last
updated date (inside a ``<time datetime="...">`` element).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from ..config import get_settings
from ..domain.enums import Country, Format, RecordKind
from ..domain.models import FetchParams, Record
from ..domain.ports import HttpClientPort
from .base_fetcher import AbstractFetcher
from .registry import register_fetcher


@register_fetcher("ofac-sanctions-programs")
class OfacSanctionsHtmlFetcher(AbstractFetcher):
    title = "OFAC — Active Sanctions Programs (HTML)"
    country = Country.US
    format = Format.HTML
    kind = RecordKind.SANCTIONS
    description = (
        "List of active U.S. sanctions programs and their last-updated dates, "
        "scraped from the OFAC HTML table. Published only as HTML (no CSV/JSON)."
    )
    fields = ["program", "last_updated", "url"]
    sample_params = {"filters": {"program": "Belarus"}}

    _PATH = "/sanctions-programs-and-country-information"

    def __init__(self, http: HttpClientPort) -> None:
        super().__init__(http)
        self._base = get_settings().ofac_base_url.rstrip("/")

    async def fetch_raw(self, params: FetchParams) -> bytes:
        url = f"{self._base}{self._PATH}"
        filters = params.filters or {}
        program = filters.get("program")
        if program:
            url = f"{url}?filter={program}"
        return await self.http.get(url)

    def parse(self, raw: bytes) -> list[dict[str, Any]]:
        soup = BeautifulSoup(raw, "lxml")
        table = soup.select_one("table") or soup.find("table")
        if table is None:
            return []
        rows: list[dict[str, Any]] = []
        for tr in table.select("tbody tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            program_cell = cells[0]
            date_cell = cells[1]
            link = program_cell.find("a")
            program_text = link.get_text(strip=True) if link else program_cell.get_text(strip=True)
            href = link.get("href") if link and link.has_attr("href") else ""
            time_el = date_cell.find("time")
            iso_date = time_el.get("datetime") if time_el and time_el.has_attr("datetime") else ""
            display_date = (
                time_el.get_text(strip=True) if time_el else date_cell.get_text(strip=True)
            )
            if not program_text:
                continue
            rows.append(
                {
                    "program": program_text,
                    "last_updated": iso_date or display_date,
                    "url": href,
                }
            )
        return rows

    def normalize(self, row: dict[str, Any]) -> Record | None:
        program = str(row.get("program") or "").strip()
        if not program:
            return None
        return Record(
            source=self.name,
            kind=self.kind,
            country=self.country,
            entity=program,
            value=None,
            value_label="",
            date=_parse_date(row.get("last_updated")),
            fields={
                "program": program,
                "last_updated": row.get("last_updated"),
                "url": row.get("url"),
            },
        )


def _parse_date(v: Any):
    if not v:
        return None
    from datetime import date as _date

    try:
        return _date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None
