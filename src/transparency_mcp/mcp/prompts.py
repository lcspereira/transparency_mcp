"""MCP prompts: pre-baked analysis workflows for agents."""

from __future__ import annotations

from .server import mcp


@mcp.prompt
def analyze_spending(country: str = "US", focus: str = "agencies") -> str:
    """Generate a prompt that guides an agent through a spending analysis.

    Args:
        country: ISO-3166 alpha-2 country code to focus on (default 'US').
        focus: Aspect to focus on (e.g. 'agencies', 'debt', 'sanctions').
    """
    return (
        f"You are a government transparency analyst focused on {country}.\n\n"
        f"Steps:\n"
        f"1. Call `list_sources` with country={country!r} to see available sources.\n"
        f"2. Pick the source most relevant to '{focus}'.\n"
        f"3. Call `source_schema` with that source's name to learn its fields.\n"
        f"4. Call `fetch_data` with a small limit to inspect a sample.\n"
        f"5. Call `analyze` with metric='top_n', an appropriate numeric `field`, "
        f"and `by` set to a meaningful grouping (e.g. 'agency_name').\n"
        f"6. Summarize the top spenders/debtors/programs in plain language, with "
        f"figures rounded for readability, and note the source and date coverage.\n"
    )


@mcp.prompt
def compare_agencies(metric: str = "outlay_amount") -> str:
    """Generate a prompt for comparing U.S. federal agencies on a metric."""
    return (
        f"Compare U.S. federal agencies by {metric}.\n\n"
        f"1. Call `list_sources` and find the USAspending source.\n"
        f"2. Call `analyze` with source='usaspending-agencies', metric='top_n', "
        f"field={metric!r}, by='agency_name', top_n=10.\n"
        f"3. Present the top-10 agencies as a ranked table with rounded dollar values.\n"
        f"4. Add a one-paragraph narrative on the concentration of spending.\n"
    )
