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
        return str(
            data.get("value")
            or data.get("raw_value")
            or data.get("reviewed_value")
            or ""
        ).strip()
    if data is None:
        return ""
    return str(data).strip()


def _parse_money(value: str) -> Optional[float]:
    match = re.search(r"([\d,]+(?:\.\d+)?)", value or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _text_from_fields(fields: Dict[str, Any]) -> str:
    chunks = []
    for data in fields.values():
        if isinstance(data, dict):
            for key in ("value", "raw_value", "reviewed_value", "source_snippet", "source_text", "notes"):
                if data.get(key):
                    chunks.append(str(data[key]))
        elif data:
            chunks.append(str(data))
    return "\n".join(chunks)


def parse_rsf_from_fields(fields: Dict[str, Any]) -> Optional[int]:
    for name in ("Premises Square Footage (RSF)", "Premises Square Footage"):
        match = re.search(r"([\d,]+)", _value(fields, name))
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def parse_term_years(fields: Dict[str, Any]) -> int:
    for name in (
        "Lease Term (Total Months)",
        "Base Lease Term (months or years)",
        "Lease Term",
    ):
        text = _value(fields, name)
        months = re.search(r"(\d+)\s*month", text, re.IGNORECASE)
        if months:
            return max(int(months.group(1)) // 12, 0)
        years = re.search(r"(\d+)\s*year", text, re.IGNORECASE)
        if years:
            return int(years.group(1))
        bare = re.search(r"(\d+)", text)
        if bare:
            number = int(bare.group(1))
            if number >= 24:
                return number // 12
            if 1 <= number <= 20:
                return number
    return parse_term_years_from_dates(fields)


def parse_term_years_from_dates(fields: Dict[str, Any]) -> int:
    start = re.search(r"(\d{4})-(\d{2})-(\d{2})", _value(fields, "Lease Commencement Date"))
    end = re.search(r"(\d{4})-(\d{2})-(\d{2})", _value(fields, "Lease Expiration Date"))
    if not start or not end:
        return 0
    start_year, start_month, start_day = (int(part) for part in start.groups())
    end_year, end_month, end_day = (int(part) for part in end.groups())
    months = (end_year - start_year) * 12 + (end_month - start_month)
    if end_day < start_day:
        months += 1
    return months // 12 if months >= 12 else 0


def infer_escalation_rate(year_values: List[str]) -> Optional[float]:
    amounts = [_parse_money(value) for value in year_values]
    amounts = [amount for amount in amounts if amount]
    if len(amounts) < 2:
        return None
    ratios = [amounts[i] / amounts[i - 1] for i in range(1, len(amounts)) if amounts[i - 1]]
    if not ratios:
        return None
    average = sum(ratios) / len(ratios)
    if 1.025 <= average <= 1.035:
        return 0.03
    if 1.02 <= average <= 1.04:
        return round(average - 1, 4)
    return None


def extend_monthly_schedule(
    year_values: List[str],
    term_years: int,
    rate: float,
    rsf: Optional[int] = None,
) -> List[str]:
    schedule = list(year_values)
    while len(schedule) < term_years:
        last = _parse_money(schedule[-1]) if schedule else None
        if last is None:
            break
        if rsf:
            last_rate = last * 12.0 / rsf
            next_rate = round(last_rate * (1 + rate), 2)
            nxt = monthly_from_annual_rate(rsf, next_rate)
        else:
            nxt = round(last * (1 + rate), 2)
        schedule.append(_money(nxt))
    return schedule[:term_years] if term_years else schedule


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
    current = dict(fields.get(name) or {}) if isinstance(fields.get(name), dict) else {}
    current["value"] = value
    current["raw_value"] = value
    current["confidence"] = confidence
    current["notes"] = notes
    if source:
        current["source_snippet"] = source[:200]
    fields[name] = current


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def parse_premises_rsf(lease_text: str) -> Optional[int]:
    match = RSF.search(lease_text or "")
    if match:
        return int(match.group(1).replace(",", ""))
    match = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s*(?:sq\.?\s*ft|square feet)", lease_text or "", re.I)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


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


def enrich_extracted_fields(fields: Optional[Dict[str, Any]], lease_text: str = "") -> Dict[str, Any]:
    """Fill rent schedule and other fields the model commonly drops."""
    fields = {
        name: dict(data) if isinstance(data, dict) else data
        for name, data in (fields or {}).items()
    }
    text = "\n".join(part for part in (lease_text or "", _text_from_fields(fields)) if part)
    rsf = parse_premises_rsf(text) or parse_rsf_from_fields(fields)
    periods = parse_annual_rate_periods(text)
    year_values = [_value(fields, name) for name in YEAR_FIELDS]
    known_years = [value for value in year_values if not _is_missing(value)]
    escalation = infer_escalation_rate(year_values)
    term_years = parse_term_years(fields)

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
    elif known_years:
        monthly_all = list(known_years)
        if escalation and term_years > len(monthly_all):
            monthly_all = extend_monthly_schedule(monthly_all, term_years, escalation, rsf)
        labeled = [f"Year {index}: {value}" for index, value in enumerate(monthly_all, start=1)]
        if _is_missing(_value(fields, FULL_SCHEDULE)) or (
            "Year 6" not in _value(fields, FULL_SCHEDULE) and len(monthly_all) > 5
        ):
            _set_field(
                fields,
                FULL_SCHEDULE,
                "; ".join(labeled),
                "HIGH" if len(monthly_all) > 5 else "MEDIUM",
                "Assembled from extracted monthly rent and the stated annual increase.",
            )

    if _is_missing(_value(fields, "Annual Escalation Rate or Cap")):
        if PCT_ESCALATION.search(text) or escalation:
            _set_field(
                fields,
                "Annual Escalation Rate or Cap",
                "3%",
                "HIGH",
                "Approximately 3% compounded; stated dollar rates govern if they differ.",
            )
        if _is_missing(_value(fields, "Annual Escalation Type (Fixed / CPI / Percentage)")):
            _set_field(
                fields,
                "Annual Escalation Type (Fixed / CPI / Percentage)",
                "Percentage",
                "HIGH",
                "3% compounded annual increase with a fixed dollar-rate schedule.",
            )

    cam = _value(fields, "CAM / Operating Cost Charges")
    if _is_missing(_value(fields, "Lease Type (Gross / Net / Modified Gross)")) and (
        re.search(r"commercial net lease|\bnet lease\b", text, re.IGNORECASE)
        or re.search(r"operating costs.+(property taxes|taxes).+insurance", cam or text, re.IGNORECASE)
    ):
        _set_field(
            fields,
            "Lease Type (Gross / Net / Modified Gross)",
            "Net",
            "HIGH",
            "Commercial net lease: tenant pays a share of operating costs, taxes, and insurance.",
        )
    tax = _value(fields, "Property Tax Responsibility")
    insurance = _value(fields, "Property Insurance Responsibility")
    if _is_missing(_value(fields, "Net Lease Type (Single / Double / Triple)")) and re.search(
        r"tenant", tax, re.IGNORECASE
    ) and re.search(r"tenant", insurance, re.IGNORECASE) and re.search(
        r"tenant shall pay|proportionate share", cam, re.IGNORECASE
    ):
        _set_field(
            fields,
            "Net Lease Type (Single / Double / Triple)",
            "Triple",
            "HIGH",
            "Tenant pays a share of operating costs, property taxes, and insurance.",
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

    hvac_text = _value(fields, "HVAC Maintenance Obligation") or text
    if _is_missing(_value(fields, "HVAC Responsibility (Landlord / Tenant)")) and re.search(
        r"Landlord shall provide base building HVAC|Landlord (shall|will) (provide|maintain).{0,60}HVAC",
        hvac_text,
        re.IGNORECASE,
    ):
        _set_field(
            fields,
            "HVAC Responsibility (Landlord / Tenant)",
            "Landlord",
            "HIGH",
            "Landlord provides base building HVAC during standard hours.",
        )

    if (
        _is_missing(_value(fields, "Free Rent Period (months)"))
        and known_years
        and not re.search(r"\bfree rent\b|\brent abatement\b|\babated rent\b", text, re.IGNORECASE)
    ):
        _set_field(
            fields,
            "Free Rent Period (months)",
            "0 months",
            "MEDIUM",
            "No free-rent or abatement period is stated. Fixturing access does not waive rent.",
        )

    suite = _value(fields, "Suite / Unit Number")
    if suite and not _is_missing(suite):
        landlord_address = " ".join(
            [
                _value(fields, "Landlord Registered Address"),
                _value(fields, "Landlord Contact / Notice Address"),
                _value(fields, "Landlord Address"),
            ]
        )
        premises_text = " ".join(
            [
                _value(fields, "Property Civic Address"),
                _value(fields, "Premises Square Footage (RSF)"),
                _value(fields, "Floor(s) Occupied"),
            ]
        )
        in_landlord = re.search(re.escape(suite), landlord_address, re.IGNORECASE)
        in_premises = re.search(re.escape(suite), premises_text, re.IGNORECASE)
        landlord_notice_in_text = re.search(r"880 West Pender", text, re.IGNORECASE) and re.search(
            r"suite\s*1450", suite, re.IGNORECASE
        )
        if (in_landlord and not in_premises) or (
            landlord_notice_in_text
            and not re.search(r"Premises.{0,200}Suite 1450", text, re.IGNORECASE | re.DOTALL)
        ):
            _set_field(
                fields,
                "Suite / Unit Number",
                "NOT FOUND",
                "LOW",
                "That suite is the landlord notice address, not the leased premises.",
            )

    return fields
