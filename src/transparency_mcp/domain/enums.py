"""Domain enumerations. Pure Python, no I/O imports."""

from __future__ import annotations

from enum import StrEnum


class Format(StrEnum):
    """Physical representation of a transparency data source."""

    JSON = "json"
    CSV = "csv"
    HTML = "html"
    XML = "xml"
    REST = "rest"  # REST/JSON endpoint (alias used by adapters)


class RecordKind(StrEnum):
    """Semantic kind of transparency record."""

    SPENDING = "spending"
    DEBT = "debt"
    SANCTIONS = "sanctions"
    SALARIES = "salaries"
    CONTRACTS = "contracts"
    BUDGET = "budget"
    GENERIC = "generic"


class Country(StrEnum):
    """ISO 3166-1 alpha-2 country codes (extensible). Use GENERIC for multi-country."""

    US = "US"
    BR = "BR"
    GENERIC = "ZZ"


class Metric(StrEnum):
    """Analysis metrics supported by the analyzer."""

    TOP_N = "top_n"
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    TREND = "trend"
