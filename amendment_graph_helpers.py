"""Helpers for the Amendment Resolution Graph page.

Kept out of the Streamlit page module so the upload tab cannot be taken down
by query-engine empty-state handling or by lease text that contains `{` / HTML.
"""

from __future__ import annotations

import html
from typing import Iterable, List, Optional


def html_text(value) -> str:
    """Escape lease/amendment text for Streamlit ``unsafe_allow_html`` + f-strings."""
    if value is None:
        return "N/A"
    text = str(value).strip()
    if not text:
        return "N/A"
    return (
        html.escape(text, quote=True)
        .replace("\n", "<br>")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
    )


def clause_types_from_history(rows: Optional[Iterable[dict]]) -> List[str]:
    """Unique sorted clause types from lease_clause_history rows."""
    types = {
        item.get("clause_type")
        for item in (rows or [])
        if item.get("clause_type")
    }
    return sorted(types)
