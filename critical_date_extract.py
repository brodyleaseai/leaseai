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
    "renewal_term": ("Renewal Option Term Length",),
    "termination": ("Early Termination Right",),
    "termination_notice": (
        "Termination Notice Period",
        "Termination Notice Deadline",
    ),
    "expansion": ("Expansion Option",),
    "rofo": ("Right of First Offer",),
    "rofr": ("Right of First Refusal",),
    "free_rent": ("Free Rent Period (months)", "Free Rent Period"),
}

WORD_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def parse_count(value: str) -> Optional[int]:
    """Read 9, (9), or nine from a short numeric phrase."""
    if not value:
        return None
    text = value.strip()
    paren = re.search(r"\((\d+)\)", text)
    if paren:
        return int(paren.group(1))
    digit = re.search(r"(\d+)", text)
    if digit:
        return int(digit.group(1))
    words = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))
    word = re.search(rf"\b({words})\b", text, re.I)
    if word:
        return WORD_NUMBERS[word.group(1).lower()]
    return None


def is_affirmative_option(value: str) -> bool:
    text = (value or "").strip()
    if not text or text.upper() in NOT_FOUND:
        return False
    return not bool(re.match(r"^(no|none|n/?a|false|0)\b", text, re.I))


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


def _notice_window(text: str) -> tuple[Optional[int], Optional[int]]:
    """Return (earliest months prior, latest months prior) from a notice clause."""
    if not text:
        return None, None
    lower = text.lower()
    latest = None
    earliest = None
    for match in re.finditer(
        r"(?:at least|not less than|minimum of)\s+(.+?)\s+months?",
        lower,
    ):
        latest = parse_count(match.group(1)) or latest
    for match in re.finditer(
        r"(?:nor more than|not more than|no more than|at most|maximum of)\s+(.+?)\s+months?",
        lower,
    ):
        earliest = parse_count(match.group(1)) or earliest
    if latest is None and earliest is None:
        prior = re.search(r"(.+?)\s+months?\s+(?:prior|before|preceding)", lower)
        if prior:
            latest = parse_count(prior.group(1))
        elif not parse_calendar_date(text):
            latest = parse_months(text) or None
    return earliest, latest


def _notice_months_prior(text: str) -> Optional[int]:
    """Use the latest allowed notice (smallest 'at least N months prior')."""
    earliest, latest = _notice_window(text)
    return latest or earliest


def _note_row(date_type: str, value: str, description: str, source_field: str) -> Dict[str, str]:
    return {
        "date_type": date_type,
        "date_value": value,
        "description": description,
        "source_field": source_field,
    }


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
    renewal_count_text = field_value(fields, FIELD_ALIASES["renewal_count"])
    renewal_term_text = field_value(fields, FIELD_ALIASES["renewal_term"])
    expansion_text = field_value(fields, FIELD_ALIASES["expansion"])
    termination_text = field_value(fields, FIELD_ALIASES["termination"])
    termination_notice_text = field_value(fields, FIELD_ALIASES["termination_notice"])
    free_rent_text = field_value(fields, FIELD_ALIASES["free_rent"])
    rofo_text = field_value(fields, FIELD_ALIASES["rofo"])
    rofr_text = field_value(fields, FIELD_ALIASES["rofr"])

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

    earliest_notice, latest_notice = _notice_window(notice_text)
    if expiration and earliest_notice:
        rows.append(_row(
            "Renewal Notice Window Opens",
            add_months(expiration, -earliest_notice),
            notice_text or f"{earliest_notice} months prior to expiration",
            "Renewal Notice Deadline",
        ))
    if expiration and latest_notice:
        rows.append(_row(
            "Renewal Notice Deadline",
            add_months(expiration, -latest_notice),
            notice_text or f"{latest_notice} months prior to expiration",
            "Renewal Notice Deadline",
        ))
    else:
        notice_date = parse_calendar_date(notice_text)
        if notice_date:
            rows.append(_row("Renewal Notice Deadline", notice_date, notice_text, "Renewal Notice Deadline"))
        elif notice_text and is_affirmative_option(notice_text):
            rows.append(_note_row("Renewal Notice Deadline", "See notes", notice_text, "Renewal Notice Deadline"))

    if expiration and (is_affirmative_option(renewal_count_text) or is_affirmative_option(renewal_term_text)):
        option_note = " / ".join(part for part in (renewal_count_text, renewal_term_text) if part)
        if notice_text:
            option_note = f"{option_note}; {notice_text}" if option_note else notice_text
        rows.append(_row(
            "Renewal Option Commencement",
            expiration,
            option_note or "Renewal option begins at expiration",
            "Number of Renewal Options",
        ))
    elif is_affirmative_option(renewal_count_text) or is_affirmative_option(renewal_term_text):
        option_note = " / ".join(part for part in (renewal_count_text, renewal_term_text, notice_text) if part)
        rows.append(_note_row("Renewal Option", "See notes", option_note, "Number of Renewal Options"))

    if commence and parse_months(free_rent_text):
        rows.append(_row(
            "Free Rent Ends",
            add_months(commence, parse_months(free_rent_text)),
            free_rent_text,
            "Free Rent Period (months)",
        ))

    termination_date = parse_calendar_date(termination_text)
    if termination_date:
        rows.append(_row("Early Termination Right", termination_date, termination_text, "Early Termination Right"))
    elif is_affirmative_option(termination_text):
        rows.append(_note_row("Early Termination Right", "See notes", termination_text, "Early Termination Right"))

    termination_notice_date = parse_calendar_date(termination_notice_text)
    if termination_notice_date:
        rows.append(_row(
            "Termination Notice Deadline",
            termination_notice_date,
            termination_notice_text,
            "Termination Notice Period",
        ))
    elif is_affirmative_option(termination_notice_text):
        rows.append(_note_row(
            "Termination Notice Deadline",
            "See notes",
            termination_notice_text,
            "Termination Notice Period",
        ))

    expansion_date = parse_calendar_date(expansion_text)
    if expansion_date:
        rows.append(_row("Expansion Option Deadline", expansion_date, expansion_text, "Expansion Option"))
    elif is_affirmative_option(expansion_text):
        rows.append(_note_row("Expansion Option", "See notes", expansion_text, "Expansion Option"))

    if is_affirmative_option(rofo_text):
        rofo_date = parse_calendar_date(rofo_text)
        if rofo_date:
            rows.append(_row("Right of First Offer", rofo_date, rofo_text, "Right of First Offer"))
        else:
            rows.append(_note_row("Right of First Offer", "See notes", rofo_text, "Right of First Offer"))
    if is_affirmative_option(rofr_text):
        rofr_date = parse_calendar_date(rofr_text)
        if rofr_date:
            rows.append(_row("Right of First Refusal", rofr_date, rofr_text, "Right of First Refusal"))
        else:
            rows.append(_note_row("Right of First Refusal", "See notes", rofr_text, "Right of First Refusal"))

    unique = []
    seen = set()
    for row in rows:
        key = (row["date_type"], row["date_value"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    unique.sort(key=lambda item: (
        0 if ISO_DATE.match(item["date_value"]) else 1,
        item["date_value"],
        item["date_type"],
    ))
    return unique


def records_for_database(lease_id: str, dates: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
    records = []
    for item in dates:
        if not ISO_DATE.match(item.get("date_value") or ""):
            continue
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
