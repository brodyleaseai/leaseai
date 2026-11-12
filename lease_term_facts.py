"""Typed, de-identified lease-term facts for the terms warehouse.

Incoming processing still writes each customer's system of record
(leases / extracted_fields). This module copies *numbers and market
dimensions only* into lease_term_facts. Party names, street addresses,
filenames, and source excerpts are dropped.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

EXPORT_OMIT = {"id", "lease_id", "client_id", "created_at", "updated_at"}
PII_FIELD_NAMES = {
    "Landlord Legal Name",
    "Landlord Registered Address",
    "Landlord Contact / Notice Address",
    "Tenant Legal Name",
    "Tenant Trade Name (if different)",
    "Tenant Registered Address",
    "Guarantor Name(s)",
}

MONEY = re.compile(r"\$?\s*([\d,]+(?:\.\d+)?)")
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
INTEGER = re.compile(r"(-?\d{1,9})")
MONTHS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:months?|mos?)\b", re.IGNORECASE)
RSF = re.compile(
    r"(\d{1,3}(?:,\d{3})+|\d+)\s*(?:rentable square feet|rsf|sq\.?\s*ft|square feet)?",
    re.IGNORECASE,
)
YES = re.compile(r"\b(yes|true|included|tenant has|landlord has)\b", re.IGNORECASE)
ZIP = re.compile(r"\s+\d{5}(?:-\d{4})?\s*$")

# Current clause-history values overlay extracted fields after amendments.
CLAUSE_TO_FIELD = {
    "Base Rent": "Base Rent Year 1 (monthly)",
    "Rent Escalations": "Annual Escalation Rate or Cap",
    "Security Deposit": "Security Deposit Amount",
    "Free Rent Period": "Free Rent Period (months)",
    "CAM Cap": "CAM Annual Increase Cap (%)",
    "Lease Term": "Lease Term (Total Months)",
    "Commencement Date": "Lease Commencement Date",
    "Expiration Date": "Lease Expiration Date",
    "Renewal Options": "Number of Renewal Options",
    "Renewal Term Length": "Renewal Option Term Length",
    "Renewal Notice Deadline": "Renewal Notice Deadline",
    "Premises Description": "Premises Square Footage (RSF)",
    "Termination Rights": "Early Termination Right",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _field_map(rows: Iterable[dict]) -> Dict[str, str]:
    mapped: Dict[str, str] = {}
    for row in rows or []:
        name = _clean(row.get("field_name"))
        if not name or name in PII_FIELD_NAMES:
            continue
        value = _clean(row.get("reviewed_value")) or _clean(row.get("raw_value"))
        if value and value.upper() != "NOT FOUND":
            mapped[name] = value
    return mapped


def _first(mapped: Dict[str, str], *names: str) -> str:
    for name in names:
        if mapped.get(name):
            return mapped[name]
    return ""


def parse_money(text: str) -> Optional[float]:
    match = MONEY.search(text or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_percent(text: str) -> Optional[float]:
    match = PERCENT.search(text or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_number(text: str) -> Optional[float]:
    if not text:
        return None
    money = parse_money(text)
    if money is not None and "$" in text:
        return money
    match = RSF.search(text)
    if not match:
        match = INTEGER.search(text.replace(",", ""))
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_int(text: str) -> Optional[int]:
    value = parse_number(text)
    if value is None:
        return None
    return int(round(value))


def parse_int_months(text: str) -> Optional[int]:
    value = parse_months(text)
    if value is None:
        return None
    return int(round(value))


def parse_months(text: str) -> Optional[float]:
    match = MONTHS.search(text or "")
    if match:
        return float(match.group(1))
    years = re.search(r"(\d+(?:\.\d+)?)\s*years?\b", text or "", re.IGNORECASE)
    if years:
        return float(years.group(1)) * 12.0
    return parse_number(text or "")


def parse_year(text: str) -> Optional[int]:
    cleaned = _clean(text)
    if not cleaned:
        return None
    try:
        if re.match(r"\d{4}-\d{2}-\d{2}", cleaned):
            return datetime.strptime(cleaned[:10], "%Y-%m-%d").year
    except ValueError:
        pass
    stripped = cleaned.replace(",", " ")
    for fmt in ("%B %d %Y", "%b %d %Y", "%m/%d/%Y", "%m/%d/%y", "%Y"):
        try:
            return datetime.strptime(stripped[:32], fmt).year
        except ValueError:
            continue
    match = re.search(r"\b(19|20)\d{2}\b", cleaned)
    return int(match.group(0)) if match else None


def parse_market(address: str) -> Dict[str, Optional[str]]:
    """City / region / country only. Street lines are discarded."""
    parts = [part.strip() for part in _clean(address).split(",") if part.strip()]
    locality = region = country = None
    if len(parts) >= 3:
        locality = parts[-2]
        region = ZIP.sub("", parts[-1]).strip()
        if re.match(r"^\d+", locality or ""):
            locality = None
    elif len(parts) == 2:
        left, right = parts[0], ZIP.sub("", parts[1]).strip()
        if not re.match(r"^\d+", left):
            locality, region = left, right
        else:
            region = right
    if region and region.upper() in {"US", "USA", "UNITED STATES"}:
        country = "US"
        region = None
    elif region and len(region) <= 3:
        country = "CA" if region.upper() in {"BC", "AB", "ON", "QC", "MB", "SK", "NS", "NB", "NL", "PE", "NT", "NU", "YT"} else country
    return {"country": country, "region": region or None, "locality": locality or None}


def _flag(text: str) -> Optional[bool]:
    if not text:
        return None
    if YES.search(text) and not re.search(r"\b(no|none|not granted)\b", text, re.IGNORECASE):
        return True
    if re.search(r"\b(no|none|n/a|not granted)\b", text, re.IGNORECASE):
        return False
    return None


def overlay_current_clauses(
    mapped: Dict[str, str],
    history_rows: Optional[Iterable[dict]] = None,
) -> Dict[str, str]:
    """Prefer the controlling amendment-graph value when it exists."""
    for row in history_rows or []:
        if row.get("is_current") is False:
            continue
        field = CLAUSE_TO_FIELD.get(_clean(row.get("clause_type")))
        value = _clean(row.get("clause_value"))
        if field and value and value.upper() != "NOT FOUND":
            mapped[field] = value
    return mapped


def _quality(rows: Iterable[dict]) -> str:
    scores = []
    for row in rows or []:
        raw = row.get("confidence_score")
        if isinstance(raw, (int, float)):
            scores.append(float(raw))
        label = _clean(row.get("confidence")).upper()
        if label == "HIGH":
            scores.append(0.9)
        elif label == "MEDIUM":
            scores.append(0.6)
        elif label == "LOW":
            scores.append(0.3)
    if not scores:
        return "unknown"
    avg = sum(scores) / len(scores)
    if avg >= 0.75:
        return "high"
    if avg >= 0.5:
        return "medium"
    return "low"


def build_term_facts(
    lease: Optional[dict],
    field_rows: Optional[Iterable[dict]] = None,
    as_of: Optional[str] = None,
    history_rows: Optional[Iterable[dict]] = None,
) -> Dict[str, Any]:
    """Build one warehouse row. Identifiers stay for upsert; export strips them."""
    lease = lease or {}
    rows = list(field_rows or [])
    mapped = overlay_current_clauses(_field_map(rows), history_rows)
    market = parse_market(_first(mapped, "Property Civic Address") or _clean(lease.get("property_address")))
    rsf = parse_number(_first(mapped, "Premises Square Footage (RSF)"))
    monthly = parse_money(_first(mapped, "Base Rent Year 1 (monthly)"))
    annual = round(monthly * 12.0, 2) if monthly is not None else None
    psf = None
    if rsf and monthly:
        psf = round(monthly * 12.0 / rsf, 4)
    return {
        "lease_id": lease.get("id"),
        "client_id": lease.get("client_id"),
        "as_of": as_of or date.today().isoformat(),
        "review_status": _clean(lease.get("status")) or "EXTRACTED",
        "country": market["country"],
        "region": market["region"],
        "locality": market["locality"],
        "asset_class": _first(mapped, "Building Class") or None,
        "lease_type": _first(mapped, "Lease Type (Gross / Net / Modified Gross)") or None,
        "net_lease_type": _first(mapped, "Net Lease Type (Single / Double / Triple)") or None,
        "commencement_year": parse_year(_first(mapped, "Lease Commencement Date")),
        "expiration_year": parse_year(_first(mapped, "Lease Expiration Date")),
        "term_months": parse_int(_first(mapped, "Lease Term (Total Months)")),
        "rsf": rsf,
        "building_rsf": parse_number(_first(mapped, "Building Total Square Footage")),
        "monthly_rent": monthly,
        "annual_rent": annual,
        "rent_per_rsf_year": psf,
        "free_rent_months": parse_months(_first(mapped, "Free Rent Period (months)")),
        "escalation_type": _first(mapped, "Annual Escalation Type (Fixed / CPI / Percentage)") or None,
        "escalation_pct": parse_percent(_first(mapped, "Annual Escalation Rate or Cap")),
        "cam_cap_pct": parse_percent(_first(mapped, "CAM Annual Increase Cap (%)")),
        "renewal_options": parse_int(_first(mapped, "Number of Renewal Options")),
        "renewal_term_months": parse_int_months(_first(mapped, "Renewal Option Term Length")),
        "renewal_notice_months": parse_int_months(_first(mapped, "Renewal Notice Deadline")),
        "security_deposit": parse_money(_first(mapped, "Security Deposit Amount")),
        "has_percentage_rent": _flag(_first(mapped, "Percentage Rent Clause")),
        "has_early_termination": _flag(_first(mapped, "Early Termination Right")),
        "governing_law": _first(mapped, "Governing Law Jurisdiction") or None,
        "source_quality": _quality(rows),
    }


def export_row(fact: Optional[dict]) -> Dict[str, Any]:
    """Drop internal identifiers. Safe to share when the customer opted in."""
    return {key: value for key, value in (fact or {}).items() if key not in EXPORT_OMIT}


def summarize_facts(rows: Iterable[dict]) -> Dict[str, Any]:
    facts = [export_row(row) for row in rows or []]
    psf = [row["rent_per_rsf_year"] for row in facts if row.get("rent_per_rsf_year")]
    rsf = [row["rsf"] for row in facts if row.get("rsf")]
    esc = [row["escalation_pct"] for row in facts if row.get("escalation_pct") is not None]
    return {
        "leases": len(facts),
        "with_rent_psf": len(psf),
        "avg_rent_per_rsf_year": round(sum(psf) / len(psf), 4) if psf else None,
        "avg_rsf": round(sum(rsf) / len(rsf), 2) if rsf else None,
        "avg_escalation_pct": round(sum(esc) / len(esc), 4) if esc else None,
    }


def _is_missing_table(exc: Exception) -> bool:
    text = str(exc).lower()
    return "lease_term_facts" in text and (
        "does not exist" in text or "could not find" in text or "schema cache" in text
    )


def sync_lease_term_facts(supabase, lease_id: str) -> Optional[dict]:
    """Upsert one lease into the warehouse. No-op if the table is not installed."""
    if not supabase or not lease_id:
        return None
    try:
        lease_rows = (
            supabase.table("leases").select("*").eq("id", lease_id).limit(1).execute().data or []
        )
        if not lease_rows:
            return None
        lease = lease_rows[0]
        fields = (
            supabase.table("extracted_fields").select("*").eq("lease_id", lease_id).execute().data or []
        )
        history = []
        try:
            history = (
                supabase.table("lease_clause_history")
                .select("clause_type, clause_value, is_current")
                .eq("lease_id", lease_id)
                .eq("is_current", True)
                .execute()
                .data
                or []
            )
        except Exception:
            history = []
        fact = build_term_facts(lease, fields, history_rows=history)
        fact["updated_at"] = datetime.utcnow().isoformat()
        existing = (
            supabase.table("lease_term_facts")
            .select("id")
            .eq("lease_id", lease_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            supabase.table("lease_term_facts").update(fact).eq("lease_id", lease_id).execute()
        else:
            supabase.table("lease_term_facts").insert(fact).execute()
        return fact
    except Exception as exc:
        if _is_missing_table(exc):
            return None
        print(f"⚠ lease_term_facts sync skipped: {exc}")
        return None


def try_sync_lease_term_facts(supabase, lease_id: str) -> Optional[dict]:
    try:
        return sync_lease_term_facts(supabase, lease_id)
    except Exception as exc:
        print(f"⚠ lease_term_facts sync failed: {exc}")
        return None


def export_anonymized_facts(supabase) -> List[dict]:
    """Rows from opted-in customers only, with identifiers removed."""
    try:
        rows = supabase.table("lease_term_facts_export").select("*").execute().data or []
        return [export_row(row) for row in rows]
    except Exception:
        pass
    try:
        facts = supabase.table("lease_term_facts").select("*").execute().data or []
        clients = {
            row["id"]: row
            for row in (supabase.table("clients").select("id, allow_anonymized_corpus").execute().data or [])
        }
        exported = []
        for fact in facts:
            client = clients.get(fact.get("client_id") or "") or {}
            if not client.get("allow_anonymized_corpus"):
                continue
            exported.append(export_row(fact))
        return exported
    except Exception as exc:
        if _is_missing_table(exc):
            return []
        print(f"⚠ lease_term_facts export skipped: {exc}")
        return []
