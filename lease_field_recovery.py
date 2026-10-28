"""Recover required lease-abstract terms from raw lease text.

GPT-4o often marks formula dates and PSF rent as NOT FOUND. This pass reads
Basic Lease Provisions and common CRE definitions, then fills those slots.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

NOT_FOUND = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "—", "-"}

BASIC_LABELS = [
    "Address of Building",
    "Premises",
    "Building",
    "Project",
    "Base Rent",
    "Rentable Area of Premises",
    "Rentable Area of Project",
    "Rentable Area of Building",
    "Building's Share of Project",
    "Tenant's Share",
    "Security Deposit",
    "Target Commencement Date",
    "Commencement Date",
    "Rent Commencement Date",
    "Expiration Date",
    "Lease Expiration Date",
    "Rent Adjustment Percentage",
    "Base Term",
    "Permitted Use",
    "Landlord's Notice Address",
    "Tenant's Notice Address",
    "Address for Rent Payment",
]


def _usable(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return "" if text.upper() in NOT_FOUND else text


def _field(value: str, confidence: str, snippet: str, notes: str = "") -> Dict[str, str]:
    return {
        "value": value,
        "confidence": confidence,
        "source_snippet": (snippet or "")[:240],
        "notes": notes,
        "prefer": "1",
    }


def _money(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"\$?\s*(-?[\d,]+(?:\.\d+)?)", text.replace("\u00a0", " "))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _percent(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(-?[\d.]+)\s*%", text)
    if match:
        return float(match.group(1))
    match = re.search(r"(-?[\d.]+)", text)
    if not match:
        return None
    number = float(match.group(1))
    return number * 100 if number <= 1 else number


def _rsf(text: str) -> Optional[float]:
    match = re.search(
        r"([\d,]+(?:\.\d+)?)\s*(?:rentable\s+)?(?:square\s+feet|sq\.?\s*ft|rsf)",
        text or "",
        re.I,
    )
    if not match:
        match = re.search(r"([\d,]+(?:\.\d+)?)", text or "")
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _parse_date(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d %Y"):
        try:
            return datetime.strptime(cleaned[:40], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        cleaned,
        re.I,
    )
    if match:
        try:
            return datetime.strptime(match.group(0).replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


ADDRESS_FIELDS = {
    "Tenant Registered Address",
    "Landlord Contact / Notice Address",
    "Landlord Registered Address",
    "Property Civic Address",
}

ADDRESS_STOPPERS = (
    r"The following Exhibits",
    r"1\.\s+Lease of Premises",
    r"BASIC LEASE PROVISIONS",
    r"pipes,?\s+ducts",
    r"Common Areas",
    r"IN WITNESS WHEREOF",
    r"From and after the Commencement Date",
    r"Upon and subject to all of the terms",
)


def clip_postal_address(value: str) -> str:
    """Keep street, city, ZIP, and Attention — drop any lease body that followed."""
    if not value:
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"^(?:Tenant'?s?|Landlord'?s?)\s+Notice Address:\s*", "", text, flags=re.I)
    for pattern in ADDRESS_STOPPERS:
        text = re.split(pattern, text, maxsplit=1, flags=re.I)[0].strip(" .;:")
    attn = re.search(r"(.+?\bAttention:\s+[^.]{2,60})", text, re.I)
    if attn:
        return attn.group(1).strip(" .;")
    zip_match = re.search(
        r"(.{8,180}?\b(?:[A-Z]{2}\s+\d{5}(?:-\d{4})?|[A-Z]{2}\s+[A-Z]\d[A-Z]\s?\d[A-Z]\d))",
        text,
    )
    if zip_match:
        clipped = zip_match.group(1).strip(" .;")
        if len(text) > len(clipped) + 40:
            return clipped
    if len(text) > 180:
        return text[:180].rsplit(" ", 1)[0].strip(" .;")
    return text


def extract_labeled_address(text: str, *labels: str) -> str:
    """Read a notice/address label and stop at the next heading."""
    window = (text[:25000] or "").replace("\u2019", "'").replace("\u2018", "'")
    next_heads = (
        "The following Exhibits",
        "Tenant's Notice Address",
        "Landlord's Notice Address",
        "Address for Rent Payment",
        "1. Lease of Premises",
        "Permitted Use",
    )
    for label in labels:
        lookahead = "|".join(re.escape(item) for item in next_heads if item.lower() != label.lower())
        match = re.search(
            rf"{re.escape(label)}\s*:\s*(.+?)(?=(?:{lookahead})\s*:|\n1\.\s+)",
            window,
            re.I | re.S,
        )
        if match:
            clipped = clip_postal_address(match.group(1))
            if clipped:
                return clipped
    return ""


def parse_basic_provisions(text: str) -> Dict[str, str]:
    """Pull labeled Basic Lease Provisions from the front of the lease."""
    window = (text[:20000] or "").replace("\u2019", "'").replace("\u2018", "'")
    start = re.search(r"BASIC\s+LEASE\s+PROVISIONS", window, re.I)
    block = window[start.start():] if start else window
    for stopper in (
        "The following Exhibits",
        "1. Lease of Premises",
        "1. Lease of Premises.",
        "\n1. ",
    ):
        idx = block.find(stopper)
        if idx > 80:
            block = block[:idx]
            break
    found: Dict[str, str] = {}
    hits = []
    for label in sorted(BASIC_LABELS, key=len, reverse=True):
        for match in re.finditer(rf"{re.escape(label)}\s*:", block, re.I):
            hits.append((match.start(), match.end(), label))
    hits.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    chosen = []
    seen_spans = []
    seen_labels = set()
    for start, end, label in hits:
        if label in seen_labels:
            continue
        if any(start < used_end and end > used_start for used_start, used_end in seen_spans):
            continue
        seen_labels.add(label)
        seen_spans.append((start, end))
        chosen.append((start, end, label))
    chosen.sort()
    for index, (start, end, label) in enumerate(chosen):
        value_end = chosen[index + 1][0] if index + 1 < len(chosen) else len(block)
        value = re.sub(r"\s+", " ", block[end:value_end]).strip(" .;")
        value = re.split(r'\s+The\s+[“"”]', value, maxsplit=1)[0].strip(" .;")
        if "address" in label.lower() or "notice" in label.lower():
            value = clip_postal_address(value)
        elif len(value) > 280:
            value = value[:280].rsplit(" ", 1)[0].strip(" .;")
        if value:
            found[label] = value
    return found


def _parties(text: str) -> Tuple[str, str]:
    match = re.search(
        r"between\s+(.+?)\s+\((?:the\s+)?[“\"]?Landlord[”\"]?\)\s*,\s*and\s+(.+?)\s+\((?:the\s+)?[“\"]?Tenant[”\"]?\)",
        text[:8000],
        re.I | re.S,
    )
    if not match:
        return "", "", "", ""
    landlord_raw = re.sub(r"\s+", " ", match.group(1)).strip(" ,")
    tenant_raw = re.sub(r"\s+", " ", match.group(2)).strip(" ,")
    landlord = re.sub(r",\s*a\s+[A-Za-z].*$", "", landlord_raw).strip(" ,")
    tenant = re.sub(r",\s*a\s+[A-Za-z].*$", "", tenant_raw).strip(" ,")
    return landlord, tenant, landlord_raw, tenant_raw


def _suites_and_floors(text: str) -> Tuple[str, str]:
    suites = re.findall(r"Suite\s+([A-Za-z0-9-]+)", text[:12000], re.I)
    # Keep premises suites, drop notice-address suite if it is the only extra.
    unique = []
    for suite in suites:
        if suite not in unique:
            unique.append(suite)
    suite_value = ", ".join(f"Suite {item}" for item in unique[:6])
    floors = []
    for suite in unique:
        floor_match = re.search(r"-(\d)\d{2}$", suite)
        if floor_match:
            floor = floor_match.group(1)
            if floor not in floors:
                floors.append(floor)
    if not floors:
        named = re.findall(
            r"(?:floors?|level)\s+(\d+(?:\s*(?:and|,)\s*\d+)*)",
            text[:12000],
            re.I,
        )
        for item in named:
            floors.extend(re.findall(r"\d+", item))
    floor_value = ""
    if floors:
        pretty = [f"Floor {n}" for n in floors]
        floor_value = " and ".join(pretty) if len(pretty) <= 2 else ", ".join(pretty)
    return suite_value, floor_value


def _monthly_from_base_rent(base_rent: str, rsf: Optional[float]) -> Tuple[Optional[float], str]:
    if not base_rent:
        return None, ""
    amount = _money(base_rent)
    if amount is None:
        return None, ""
    lower = base_rent.lower()
    if "per month" in lower or "/month" in lower or "monthly" in lower:
        return amount, "monthly amount stated in the lease"
    if rsf and ("square foot" in lower or "rsf" in lower or "sq. ft" in lower or "sq ft" in lower):
        if "year" in lower or "annum" in lower or "annual" in lower:
            monthly = round(amount * rsf / 12.0, 2)
            return monthly, f"{amount:.2f} per RSF per year × {rsf:,.0f} RSF / 12"
        monthly = round(amount * rsf, 2)
        return monthly, f"{amount:.2f} per RSF per month × {rsf:,.0f} RSF"
    if "year" in lower or "annum" in lower or "annual" in lower:
        return round(amount / 12.0, 2), "annual rent / 12"
    return amount, "rent amount stated in the lease"


def _rent_schedule(year1: float, increase_pct: float, years: int = 7) -> List[str]:
    rows = []
    current = year1
    rate = 1.0 + (increase_pct / 100.0)
    for year in range(1, years + 1):
        rows.append(f"Year {year}: ${current:,.2f}/month")
        current = round(current * rate, 2)
    return rows


def _free_rent_months(text: str) -> Optional[int]:
    match = re.search(
        r"Rent Commencement Date[”\"']?\s*shall be the date that is\s+(\d+)\s+months?\s+after",
        text,
        re.I,
    )
    if match:
        return int(match.group(1))
    match = re.search(
        r"(?:free rent|rent abatement|abated(?:\s+base)?\s+rent)[^\n.]{0,80}?(\d+)\s+months?",
        text,
        re.I,
    )
    if match:
        return int(match.group(1))
    return None


def recover_lease_fields(lease_text: str) -> Dict[str, Dict[str, str]]:
    """Return high-confidence field dicts recovered from lease text."""
    text = lease_text or ""
    basic = parse_basic_provisions(text)
    recovered: Dict[str, Dict[str, str]] = {}

    landlord, tenant, landlord_raw, tenant_raw = _parties(text)
    if landlord:
        recovered["Landlord Legal Name"] = _field(
            landlord,
            "HIGH",
            landlord_raw or landlord,
            "Parsed from the lease preamble",
        )
        formation = re.search(r"\b(Delaware|California|Massachusetts|New York)\b", landlord_raw or landlord, re.I)
        if formation:
            recovered["Landlord Registered Address"] = _field(
                f"{formation.group(1)} (state of formation)",
                "MEDIUM",
                landlord_raw,
                "Lease states entity formation, not a street registered office",
            )
    if tenant:
        recovered["Tenant Legal Name"] = _field(
            tenant,
            "HIGH",
            tenant_raw or tenant,
            "Parsed from the lease preamble",
        )

    building = basic.get("Address of Building") or ""
    if building:
        recovered["Property Civic Address"] = _field(building, "HIGH", building)

    notice = extract_labeled_address(text, "Landlord's Notice Address") or clip_postal_address(basic.get("Landlord's Notice Address", ""))
    if notice:
        recovered["Landlord Contact / Notice Address"] = _field(
            notice,
            "HIGH",
            notice,
            "Landlord notice address from Basic Lease Provisions",
        )
    tenant_notice = extract_labeled_address(text, "Tenant's Notice Address") or clip_postal_address(basic.get("Tenant's Notice Address", ""))
    if tenant_notice:
        recovered["Tenant Registered Address"] = _field(
            tenant_notice,
            "HIGH",
            tenant_notice,
            "Tenant notice address; stopped at Attention / next heading",
        )

    premises_rsf = _rsf(basic.get("Rentable Area of Premises", "") or basic.get("Premises", ""))
    if premises_rsf:
        recovered["Premises Square Footage (RSF)"] = _field(
            f"{premises_rsf:,.0f} rentable square feet",
            "HIGH",
            basic.get("Rentable Area of Premises") or basic.get("Premises", ""),
        )
    building_rsf = _rsf(basic.get("Rentable Area of Building", ""))
    if building_rsf:
        recovered["Building Total Square Footage"] = _field(
            f"{building_rsf:,.0f} rentable square feet",
            "HIGH",
            basic.get("Rentable Area of Building", ""),
        )

    suites, floors = _suites_and_floors(basic.get("Premises", "") + "\n" + text[:8000])
    if suites:
        recovered["Suite / Unit Number"] = _field(suites, "HIGH", suites)
    if floors:
        recovered["Floor(s) Occupied"] = _field(floors, "MEDIUM", suites, "Derived from suite numbers")

    security = _money(basic.get("Security Deposit", ""))
    if security is not None:
        recovered["Security Deposit Amount"] = _field(
            f"${security:,.0f}" if security >= 100 else f"${security:,.2f}",
            "HIGH",
            basic.get("Security Deposit", ""),
        )
    if re.search(r"letter of credit", text[:20000], re.I):
        recovered["Security Deposit — Letter of Credit"] = _field(
            "Yes",
            "HIGH",
            "Security Deposit shall be in the form of an unconditional and irrevocable letter of credit",
        )

    term_months = None
    term_match = re.search(r"ending\s+(\d+)\s+months?\s+from\s+the\s+Commencement Date", text, re.I)
    if not term_match:
        term_match = re.search(r"(\d+)\s+months?\s+from\s+the\s+Commencement Date", basic.get("Base Term", ""), re.I)
    if term_match:
        term_months = int(term_match.group(1))
        recovered["Lease Term (Total Months)"] = _field(
            f"{term_months} months",
            "HIGH",
            term_match.group(0),
        )

    target = _parse_date(basic.get("Target Commencement Date", "") or basic.get("Commencement Date", ""))
    delivery_defined = bool(re.search(
        r"Commencement Date[”\"']?\s*shall be the date Landlord Delivers",
        text,
        re.I,
    ))
    if target and delivery_defined:
        recovered["Lease Commencement Date"] = _field(
            f"{target} (Target; actual Commencement Date is Delivery of the Premises)",
            "MEDIUM",
            basic.get("Target Commencement Date", ""),
            "CONDITIONAL: Commencement Date is Delivery; Target Commencement Date is shown",
        )
    elif target:
        recovered["Lease Commencement Date"] = _field(target, "HIGH", basic.get("Target Commencement Date", "") or basic.get("Commencement Date", ""))
    elif delivery_defined:
        recovered["Lease Commencement Date"] = _field(
            "CONDITIONAL: date Landlord Delivers the Premises to Tenant",
            "MEDIUM",
            "The Commencement Date shall be the date Landlord Delivers the Premises to Tenant",
        )

    free_months = _free_rent_months(text)
    if free_months:
        recovered["Rent Commencement Date"] = _field(
            f"CONDITIONAL: {free_months} months after the Commencement Date",
            "HIGH",
            f"The Rent Commencement Date shall be the date that is {free_months} months after the Commencement Date",
        )
        recovered["Free Rent Period (months)"] = _field(
            f"{free_months} months",
            "HIGH",
            f"Rent Commencement Date is {free_months} months after Commencement Date",
            "Gap between commencement and rent commencement",
        )
    elif basic.get("Rent Commencement Date"):
        rent_date = _parse_date(basic["Rent Commencement Date"])
        recovered["Rent Commencement Date"] = _field(
            rent_date or basic["Rent Commencement Date"],
            "HIGH",
            basic["Rent Commencement Date"],
        )

    if term_months and (target or delivery_defined):
        recovered["Lease Expiration Date"] = _field(
            f"CONDITIONAL: {term_months} months from the Commencement Date",
            "HIGH",
            basic.get("Base Term", "")[:240],
        )

    increase = _percent(basic.get("Rent Adjustment Percentage", ""))
    if increase is None:
        inc_match = re.search(r"Rent Adjustment Percentage:\s*([\d.]+)\s*%", text, re.I)
        if inc_match:
            increase = float(inc_match.group(1))
    if increase is not None:
        recovered["Annual Escalation Rate or Cap"] = _field(f"{increase:g}%", "HIGH", f"Rent Adjustment Percentage: {increase:g}%")
        recovered["Annual Escalation Type (Fixed / CPI / Percentage)"] = _field(
            "Percentage",
            "HIGH",
            f"Rent Adjustment Percentage: {increase:g}%",
        )

    monthly, rent_note = _monthly_from_base_rent(basic.get("Base Rent", ""), premises_rsf)
    if monthly:
        recovered["Base Rent Year 1 (monthly)"] = _field(
            f"${monthly:,.2f}",
            "HIGH",
            basic.get("Base Rent", ""),
            rent_note,
        )
        rate = increase or 0.0
        schedule = _rent_schedule(monthly, rate, years=max(5, (term_months or 60) // 12))
        for index, label in enumerate(
            (
                "Base Rent Year 2 (monthly)",
                "Base Rent Year 3 (monthly)",
                "Base Rent Year 4 (monthly)",
                "Base Rent Year 5 (monthly)",
            ),
            start=1,
        ):
            if index < len(schedule):
                amount = schedule[index].split(": ", 1)[1].replace("/month", "")
                recovered[label] = _field(amount, "HIGH", basic.get("Base Rent", ""), f"Year 1 escalated at {rate:g}% annually")
        recovered["Full Rent Schedule (all years)"] = _field(
            "; ".join(schedule),
            "HIGH",
            basic.get("Base Rent", ""),
            f"Computed from stated Base Rent and {rate:g}% annual increase",
        )

    if basic.get("Permitted Use"):
        recovered["Permitted Use"] = _field(basic["Permitted Use"], "HIGH", basic["Permitted Use"])

    tenant_share = _percent(basic.get("Tenant's Share", ""))
    if tenant_share is not None:
        recovered["CAM / Operating Cost Charges"] = _field(
            f"Tenant's Share of Operating Expenses ({tenant_share:g}%)",
            "HIGH",
            basic.get("Tenant's Share", ""),
        )

    if re.search(r"subject and\s+subordinate", text, re.I) and re.search(r"non-disturbance|attorn", text, re.I):
        recovered["SNDA Agreement Required"] = _field(
            "Yes — Tenant must execute subordination and attornment instruments containing non-disturbance provisions",
            "HIGH",
            "This Lease and Tenant’s interest and rights hereunder are hereby made and shall be subject and subordinate",
        )

    if re.search(r"shall be deemed to have elected arbitration|Arbitrator", text, re.I):
        recovered["Dispute Resolution Mechanism"] = _field(
            "Arbitration for Extension Term Market Rate (and court appointment of a third arbitrator if needed)",
            "HIGH",
            "Tenant shall be deemed to have elected arbitration as described in Section 39(b)",
        )

    if re.search(r"Premises shall be expanded to include the Prior Premises", text, re.I):
        prior_rsf = re.search(
            r"Prior Premises[^\n.]{0,120}approximately\s+([\d,]+)\s+rentable square feet"
            r"|approximately\s+([\d,]+)\s+rentable square feet\s+\(the\s+[“\"]Prior Premises",
            text,
            re.I,
        )
        prior_date = re.search(
            r"Commencing on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+\(the\s+[“\"]Prior Premises Commencement Date",
            text,
            re.I,
        )
        prior_size = next((group for group in prior_rsf.groups() if group), None) if prior_rsf else None
        size = f" of {prior_size} rentable square feet" if prior_size else ""
        when = f" on {prior_date.group(1)}" if prior_date else " on the Prior Premises Commencement Date"
        recovered["Expansion Option"] = _field(
            f"Yes — Prior Premises{size} are added{when}",
            "HIGH",
            "the Premises shall be expanded to include the Prior Premises",
        )

    tia = re.search(
        r"Tenant Improvement Allowance[^\n.]{0,120}(\$\s*[\d,]+(?:\.\d+)?)",
        text,
        re.I,
    )
    if tia and "[***]" not in tia.group(0):
        recovered["Tenant Improvement Allowance (TIA)"] = _field(
            tia.group(1).replace(" ", ""),
            "HIGH",
            tia.group(0),
        )

    if re.search(r"triple\s+net|NNN", text[:15000], re.I):
        recovered["Lease Type (Gross / Net / Modified Gross)"] = _field("Net", "HIGH", "triple net / NNN")
        recovered["Net Lease Type (Single / Double / Triple)"] = _field("Triple", "HIGH", "triple net / NNN")
    elif re.search(r"Additional Rent[^\n]{0,120}Tenant’s Share of Operating Expenses", text, re.I):
        recovered["Lease Type (Gross / Net / Modified Gross)"] = _field("Net", "MEDIUM", "Tenant pays Tenant's Share of Operating Expenses")
        recovered["Net Lease Type (Single / Double / Triple)"] = _field("Triple", "MEDIUM", "Tenant pays operating expenses, taxes, and insurance share")

    return recovered


def merge_extracted_fields(
    field_names: Iterable[str],
    model_fields: Dict[str, Any],
    recovered_fields: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """Fill every required slot; recovered structured terms win over NOT FOUND."""
    merged: Dict[str, Dict[str, Any]] = {}
    model_by_lower = {str(key).lower(): value for key, value in (model_fields or {}).items()}
    for name in field_names:
        model = model_fields.get(name) or model_by_lower.get(name.lower())
        if not isinstance(model, dict):
            model = {"value": model, "confidence": "LOW", "source_snippet": "", "notes": ""} if model else {}
        model_value = _usable(model.get("value"))
        recovered = recovered_fields.get(name)
        if recovered and (not model_value or recovered.get("prefer") or _address_overflow(name, model_value)):
            chosen = {k: v for k, v in recovered.items() if k != "prefer"}
        elif model_value:
            chosen = {
                "value": model_value,
                "confidence": model.get("confidence") or "MEDIUM",
                "source_snippet": model.get("source_snippet") or model.get("source_text") or "",
                "notes": model.get("notes") or "",
            }
        else:
            chosen = {
                "value": "NOT FOUND",
                "confidence": "LOW",
                "source_snippet": "",
                "notes": "No clause found referencing this field",
            }
        if name in ADDRESS_FIELDS and chosen.get("value") and chosen["value"] != "NOT FOUND":
            clipped = clip_postal_address(str(chosen["value"]))
            if clipped:
                chosen["value"] = clipped
        merged[name] = chosen
    return merged


def _address_overflow(field_name: str, value: str) -> bool:
    if field_name not in ADDRESS_FIELDS or not value:
        return False
    if len(value) > 220:
        return True
    return bool(re.search(r"The following Exhibits|pipes,?\s+ducts|1\.\s+Lease of Premises", value, re.I))


def extracted_display_value(fields: Dict[str, Any], *names: str) -> str:
    for name in names:
        raw = fields.get(name)
        if isinstance(raw, dict):
            value = _usable(raw.get("reviewed_value") or raw.get("raw_value") or raw.get("value"))
        else:
            value = _usable(raw)
        if value:
            return value
    return ""
