"""Entry point for the transparency-mcp MCP server (stdio)."""

from __future__ import annotations

from .mcp.server import mcp


def main() -> None:
    """Run the transparency-mcp FastMCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
