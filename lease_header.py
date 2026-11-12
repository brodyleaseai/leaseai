"""Resolve the abstract header from extracted fields, not bulk placeholders."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

PLACEHOLDER_TENANTS = {
    "",
    "to be reviewed",
    "tenant not provided",
    "n/a",
    "na",
    "none",
    "unknown",
    "unknown tenant",
}
PLACEHOLDER_ADDRESSES = {
    "",
    "address not provided",
    "n/a",
    "na",
    "none",
    "unknown",
}
EMPTY_VALUES = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "—", "-"}


def _clean(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return "" if text.upper() in EMPTY_VALUES else text


def field_value(extracted_fields: Optional[Dict], *names: str) -> str:
    rows = extracted_fields or {}
    for name in names:
        data = rows.get(name)
        if isinstance(data, dict):
            text = _clean(
                data.get("value")
                or data.get("reviewed_value")
                or data.get("raw_value")
            )
        else:
            text = _clean(data)
        if text:
            return text
    return ""


def is_placeholder_tenant(value: Any) -> bool:
    return str(value or "").strip().lower() in PLACEHOLDER_TENANTS


def is_placeholder_address(value: Any) -> bool:
    text = str(value or "").strip()
    if text.lower() in PLACEHOLDER_ADDRESSES:
        return True
    # Bulk upload used the PDF filename, e.g. "01 Commercial Office Lease Alder Peak"
    if text.lower().endswith(".pdf"):
        return True
    if "," not in text and re.search(r"(\blease\b|\.pdf$)", text, re.I):
        return True
    return False


def extracted_tenant_name(extracted_fields: Optional[Dict] = None) -> str:
    return field_value(
        extracted_fields,
        "Tenant Legal Name",
        "Tenant Trade Name (if different)",
    )


def extracted_property_address(extracted_fields: Optional[Dict] = None) -> str:
    return field_value(extracted_fields, "Property Civic Address")


def display_tenant_name(lease_data: Optional[Dict] = None, extracted_fields: Optional[Dict] = None) -> str:
    lease = lease_data or {}
    current = _clean(lease.get("tenant_name"))
    extracted = extracted_tenant_name(extracted_fields)
    if extracted and (not current or is_placeholder_tenant(current)):
        return extracted
    return current or extracted or "N/A"


def display_property_address(lease_data: Optional[Dict] = None, extracted_fields: Optional[Dict] = None) -> str:
    lease = lease_data or {}
    current = _clean(lease.get("property_address"))
    extracted = extracted_property_address(extracted_fields)
    if extracted and (not current or is_placeholder_address(current)):
        return extracted
    return current or extracted or "N/A"


def lease_header_updates(extracted_fields: Optional[Dict] = None) -> Dict[str, str]:
    """Columns to write back onto the leases row after GPT extraction."""
    updates = {}
    tenant = extracted_tenant_name(extracted_fields)
    address = extracted_property_address(extracted_fields)
    if tenant:
        updates["tenant_name"] = tenant
    if address:
        updates["property_address"] = address
    return updates


def apply_extracted_header(lease_data: Optional[Dict], extracted_fields: Optional[Dict] = None) -> Dict[str, Any]:
    row = dict(lease_data or {})
    row["tenant_name"] = display_tenant_name(row, extracted_fields)
    row["property_address"] = display_property_address(row, extracted_fields)
    return row
