"""Application settings.

Configuration is sourced from environment variables prefixed with
``TRANSPARENCY_MCP_`` (pydantic-settings handles the mapping). The Settings
instance is the single source of truth and is injected into fetchers and the
HTTP client via dependency injection.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the transparency MCP server."""

    model_config = SettingsConfigDict(
        env_prefix="TRANSPARENCY_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    http_timeout: float = Field(30.0, description="Default HTTP request timeout in seconds.")
    http_user_agent: str = Field(
        "transparency-mcp/0.1 (+https://example.org)",
        description="User-Agent header sent on all outbound requests.",
    )
    default_limit: int = Field(
        100, ge=1, le=10_000, description="Default record limit when none is requested."
    )
    log_level: str = Field("INFO", description="Python log level for the server.")

    # Source base URLs (overridable for tests / self-hosted mirrors)
    usaspending_base_url: str = "https://api.usaspending.gov"
    treasury_base_url: str = "https://api.fiscaldata.treasury.gov"
    ofac_base_url: str = "https://ofac.treasury.gov"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
