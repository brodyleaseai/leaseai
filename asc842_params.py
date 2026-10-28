"""Map extracted lease fields onto ASC 842 calculator inputs."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

NOT_FOUND = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "—", "-"}

FIELD_ALIASES = {
    "commencement_date": (
        "Lease Commencement Date",
        "Rent Commencement Date",
        "Lease Start Date",
    ),
    "end_date": (
        "Lease Expiration Date",
        "Lease End Date",
        "Expiration Date",
    ),
    "term_months": (
        "Lease Term (Total Months)",
        "Lease Term (total months)",
        "Lease Term",
    ),
    "monthly_payment": (
        "Base Rent Year 1 (monthly)",
        "Base Rent Year 1 (Monthly)",
        "Base Rent Year 1 monthly",
        "Base Rent",
    ),
    "annual_increase": (
        "Annual Escalation Rate or Cap",
        "Annual Escalation Rate",
        "Annual Rent Escalation Rate",
    ),
    "escalation_type": (
        "Annual Escalation Type (Fixed / CPI / Percentage)",
        "Annual Escalation Type",
        "Annual Rent Escalation Type",
    ),
    "renewal_count": ("Number of Renewal Options",),
    "renewal_length": ("Renewal Option Term Length",),
    "termination_right": ("Early Termination Right",),
    "termination_fee": ("Early Termination Fee / Penalty",),
    "incentives": ("Tenant Improvement Allowance (TIA)", "Lease Incentives"),
    "prepayments": ("Prepaid Rent", "Rent Paid in Advance"),
}


def _usable_text(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text if text.upper() not in NOT_FOUND else ""


def _field_value(fields: Dict[str, Any], names: Iterable[str]) -> str:
    for name in names:
        raw = fields.get(name)
        if raw is None:
            continue
        if isinstance(raw, dict):
            for key in ("reviewed_value", "raw_value", "value"):
                text = _usable_text(raw.get(key))
                if text:
                    return text
        else:
            text = _usable_text(raw)
            if text:
                return text
    return ""


def parse_money(value: str, default: float = 0.0) -> float:
    if not value:
        return default
    match = re.search(r"-?[\d,]+(?:\.\d+)?", value.replace(" ", ""))
    if not match:
        return default
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return default


def parse_percent(value: str, default: float = 0.0) -> float:
    if not value:
        return default
    match = re.search(r"-?[\d.]+", value)
    if not match:
        return default
    try:
        number = float(match.group(0))
    except ValueError:
        return default
    if number > 1 and "%" in value:
        return number
    if number <= 1 and "%" not in value and "percent" not in value.lower():
        return number * 100
    return number


def is_duration_formula(value: str) -> bool:
    """True when the value is a term formula, not a calendar end date."""
    lower = (value or "").lower()
    if "conditional" in lower:
        return True
    return bool(re.search(r"\d+\s+months?\s+(from|after|following)", lower))


def parse_date_value(value: str) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    leading = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    if leading:
        try:
            return datetime.strptime(leading.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    if is_duration_formula(text):
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:32], fmt).date()
        except ValueError:
            continue
    if not re.search(
        r"\d{1,2}/\d{1,2}/\d{2,4}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b",
        text,
        re.I,
    ):
        return None
    try:
        from dateutil import parser
        return parser.parse(text, fuzzy=True).date()
    except Exception:
        return None


def _add_months(start: date, months: int) -> date:
    try:
        from dateutil.relativedelta import relativedelta
        return start + relativedelta(months=months)
    except Exception:
        return start + timedelta(days=int(months * 30.44))


def parse_months(value: str, default: int = 0) -> int:
    if not value:
        return default
    lower = value.lower()
    year_match = re.search(r"(\d+(?:\.\d+)?)\s*year", lower)
    month_match = re.search(r"(\d+)\s*month", lower)
    if year_match and ("year" in lower):
        return int(round(float(year_match.group(1)) * 12))
    if month_match:
        return int(month_match.group(1))
    number = re.search(r"(\d+)", value)
    if not number:
        return default
    amount = int(number.group(1))
    if amount <= 30 and "option" not in lower:
        return amount * 12 if amount <= 15 else amount
    return amount


def looks_true(value: str) -> bool:
    if not value:
        return False
    lower = value.lower()
    if any(token in lower for token in ("not found", "none", "n/a", "no right", "not applicable")):
        return False
    return any(token in lower for token in ("yes", "option", "right", "tenant may", "permitted", "has "))


def fields_from_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    mapped = {}
    for row in rows or []:
        name = row.get("field_name")
        if name:
            mapped[name] = row
    return mapped


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def widget_key(lease_id: Any, name: str) -> str:
    """Streamlit widget keys must change when the selected lease changes."""
    return f"asc842_{lease_id}_{name}"


def source_labels(params: Dict[str, Any]) -> List[str]:
    labels = []
    if params.get("source_commencement"):
        labels.append("commencement date")
    if params.get("source_end"):
        labels.append("end date")
    if params.get("source_rent"):
        labels.append("monthly rent")
    if params.get("source_increase"):
        labels.append("annual increase")
    return labels


def params_from_extracted_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Return widget defaults for one lease. Missing terms keep safe blanks/zeros."""
    commence_text = _field_value(fields, FIELD_ALIASES["commencement_date"])
    end_text = _field_value(fields, FIELD_ALIASES["end_date"])
    term_text = _field_value(fields, FIELD_ALIASES["term_months"])
    commence = parse_date_value(commence_text)
    end = parse_date_value(end_text)
    term_months = parse_months(term_text)
    if not term_months and is_duration_formula(end_text):
        term_months = parse_months(end_text)
    if commence and term_months and (not end or is_duration_formula(end_text)):
        end = _add_months(commence, term_months)
    if commence and end and not term_months:
        term_months = max(1, (end.year - commence.year) * 12 + (end.month - commence.month))

    renewal_raw = _field_value(fields, FIELD_ALIASES["renewal_count"])
    renewal_match = re.search(r"(\d+)", renewal_raw)
    renewal_count = int(renewal_match.group(1)) if renewal_match else 0
    renewal_length = parse_months(_field_value(fields, FIELD_ALIASES["renewal_length"]))
    termination_text = _field_value(fields, FIELD_ALIASES["termination_right"])
    escalation_type = _field_value(fields, FIELD_ALIASES["escalation_type"])

    return {
        "commencement_date": commence or date.today(),
        "end_date": end or _add_years(commence or date.today(), 3),
        "monthly_payment": parse_money(_field_value(fields, FIELD_ALIASES["monthly_payment"]), 0.0),
        "annual_increase": parse_percent(_field_value(fields, FIELD_ALIASES["annual_increase"]), 0.0),
        "has_variable": "cpi" in escalation_type.lower() or "index" in escalation_type.lower(),
        "has_renewal": renewal_count > 0 or renewal_length > 0,
        "renewal_months": renewal_length or 12,
        "has_termination": looks_true(termination_text),
        "termination_penalty": parse_money(_field_value(fields, FIELD_ALIASES["termination_fee"]), 0.0),
        "lease_incentives": parse_money(_field_value(fields, FIELD_ALIASES["incentives"]), 0.0),
        "prepayments": parse_money(_field_value(fields, FIELD_ALIASES["prepayments"]), 0.0),
        "source_commencement": bool(commence),
        "source_end": bool(end),
        "source_rent": bool(_field_value(fields, FIELD_ALIASES["monthly_payment"])),
        "source_increase": bool(_field_value(fields, FIELD_ALIASES["annual_increase"])),
    }
