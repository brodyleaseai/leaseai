"""Resolve calendar critical dates from extracted lease fields."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

NOT_FOUND = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "—", "-"}

FIELD_ALIASES = {
    "commencement": (
        "Lease Commencement Date",
        "Target Commencement Date",
        "Lease Start Date",
    ),
    "rent_commencement": ("Rent Commencement Date",),
    "expiration": (
        "Lease Expiration Date",
        "Lease End Date",
        "Expiration Date",
    ),
    "term_months": (
        "Lease Term (Total Months)",
        "Lease Term (total months)",
        "Lease Term",
    ),
    "renewal_notice": ("Renewal Notice Deadline",),
    "renewal_count": ("Number of Renewal Options",),
    "termination": (
        "Early Termination Right",
        "Termination Notice Period",
        "Termination Notice Deadline",
    ),
    "expansion": ("Expansion Option",),
}


def _usable(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return "" if text.upper() in NOT_FOUND else text


def fields_from_any(extracted_fields: Any) -> Dict[str, Any]:
    if not extracted_fields:
        return {}
    if isinstance(extracted_fields, dict):
        return extracted_fields
    mapped = {}
    for row in extracted_fields:
        name = row.get("field_name") if isinstance(row, dict) else None
        if name:
            mapped[name] = row
    return mapped


def field_value(fields: Dict[str, Any], names: Iterable[str]) -> str:
    for name in names:
        raw = fields.get(name)
        if raw is None:
            continue
        if isinstance(raw, dict):
            for key in ("reviewed_value", "raw_value", "value"):
                text = _usable(raw.get(key))
                if text:
                    return text
        else:
            text = _usable(raw)
            if text:
                return text
    return ""


def is_duration_formula(value: str) -> bool:
    lower = (value or "").lower()
    if "conditional" in lower:
        return True
    return bool(re.search(r"\d+\s+months?\s+(from|after|following|prior|before)", lower))


def parse_calendar_date(value: str) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    leading = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    if leading:
        try:
            return datetime.strptime(leading.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    named = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        text,
        re.I,
    )
    if named:
        try:
            return datetime.strptime(named.group(0).replace(",", ""), "%B %d %Y").date()
        except ValueError:
            return None
    if is_duration_formula(text):
        return None
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y"):
        try:
            return datetime.strptime(text[:32], fmt).date()
        except ValueError:
            continue
    return None


def parse_months(value: str) -> int:
    if not value:
        return 0
    lower = value.lower()
    year_match = re.search(r"(\d+(?:\.\d+)?)\s*year", lower)
    month_match = re.search(r"(\d+)\s*month", lower)
    if year_match and "month" not in lower:
        return int(round(float(year_match.group(1)) * 12))
    if month_match:
        return int(month_match.group(1))
    return 0


def add_months(start: date, months: int) -> date:
    try:
        from dateutil.relativedelta import relativedelta
        return start + relativedelta(months=months)
    except Exception:
        return start + timedelta(days=int(months * 30.44))


def _notice_months_prior(text: str) -> Optional[int]:
    """Use the latest allowed notice (smallest 'at least N months prior')."""
    if not text:
        return None
    lower = text.lower()
    at_least = re.search(r"(?:at least|not less than|minimum of)\s+(\d+)\s+months?", lower)
    if at_least:
        return int(at_least.group(1))
    prior = re.search(r"(\d+)\s+months?\s+(?:prior|before|preceding)", lower)
    if prior:
        return int(prior.group(1))
    if parse_calendar_date(text):
        return None
    months = parse_months(text)
    return months or None


def _row(date_type: str, value: date, description: str, source_field: str) -> Dict[str, str]:
    return {
        "date_type": date_type,
        "date_value": value.isoformat(),
        "description": description,
        "source_field": source_field,
    }


def critical_dates_from_fields(extracted_fields: Any) -> List[Dict[str, str]]:
    """Return calendar critical dates derived from one lease abstract."""
    fields = fields_from_any(extracted_fields)
    commence_text = field_value(fields, FIELD_ALIASES["commencement"])
    rent_text = field_value(fields, FIELD_ALIASES["rent_commencement"])
    end_text = field_value(fields, FIELD_ALIASES["expiration"])
    term_text = field_value(fields, FIELD_ALIASES["term_months"])
    notice_text = field_value(fields, FIELD_ALIASES["renewal_notice"])
    expansion_text = field_value(fields, FIELD_ALIASES["expansion"])

    commence = parse_calendar_date(commence_text)
    term_months = parse_months(term_text) or (parse_months(end_text) if is_duration_formula(end_text) else 0)
    expiration = parse_calendar_date(end_text)
    if commence and term_months and (not expiration or is_duration_formula(end_text)):
        expiration = add_months(commence, term_months)

    rent_start = parse_calendar_date(rent_text)
    if commence and not rent_start and is_duration_formula(rent_text):
        gap = parse_months(rent_text)
        if gap:
            rent_start = add_months(commence, gap)

    rows: List[Dict[str, str]] = []
    if commence:
        note = commence_text if "target" in commence_text.lower() or "conditional" in commence_text.lower() else "Lease commencement"
        rows.append(_row("Lease Commencement", commence, note, "Lease Commencement Date"))
    if rent_start:
        rows.append(_row("Rent Commencement", rent_start, rent_text or "Rent commencement", "Rent Commencement Date"))
    if expiration:
        desc = end_text if is_duration_formula(end_text) or term_months else "Lease expiration"
        if term_months and is_duration_formula(end_text):
            desc = f"{term_months} months from commencement"
        rows.append(_row("Lease Expiration", expiration, desc, "Lease Expiration Date"))

    notice_months = _notice_months_prior(notice_text)
    if expiration and notice_months:
        notice_date = add_months(expiration, -notice_months)
        rows.append(_row(
            "Renewal Notice Deadline",
            notice_date,
            notice_text or f"{notice_months} months prior to expiration",
            "Renewal Notice Deadline",
        ))
    else:
        notice_date = parse_calendar_date(notice_text)
        if notice_date:
            rows.append(_row("Renewal Notice Deadline", notice_date, notice_text, "Renewal Notice Deadline"))

    expansion_date = parse_calendar_date(expansion_text)
    if expansion_date:
        rows.append(_row("Expansion Option Deadline", expansion_date, expansion_text, "Expansion Option"))

    unique = []
    seen = set()
    for row in rows:
        key = (row["date_type"], row["date_value"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    unique.sort(key=lambda item: item["date_value"])
    return unique


def records_for_database(lease_id: str, dates: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
    records = []
    for item in dates:
        records.append({
            "lease_id": lease_id,
            "date_type": item["date_type"],
            "date_value": item["date_value"],
            "description": item.get("description") or f"Extracted from {item.get('source_field', 'lease')}",
            "notification_intervals": [90, 60, 30, 14, 7, 1],
            "notifications_sent": [],
            "is_active": True,
        })
    return records
