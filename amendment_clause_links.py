"""Link related lease clauses when an amendment changes one of them.

A Base Rent replacement is also a new rent schedule and a new escalation
rule. Customers billing rent or issuing an estoppel need the governing
file, not a standalone extraction of the amendment.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

# When the parent is amended, these siblings must follow.
CLAUSE_DEPENDENTS = {
    "Base Rent": ["Rent Schedule", "Rent Escalations"],
    "Rent Schedule": ["Rent Escalations"],
    "Expansion of Premises": ["Premises Description"],
    "Renewal Options": ["Renewal Notice Deadline"],
    "Renewal Notice Deadline": [],
}

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
    r"(\d{1,3}(?:,\d{3})+|\d+)\s+(?:rentable square feet|rsf|sq\.?\s*ft|square feet)",
    re.IGNORECASE,
)
WORD_MONTHS = {
    "nine": 9,
    "twelve": 12,
    "six": 6,
    "three": 3,
    "eighteen": 18,
    "fifteen": 15,
}


def parse_rsf(text: str) -> Optional[int]:
    match = RSF.search(text or "")
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_rate_periods(text: str) -> List[Dict[str, Any]]:
    rows = []
    for match in PERIOD_RATE.finditer(text or ""):
        rows.append(
            {
                "start": match.group("start"),
                "end": match.group("end"),
                "annual_rate": float(match.group("rate").replace(",", "")),
            }
        )
    return rows


def format_rent_schedule(periods: List[Dict[str, Any]], rsf: int) -> str:
    parts = []
    for index, period in enumerate(periods, start=1):
        monthly = round(rsf * period["annual_rate"] / 12.0, 2)
        parts.append(
            f"Year {index} ({period['start']}–{period['end']}): "
            f"${period['annual_rate']:,.2f}/RSF/year = ${monthly:,.2f}/month"
        )
    return "; ".join(parts)


def derive_rent_schedule(source_text: str) -> Optional[str]:
    periods = parse_rate_periods(source_text)
    if not periods:
        return None
    rsf = parse_rsf(source_text)
    if rsf:
        return format_rent_schedule(periods, rsf)
    return "; ".join(
        f"{period['start']}–{period['end']}: ${period['annual_rate']:,.2f}/RSF/year"
        for period in periods
    )


def derive_rent_escalations(source_text: str) -> Optional[str]:
    text = source_text or ""
    if re.search(
        r"no additional\s+3\s?%|replace,\s*not supplement,\s*any annual percentage|"
        r"fixed dollar rates and replace",
        text,
        re.IGNORECASE,
    ):
        return "None — fixed dollar rates replace any percentage escalation"
    if re.search(r"(?:approximately\s+)?(?:three percent|\b3\s?%)", text, re.IGNORECASE):
        return "3%"
    return None


def derive_premises_description(source_text: str) -> Optional[str]:
    rsf = parse_rsf(source_text)
    if not rsf:
        return None
    return f"{rsf:,} sq ft"


def derive_renewal_notice(source_text: str) -> Optional[str]:
    text = source_text or ""
    replaced = re.search(
        r"replaced with [“\"]not later than ([A-Za-z]+|\d+)\s*(?:\(\s*(\d+)\s*\))?\s*months",
        text,
        re.IGNORECASE,
    )
    match = replaced or re.search(
        r"not later than ([A-Za-z]+|\d+)\s*(?:\(\s*(\d+)\s*\))?\s*months",
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r"\b(\d+)\s+months before the Expiry Date", text, re.IGNORECASE)
        if match:
            return f"{int(match.group(1))} months before the Expiry Date"
        return None
    token = (match.group(2) or match.group(1) or "").strip().lower()
    if token.isdigit():
        months = int(token)
    else:
        months = WORD_MONTHS.get(token)
    if not months:
        return None
    return f"{months} months before the Expiry Date"


DERIVERS = {
    "Rent Schedule": derive_rent_schedule,
    "Rent Escalations": derive_rent_escalations,
    "Premises Description": derive_premises_description,
    "Renewal Notice Deadline": derive_renewal_notice,
}


def derive_dependent_value(clause_type: str, source_text: str) -> Optional[str]:
    deriver = DERIVERS.get(clause_type)
    if not deriver:
        return None
    return deriver(source_text)


def expand_related_modifications(
    modifications: Iterable[dict],
    existing_originals: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """Add dependent clause rows after GPT extracts a parent change."""
    rows = [dict(item) for item in (modifications or []) if item.get("clause_type")]
    existing_originals = existing_originals or {}
    present = {row["clause_type"] for row in rows}
    extras: List[dict] = []
    for parent in list(rows):
        source = parent.get("new_value") or parent.get("source_text") or ""
        for dependent in CLAUSE_DEPENDENTS.get(parent["clause_type"], []):
            if dependent in present:
                continue
            derived = derive_dependent_value(dependent, source)
            if not derived:
                continue
            extras.append(
                {
                    "clause_type": dependent,
                    "clause_section": parent.get("clause_section", ""),
                    "modification_type": "SUPERSEDES",
                    "original_value": existing_originals.get(dependent)
                    or parent.get("original_value")
                    or "",
                    "new_value": derived,
                    "source_text": (parent.get("source_text") or source)[:1000],
                    "confidence": parent.get("confidence", "MEDIUM"),
                    "effective_date": parent.get("effective_date"),
                    "notes": f"Updated because {parent['clause_type']} was amended.",
                    "linked_from": parent["clause_type"],
                }
            )
            present.add(dependent)
    return rows + extras


def _copy_parent_source(target: dict, parent: dict) -> None:
    target["governing_source"] = "AMENDMENT"
    target["governing_label"] = parent.get("governing_label") or "Amendment"
    target["governing_amendment_number"] = parent.get("governing_amendment_number")
    target["governing_amendment_date"] = parent.get("governing_amendment_date")
    target["governing_version"] = parent.get("governing_version")
    target["effective_from"] = parent.get("effective_from")
    target["modification_type"] = "SUPERSEDES"
    target["linked_from"] = parent.get("clause_type")


def apply_related_clause_updates(clauses: Iterable[dict]) -> List[dict]:
    """Move dependent Schedule B clauses onto the governing amendment."""
    updated = [dict(clause) for clause in (clauses or [])]
    by_type = {clause["clause_type"]: clause for clause in updated if clause.get("clause_type")}
    parents = [clause for clause in updated if clause.get("changed")]
    parents.sort(
        key=lambda clause: (
            clause.get("governing_amendment_number") or 0,
            clause.get("clause_type") or "",
        )
    )
    for parent in parents:
        source = parent.get("governing_value") or ""
        for dependent in CLAUSE_DEPENDENTS.get(parent.get("clause_type") or "", []):
            derived = derive_dependent_value(dependent, source)
            if not derived:
                continue
            existing = by_type.get(dependent)
            if existing and existing.get("changed"):
                continue
            if existing:
                original = existing.get("original_value") or existing.get("governing_value") or ""
                existing["original_value"] = original
                existing["governing_value"] = derived
                existing["changed"] = True
                _copy_parent_source(existing, parent)
            else:
                created = {
                    "clause_type": dependent,
                    "original_value": "Not stated - amendment updates a related clause",
                    "governing_value": derived,
                    "changed": True,
                    "original_source": "BASE_LEASE",
                    "versions": [],
                }
                _copy_parent_source(created, parent)
                updated.append(created)
                by_type[dependent] = created
    return updated
