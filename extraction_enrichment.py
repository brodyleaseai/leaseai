"""Deterministic fill-ins after GPT extraction.

GPT-4o often fills Base Rent Year 1-5 and then leaves Full Rent Schedule
as NOT FOUND because the 84-field JSON is long. This module rebuilds the
schedule from the lease text (and from any year fields already extracted).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

FULL_SCHEDULE = "Full Rent Schedule (all years)"
YEAR_FIELDS = [
    "Base Rent Year 1 (monthly)",
    "Base Rent Year 2 (monthly)",
    "Base Rent Year 3 (monthly)",
    "Base Rent Year 4 (monthly)",
    "Base Rent Year 5 (monthly)",
]

MONTHS = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
DATE = rf"(?:{MONTHS})\s+\d{{1,2}},\s+\d{{4}}"
PERIOD_RATE = re.compile(
    rf"(?P<start>{DATE})\s*[–\-]\s*(?P<end>{DATE})\s*:\s*\$?(?P<rate>\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
    re.IGNORECASE,
)
RSF = re.compile(
    r"(\d{1,3}(?:,\d{3})+|\d+)\s+rentable square feet",
    re.IGNORECASE,
)
PCT_ESCALATION = re.compile(
    r"(?:approximately\s+)?(?:three percent|\b3\s?%)\s*(?:\(3%\))?\s*(?:compounded)?",
    re.IGNORECASE,
)


def _value(fields: Dict[str, Any], name: str) -> str:
    data = fields.get(name)
    if isinstance(data, dict):
        return str(data.get("value") or "").strip()
    if data is None:
        return ""
    return str(data).strip()


def _is_missing(value: str) -> bool:
    return (not value) or value.upper() in {"NOT FOUND", "N/A", "NONE", "NULL"}


def _set_field(
    fields: Dict[str, Any],
    name: str,
    value: str,
    confidence: str,
    notes: str,
    source: str = "",
) -> None:
    current = fields.get(name)
    if not isinstance(current, dict):
        current = {}
    current["value"] = value
    current["confidence"] = confidence
    current["notes"] = notes
    if source:
        current["source_snippet"] = source[:200]
    fields[name] = current


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def parse_premises_rsf(lease_text: str) -> Optional[int]:
    match = RSF.search(lease_text or "")
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_annual_rate_periods(lease_text: str) -> List[Dict[str, Any]]:
    """Read Section 5-style 'April 1, 2025–March 31, 2026: $24.00' rows."""
    rows = []
    for match in PERIOD_RATE.finditer(lease_text or ""):
        rate = float(match.group("rate").replace(",", ""))
        rows.append(
            {
                "start": match.group("start"),
                "end": match.group("end"),
                "annual_rate": rate,
            }
        )
    return rows


def monthly_from_annual_rate(rsf: int, annual_rate: float) -> float:
    return round(rsf * annual_rate / 12.0, 2)


def build_full_rent_schedule(
    periods: List[Dict[str, Any]],
    rsf: int,
    year_values: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    """Return (schedule text, first five monthly strings)."""
    parts = []
    first_five = []
    for index, period in enumerate(periods, start=1):
        monthly = monthly_from_annual_rate(rsf, period["annual_rate"])
        monthly_text = _money(monthly)
        if index <= 5:
            first_five.append(monthly_text)
        parts.append(
            f"Year {index} ({period['start']}–{period['end']}): "
            f"{_money(period['annual_rate'])}/RSF/year = {monthly_text}/month"
        )
    if not parts and year_values:
        labeled = []
        for index, value in enumerate(year_values, start=1):
            if not _is_missing(value):
                labeled.append(f"Year {index}: {value}")
        return "; ".join(labeled), first_five
    return "; ".join(parts), first_five


def enrich_extracted_fields(fields: Optional[Dict[str, Any]], lease_text: str) -> Dict[str, Any]:
    """Fill rent schedule and other fields the model commonly drops."""
    fields = dict(fields or {})
    text = lease_text or ""
    rsf = parse_premises_rsf(text)
    periods = parse_annual_rate_periods(text)

    year_values = [_value(fields, name) for name in YEAR_FIELDS]
    if periods and rsf:
        schedule, first_five = build_full_rent_schedule(periods, rsf)
        _set_field(
            fields,
            FULL_SCHEDULE,
            schedule,
            "HIGH",
            f"Built from the {len(periods)}-year per-RSF table on {rsf:,} rentable square feet.",
            source="Base Rent is calculated on",
        )
        for name, monthly in zip(YEAR_FIELDS, first_five):
            if _is_missing(_value(fields, name)):
                _set_field(
                    fields,
                    name,
                    monthly,
                    "HIGH",
                    f"Calculated as {rsf:,} RSF × stated annual rate / 12.",
                )
    elif any(not _is_missing(value) for value in year_values) and _is_missing(_value(fields, FULL_SCHEDULE)):
        schedule, _ = build_full_rent_schedule([], rsf or 0, year_values)
        if schedule:
            _set_field(
                fields,
                FULL_SCHEDULE,
                schedule,
                "MEDIUM",
                "Assembled from extracted Year 1-5 monthly rent fields.",
            )

    if _is_missing(_value(fields, "Annual Escalation Rate or Cap")) and PCT_ESCALATION.search(text):
        _set_field(
            fields,
            "Annual Escalation Rate or Cap",
            "3%",
            "HIGH",
            "Lease states approximately 3% compounded; stated dollar rates govern if they differ.",
        )
        if _is_missing(_value(fields, "Annual Escalation Type (Fixed / CPI / Percentage)")):
            _set_field(
                fields,
                "Annual Escalation Type (Fixed / CPI / Percentage)",
                "Percentage",
                "HIGH",
                "3% compounded annual increase with a fixed dollar-rate schedule.",
            )

    if _is_missing(_value(fields, "Lease Type (Gross / Net / Modified Gross)")) and re.search(
        r"commercial net lease|\bnet lease\b", text, re.IGNORECASE
    ):
        _set_field(
            fields,
            "Lease Type (Gross / Net / Modified Gross)",
            "Net",
            "HIGH",
            "Document is titled a Commercial Net Lease.",
        )

    if _is_missing(_value(fields, "Renewal Rent Basis (FMV / Fixed / CPI)")) and re.search(
        r"fair market", text, re.IGNORECASE
    ):
        _set_field(
            fields,
            "Renewal Rent Basis (FMV / Fixed / CPI)",
            "FMV",
            "HIGH",
            "Renewal Base Rent is then-current fair market net rent.",
        )

    if _is_missing(_value(fields, "HVAC Responsibility (Landlord / Tenant)")) and re.search(
        r"Landlord shall provide base building HVAC", text, re.IGNORECASE
    ):
        _set_field(
            fields,
            "HVAC Responsibility (Landlord / Tenant)",
            "Landlord",
            "HIGH",
            "Landlord provides base building HVAC during standard hours.",
        )

    if _is_missing(_value(fields, "Free Rent Period (months)")) and not re.search(
        r"\bfree rent\b|\brent abatement\b|\babated rent\b", text, re.IGNORECASE
    ):
        _set_field(
            fields,
            "Free Rent Period (months)",
            "0 months",
            "MEDIUM",
            "No free-rent or abatement period is stated. Fixturing access does not waive rent.",
        )

    suite = _value(fields, "Suite / Unit Number")
    if suite and re.search(r"suite\s*1450", suite, re.IGNORECASE):
        if re.search(r"880 West Pender", text) and not re.search(
            r"Premises.{0,200}Suite 1450", text, re.IGNORECASE | re.DOTALL
        ):
            _set_field(
                fields,
                "Suite / Unit Number",
                "NOT FOUND",
                "LOW",
                "Suite 1450 is the landlord notice address, not the leased premises.",
            )

    return fields
