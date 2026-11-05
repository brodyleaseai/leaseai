"""Helpers for the Amendment Resolution Graph page.

Kept out of the Streamlit page module so the upload tab cannot be taken down
by query-engine empty-state handling or by lease text that contains `{` / HTML.
"""

from __future__ import annotations

import html
from typing import Any, Dict, Iterable, List, Optional


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


def nested_client(lease: Optional[dict]) -> Dict[str, Any]:
    clients = (lease or {}).get("clients")
    if isinstance(clients, list) and clients:
        clients = clients[0]
    return clients if isinstance(clients, dict) else {}


def lease_client_name(lease: Optional[dict]) -> str:
    """Client / customer name for Prepared-for fields. Prefer the clients row."""
    lease = lease or {}
    client = nested_client(lease)
    for value in (
        client.get("name"),
        client.get("company_name"),
        lease.get("client_name"),
        lease.get("tenant_name"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return ""


def lease_option_label(lease: dict, amendment_count: Optional[int] = None) -> str:
    """Stable unique selectbox label so two leases cannot collapse into one option."""
    address = str(lease.get("property_address") or "Unknown property").strip()
    tenant = str(lease.get("tenant_name") or lease_client_name(lease) or "Unknown tenant").strip()
    lease_id = str(lease.get("id") or "")
    parts = [f"{address} — {tenant}"]
    if amendment_count:
        parts.append(f"{amendment_count} amendment{'s' if amendment_count != 1 else ''}")
    if lease_id:
        parts.append(lease_id[:8])
    return " · ".join(parts)
