"""transparency-mcp package root.

Importing this package wires the layers together. The runnable entry point is
``transparency_mcp.__main__:main`` (see ``pyproject.toml``).
"""

from __future__ import annotations

from .adapters import available_sources  # noqa: F401 (registers fetchers)

__version__ = "0.1.0"

__all__ = ["available_sources", "__version__"]
