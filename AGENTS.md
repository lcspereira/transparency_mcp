# AGENTS.md

Guidance for AI agents (and humans) working on this repository.

## Environment
- Python 3.13 (pinned in `.python-version`; `uv` manages the venv)
- Package manager: `uv`

## Commands
- Install (editable, with dev deps): `uv sync --extra dev`
- Run the MCP server (stdio): `uv run transparency-mcp`
- Inspect with FastMCP CLI: `uv run fastmcp dev src/transparency_mcp/__main__.py`
- Lint: `uv run ruff check`
- Lint + fix: `uv run ruff check --fix`
- Format check: `uv run ruff format --check`
- Tests: `uv run pytest`
- Tests verbose: `uv run pytest -v`

## Architecture
Clean Architecture (domain -> adapters -> analysis -> mcp delivery). See README.md
"Extending the framework" section for how to add a new fetcher.

Key invariant: the `domain/` layer has **no I/O imports** (no aiohttp, no bs4).
Fetchers implement the `FetcherPort` protocol and register via the
`@register_fetcher` decorator; no MCP tool code needs editing to add a source.