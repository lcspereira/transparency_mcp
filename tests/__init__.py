"""Test package for transparency-mcp."""

import sys
from pathlib import Path

# Ensure the src/ layout is importable without installation during local runs.
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

FIXTURES_DIR = Path(__file__).parent / "fixtures"
