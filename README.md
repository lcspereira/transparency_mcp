# transparency-mcp

An [MCP](https://modelcontextprotocol.io/) server to **analyze governments' transparency data**, built with [Python 3.13](https://www.python.org/), [FastMCP](https://gofastmcp.com/), and [aiohttp](https://docs.aiohttp.org/).

It ships with an **extensible fetcher framework** so developers can adapt it to fetch transparency data from any country, any platform, and any format (REST/JSON, CSV, HTML scraping, …) — without touching the MCP tool code.

## Features

- **3 working example adapters** (no API key required):
  - `usaspending-agencies` — USAspending REST/JSON (U.S. federal agency outlays)
  - `treasury-debt-to-penny` — U.S. Treasury Fiscal Data CSV (daily public debt)
  - `ofac-sanctions-programs` — OFAC HTML table scraping (active sanctions programs)
- **MCP tools**: `list_sources`, `fetch_data`, `analyze`, `source_schema`
- **MCP resources** and **prompts** for guided analysis workflows
- **Clean Architecture** (domain → adapters → analysis → MCP delivery)
- **SOLID + design patterns**: Strategy (fetcher port), Template Method (base fetcher), Registry (`@register_fetcher`), Dependency Injection (HTTP client + config), Adapter (raw→Record normalization)
- **Unit tests** for the framework, fetchers (HTTP mocked), and in-process MCP server

## Quick start

```bash
# 1. Install (editable, with dev dependencies)
uv sync --extra dev

# 2. Run the MCP server over stdio
uv run transparency-mcp

# 3. Inspect interactively (optional)
uv run fastmcp dev src/transparency_mcp/__main__.py
```

Then point any MCP client (Claude Desktop, `fastmcp` CLI, the MCP inspector, …) at this server.

## Environment variables

All settings are optional and prefixed with `TRANSPARENCY_MCP_`:

| Variable | Default | Description |
|---|---|---|
| `TRANSPARENCY_MCP_HTTP_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `TRANSPARENCY_MCP_HTTP_USER_AGENT` | `transparency-mcp/0.1 …` | Outbound User-Agent |
| `TRANSPARENCY_MCP_DEFAULT_LIMIT` | `100` | Default record limit |
| `TRANSPARENCY_MCP_USASPENDING_BASE_URL` | `https://api.usaspending.gov` | Override base URL |
| `TRANSPARENCY_MCP_TREASURY_BASE_URL` | `https://api.fiscaldata.treasury.gov` | Override base URL |
| `TRANSPARENCY_MCP_OFAC_BASE_URL` | `https://ofac.treasury.gov` | Override base URL |

## MCP surface

### Tools
- **`list_sources(country?, format?)`** → catalog of registered sources
- **`fetch_data(source, limit?, filters?)`** → normalized records
- **`analyze(source, metric, field, by?, top_n?, limit?, filters?)`** → aggregate metrics (`top_n`, `sum`, `average`, `count`, `trend`)
- **`source_schema(name)`** → field schema + sample params

### Prompts
- **`analyze_spending(country?, focus?)`** — guided spending-analysis workflow
- **`compare_agencies(metric?)`** — compare U.S. federal agencies

## Architecture

```
src/transparency_mcp/
├── domain/          Pure models, enums, ports (NO I/O imports)
│   ├── enums.py       Format, RecordKind, Country, Metric
│   ├── models.py      Record, Dataset, SourceInfo, FetchParams, AnalysisResult
│   └── ports.py       FetcherPort, HttpClientPort (Protocols)
├── adapters/        I/O-bound fetchers + HTTP client
│   ├── http_client.py        AioHttpHttpClient (HttpClientPort impl)
│   ├── base_fetcher.py       AbstractFetcher (Template Method)
│   ├── registry.py           @register_fetcher (Registry pattern)
│   ├── rest_json_fetcher.py  USAspending (REST/JSON)
│   ├── csv_fetcher.py        Treasury FiscalData (CSV)
│   └── html_table_fetcher.py OFAC (HTML scraping via BeautifulSoup)
├── analysis/        Pure use cases
│   └── analyzer.py   AnalysisService (top_n/sum/average/count/trend)
├── mcp/             FastMCP delivery layer
│   ├── server.py     FastMCP instance + lifespan (HTTP session lifecycle)
│   ├── tools.py       @mcp.tool functions (thin façades)
│   └── prompts.py     @mcp.prompt templates
├── config.py        Settings (env-driven, pydantic-settings)
└── __main__.py      Entry point: mcp.run()
```

**Invariants**
- `domain/` has **no I/O imports** (no `aiohttp`, no `bs4`). It only depends on Pydantic + the standard library.
- `analysis/` operates purely on in-memory `Dataset`/`Record` objects.
- `mcp/` is a thin delivery layer: it resolves the HTTP client from the lifespan, looks up fetchers by name in the registry, and delegates to fetchers + the analysis service.
- Adding a new source never touches `mcp/` or `analysis/`.

## Extending the framework

To add a new transparency source, create a fetcher and register it. That's it — the MCP tools (`list_sources`, `fetch_data`, `analyze`) will pick it up automatically.

### Minimal example (JSON)

```python
# src/transparency_mcp/adapters/my_country_fetcher.py
from __future__ import annotations
import json
from typing import Any
from urllib.parse import urljoin

from .base_fetcher import AbstractFetcher
from .registry import register_fetcher
from ..config import get_settings
from ..domain.enums import Country, Format, RecordKind
from ..domain.models import FetchParams, Record


@register_fetcher("br-portal-salaries")
class BrazilPortalFetcher(AbstractFetcher):
    title = "Brazil Portal da Transparência — Salaries"
    country = Country.BR
    format = Format.REST
    kind = RecordKind.SALARIES
    description = "Public servant salaries from Brazil's transparency portal."
    fields = ["nome", "cargo", "remuneracao"]
    sample_params = {"filters": {"orgao": "minsaude"}}

    _PATH = "/api-de-dados/servidores"

    def __init__(self, http) -> None:
        super().__init__(http)
        self._base = "https://api.portaldatransparencia.gov.br"

    async def fetch_raw(self, params: FetchParams) -> bytes:
        url = urljoin(self._base + "/", self._PATH.lstrip("/"))
        return await self.http.get(url, params={"pagina": params.offset // 100 + 1})

    def parse(self, raw: bytes) -> list[dict[str, Any]]:
        return json.loads(raw)

    def normalize(self, row: dict[str, Any]) -> Record | None:
        return Record(
            source=self.name,
            kind=self.kind,
            country=self.country,
            entity=str(row.get("nome") or ""),
            value=float(row.get("remuneracao") or 0) or None,
            value_label="remuneracao",
            fields={
                "nome": row.get("nome"),
                "cargo": row.get("cargo"),
                "remuneracao": row.get("remuneracao"),
            },
        )
```

### Make it discoverable

Add an import in `src/transparency_mcp/adapters/__init__.py` so the decorator runs at import time:

```python
from . import my_country_fetcher  # noqa: F401
```

That's the entire change. `list_sources` will now return your source, and agents can `fetch_data("br-portal-salaries", …)` and `analyze("br-portal-salaries", "top_n", "remuneracao", by="cargo")` immediately.

### Other formats

The only format-specific hooks are `fetch_raw` (return `bytes`) and `parse` (return `list[dict]`). For CSV, use the stdlib `csv` module; for HTML, use BeautifulSoup (see `html_table_fetcher.py`); for XML, use `lxml.etree`. The `normalize` method maps your row dicts to domain `Record`s — override it whenever the default field-name heuristics aren't enough.

## Design patterns used

| Pattern | Where | SOLID |
|---|---|---|
| Strategy / Interface | `FetcherPort` Protocol | OCP, DIP |
| Template Method | `AbstractFetcher.fetch` pipeline | DRY, SRP |
| Registry | `@register_fetcher` + `build_fetcher` | OCP (add without editing core) |
| Adapter | raw row dict → `Record` (normalize) | ISP |
| Dependency Injection | lifespan-stored HTTP client, `Settings` | DIP |
| Facade | MCP tools delegate to `AnalysisService` | SRP |

## Testing

```bash
uv run pytest -v          # full suite
uv run pytest tests/test_analyzer.py -v   # one file
uv run ruff check         # lint
uv run ruff format --check
```

Tests use a fake ``HttpClientPort`` (no real network, no aiohttp mocking) and
exercise the MCP tools in-process via FastMCP's ``Client`` with a fake
fetcher.

## License

MIT