"""Deterministic rent schedule for client abstracts.

The lease often states Year 1 rent and a fixed annual increase without a
year-by-year exhibit. GPT must not put those calculated dollars into
extracted Year 2–5 fields at HIGH confidence. This module expands a
schedule through expiration and marks each row Extracted or Calculated.
"""

from __future__ import annotations

import copy
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

YEAR_FIELDS = [f"Base Rent Year {n} (monthly)" for n in range(1, 6)]
COMPUTED_FIELD = "Computed Rent Schedule (through expiration)"
META_KEY = "_computed_rent_schedule"

SKIP_TYPE_MARKERS = ("CPI", "INDEX", "FMV", "FAIR MARKET", "MARKET RENT")
COMPUTE_TYPE_MARKERS = ("FIXED", "PERCENT", "ANNUAL", "ESCALAT")
NOT_STATED = "Not stated in the lease"
NOT_FOUND = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "—", "-", NOT_STATED.upper()}

MONEY_RE = re.compile(r"\$?\s*([\d,]+(?:\.\d{1,2})?)")
RATE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
MONTHS_RE = re.compile(r"(\d+)")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()


def _names_match(key: str, candidate: str) -> bool:
    nk, nc = _norm(key), _norm(candidate)
    return nk == nc or nk.startswith(nc + " ")


def _field_get(fields: Dict[str, Any], *candidates: str) -> Tuple[str, Dict[str, Any]]:
    for key, payload in (fields or {}).items():
        if str(key).startswith("_"):
            continue
        if any(_names_match(key, name) for name in candidates):
            return key, payload if isinstance(payload, dict) else {"value": payload}
    return "", {}


def _text(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("value", "reviewed_value", "raw_value", "governing_value"):
            text = str(payload.get(key) or "").strip()
            if text:
                return text
        return ""
    return str(payload or "").strip()


def _snippet(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("source_snippet")
        or payload.get("source_text")
        or payload.get("excerpt")
        or ""
    )


def _is_blank(value: str) -> bool:
    return str(value or "").strip().upper() in NOT_FOUND


def parse_money(value: Any) -> Optional[float]:
    match = MONEY_RE.search(str(value or ""))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_rate(value: Any) -> Optional[float]:
    text = str(value or "")
    match = RATE_RE.search(text)
    if match:
        return float(match.group(1))
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        number = float(cleaned) if cleaned else None
    except ValueError:
        return None
    if number is None:
        return None
    if number > 25:
        return None
    return number


def parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if _is_blank(text):
        return None
    try:
        parsed = date_parser.parse(text, fuzzy=True, default=date(2099, 1, 1))
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.year == 2099 and "2099" not in text:
        return None
    return parsed.date() if hasattr(parsed, "date") else parsed


def parse_months(value: Any) -> Optional[int]:
    match = MONTHS_RE.search(str(value or ""))
    if not match:
        return None
    months = int(match.group(1))
    return months if 1 <= months <= 600 else None


def money(amount: float) -> str:
    return f"${amount:,.2f}"


def amount_stated_in_source(amount: Optional[float], snippet: str) -> bool:
    """True only when the dollar figure itself appears in the cited clause."""
    if amount is None or not snippet:
        return False
    variants = {
        f"{amount:,.2f}",
        f"{amount:.2f}",
        f"{amount:,.0f}" if amount == int(amount) else "",
        f"{int(amount)}" if amount == int(amount) else "",
    }
    blob = snippet.replace(" ", "")
    for variant in variants:
        if variant and variant.replace(" ", "") in blob:
            return True
        if variant and variant in snippet:
            return True
    return False


def _escalation_kind(type_text: str) -> str:
    upper = (type_text or "").upper()
    if any(marker in upper for marker in SKIP_TYPE_MARKERS):
        return "skip"
    if any(marker in upper for marker in COMPUTE_TYPE_MARKERS):
        return "fixed"
    if not upper or upper in NOT_FOUND:
        return "unknown"
    return "unknown"


def _add_years(start: date, years: int) -> date:
    try:
        return start + relativedelta(years=years)
    except Exception:
        return start.replace(year=start.year + years, day=min(start.day, 28))


def _months_in_span(start: date, end: date) -> int:
    """Inclusive calendar months that overlap the period."""
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return max(1, months)


def _period_end(anniversary: date, next_anniversary: date, expiration: date) -> date:
    candidate = next_anniversary - timedelta(days=1)
    return min(candidate, expiration)


def build_periods(rent_start: date, expiration: date) -> List[Dict[str, Any]]:
    periods = []
    year = 1
    while True:
        start = _add_years(rent_start, year - 1)
        if start > expiration:
            break
        end = _period_end(start, _add_years(rent_start, year), expiration)
        periods.append({
            "year": year,
            "start": start,
            "end": end,
            "months": _months_in_span(start, end),
        })
        if end >= expiration:
            break
        year += 1
        if year > 60:
            break
    return periods


def _format_period_portable(start: date, end: date) -> str:
    def _one(day: date) -> str:
        return f"{day.strftime('%b')} {day.day}, {day.year}"
    return f"{_one(start)} – {_one(end)}"


def round_cent(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def computed_monthly(year1: float, rate_pct: float, year_number: int) -> float:
    """Compound the billed monthly, rounding half-up to the cent each year."""
    amount = round_cent(year1)
    factor = Decimal("1") + (Decimal(str(rate_pct)) / Decimal("100"))
    for _ in range(1, year_number):
        amount = (amount * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(amount)


def _skip_result(reason: str) -> Dict[str, Any]:
    return {
        "computed": False,
        "reason": reason,
        "rows": [],
        "method": "",
        "rate_pct": None,
        "year1_monthly": None,
    }


def plan_rent_schedule(fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    fields = fields or {}
    _, year1_field = _field_get(fields, "Base Rent Year 1 (monthly)", "Base Rent Year 1")
    year1 = parse_money(_text(year1_field))
    if year1 is None:
        return _skip_result("Year 1 monthly rent is not on this file")

    _, type_field = _field_get(
        fields,
        "Annual Escalation Type (Fixed / CPI / Percentage)",
        "Annual Escalation Type",
    )
    kind = _escalation_kind(_text(type_field))
    if kind == "skip":
        return _skip_result(
            "The lease uses CPI, FMV, or another non-fixed increase, so LeaseAI did not expand a rent table"
        )

    _, rate_field = _field_get(fields, "Annual Escalation Rate or Cap", "Annual Escalation Rate")
    rate_pct = parse_rate(_text(rate_field))
    if rate_pct is None:
        if kind == "unknown":
            return _skip_result("No fixed annual increase was extracted")
        return _skip_result("A fixed increase was noted but no percentage was extracted")

    _, rent_field = _field_get(fields, "Rent Commencement Date")
    _, commence_field = _field_get(fields, "Lease Commencement Date")
    _, expire_field = _field_get(fields, "Lease Expiration Date")
    _, term_field = _field_get(fields, "Lease Term (Total Months)")

    rent_start = parse_date(_text(rent_field)) or parse_date(_text(commence_field))
    if rent_start is None:
        return _skip_result("Rent commencement (or lease commencement) is missing, so the anniversary is unclear")

    expiration = parse_date(_text(expire_field))
    term_months = parse_months(_text(term_field))
    commence = parse_date(_text(commence_field))
    if expiration is None and term_months and commence:
        expiration = commence + relativedelta(months=term_months) - timedelta(days=1)
    elif expiration is None and term_months:
        expiration = rent_start + relativedelta(months=term_months) - timedelta(days=1)
    if expiration is None or expiration < rent_start:
        return _skip_result("Lease expiration is missing, so the schedule cannot run through the term")

    stated = {}
    for index, name in enumerate(YEAR_FIELDS, start=1):
        key, payload = _field_get(fields, name, f"Base Rent Year {index}")
        amount = parse_money(_text(payload))
        if amount is None:
            continue
        if amount_stated_in_source(amount, _snippet(payload)):
            stated[index] = {"amount": amount, "key": key, "payload": payload}

    periods = build_periods(rent_start, expiration)
    rows = []
    for period in periods:
        year = period["year"]
        if year in stated:
            monthly = stated[year]["amount"]
            basis = "Extracted"
        else:
            monthly = computed_monthly(year1, rate_pct, year)
            basis = "Calculated" if year > 1 else "Extracted"
            if year == 1:
                monthly = year1
                basis = "Extracted"
        annual = round(monthly * period["months"], 2)
        rows.append({
            "year": year,
            "start": period["start"],
            "end": period["end"],
            "period": _format_period_portable(period["start"], period["end"]),
            "months": period["months"],
            "monthly": monthly,
            "annual": annual,
            "basis": basis,
            "monthly_display": money(monthly),
            "annual_display": money(annual),
        })

    method = (
        f"{rate_pct:g}% compounded on each anniversary of rent commencement "
        f"({_format_period_portable(rent_start, rent_start).split(' – ')[0]}), "
        f"rounded to the nearest cent"
    )
    return {
        "computed": True,
        "reason": "",
        "rows": rows,
        "method": method,
        "rate_pct": rate_pct,
        "year1_monthly": year1,
        "rent_start": rent_start,
        "expiration": expiration,
        "stated_years": sorted(stated),
    }


def _schedule_text(plan: Dict[str, Any]) -> str:
    lines = []
    for row in plan["rows"]:
        lines.append(
            f"Year {row['year']} | {row['period']} | {row['monthly_display']}/mo "
            f"| {row['annual_display']} | {row['basis']}"
        )
    lines.append(f"Method: {plan['method']}.")
    return "\n".join(lines)


def apply_computed_rent_schedule(fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Label invented Year 2–5 amounts and attach a through-expiration schedule."""
    updated = copy.deepcopy(fields or {})
    plan = plan_rent_schedule(updated)
    updated[META_KEY] = {
        "computed": plan["computed"],
        "reason": plan.get("reason") or "",
        "method": plan.get("method") or "",
        "rate_pct": plan.get("rate_pct"),
        "rows": [
            {
                "year": row["year"],
                "period": row["period"],
                "months": row["months"],
                "monthly": row["monthly"],
                "annual": row["annual"],
                "basis": row["basis"],
                "monthly_display": row["monthly_display"],
                "annual_display": row["annual_display"],
            }
            for row in plan.get("rows") or []
        ],
    }
    if not plan["computed"]:
        return updated

    parent = "Base Rent Year 1 (monthly); Annual Escalation Rate or Cap"
    note = (
        f"LeaseAI calculated this amount from Year 1 rent compounded at "
        f"{plan['rate_pct']:g}% annually. It is not quoted from a year-by-year exhibit."
    )
    by_year = {row["year"]: row for row in plan["rows"]}
    for index, name in enumerate(YEAR_FIELDS[1:], start=2):
        row = by_year.get(index)
        if not row:
            continue
        key, payload = _field_get(updated, name, f"Base Rent Year {index}")
        amount = parse_money(_text(payload))
        if key and amount is not None and amount_stated_in_source(amount, _snippet(payload)):
            continue
        payload = dict(payload) if payload else {}
        payload["value"] = row["monthly_display"]
        payload["confidence"] = "COMPUTED"
        payload["source_snippet"] = plan["method"]
        payload["derived_from"] = parent
        payload["notes"] = note
        updated[key or name] = payload

    updated[COMPUTED_FIELD] = {
        "value": _schedule_text(plan),
        "confidence": "COMPUTED",
        "source_snippet": plan["method"],
        "derived_from": parent,
        "notes": plan["method"],
    }
    return updated


def is_meta_key(name: str) -> bool:
    return str(name).startswith("_")


def is_hidden_schedule_key(name: str) -> bool:
    """Hide engine metadata and the duplicate computed-field blob from the extracted table."""
    return is_meta_key(name) or str(name) == COMPUTED_FIELD
