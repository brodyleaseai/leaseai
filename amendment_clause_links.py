"""Link related lease clauses when an amendment changes one of them.

A Base Rent replacement is also a new rent schedule and a new escalation
rule. Customers billing rent or issuing an estoppel need the governing
file, not a standalone extraction of the amendment.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

# When the parent is amended, these siblings must follow.
CLAUSE_DEPENDENTS = {
    "Base Rent": ["Rent Schedule", "Rent Escalations"],
    "Rent Schedule": ["Rent Escalations"],
    "Expansion of Premises": ["Premises Description", "Rent Schedule"],
    "Premises Description": ["Rent Schedule"],
    "Renewal Options": ["Renewal Notice Deadline"],
    "Renewal Notice Deadline": [],
}

SKIP_CLAUSE_TYPES = {
    "Execution",
    "Signature",
    "Signatures",
    "Signature Block",
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
PERIOD_RATE_LOOSE = re.compile(
    rf"(?:from\s+)?(?P<start>{DATE})\s+(?:to|through|[–\-])\s+(?P<end>{DATE})\s+"
    rf"(?:remains|:)\s+\$?(?P<rate>\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)",
    re.IGNORECASE,
)
RSF = re.compile(
    r"(\d{1,3}(?:,\d{3})+|\d+)\s+(?:rentable square feet|rsf|sq\.?\s*ft|square feet)",
    re.IGNORECASE,
)
REMAINING_RSF = re.compile(
    r"(?:comprise[s]?|comprising|multiplied by|total(?:ling)?|"
    r"premises (?:shall be|are|is))\s+(?:approximately\s+)?"
    r"(\d{1,3}(?:,\d{3})+|\d+)\s+(?:rentable square feet|rsf|sq\.?\s*ft|square feet)",
    re.IGNORECASE,
)
SURRENDER_RSF = re.compile(
    r"(?:surrender|return of|surrendered area)\b.{0,120}?"
    r"(\d{1,3}(?:,\d{3})+|\d+)\s+(?:rentable square feet|rsf|sq\.?\s*ft|square feet)",
    re.IGNORECASE | re.DOTALL,
)
WORD_MONTHS = {
    "nine": 9,
    "twelve": 12,
    "six": 6,
    "three": 3,
    "eighteen": 18,
    "fifteen": 15,
}


def _as_rsf(value: str) -> Optional[int]:
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return None


def parse_rsf(text: str) -> Optional[int]:
    """Return the remaining / billed premises RSF, not a surrendered slice."""
    remaining = [
        _as_rsf(match.group(1))
        for match in REMAINING_RSF.finditer(text or "")
    ]
    remaining = [value for value in remaining if value]
    if remaining:
        return remaining[-1]
    surrendered = {
        _as_rsf(match.group(1))
        for match in SURRENDER_RSF.finditer(text or "")
    }
    surrendered.discard(None)
    found = [_as_rsf(match.group(1)) for match in RSF.finditer(text or "")]
    found = [value for value in found if value]
    kept = [value for value in found if value not in surrendered]
    if kept:
        return kept[-1]
    return max(found) if found else None


def parse_rate_periods(text: str) -> List[Dict[str, Any]]:
    rows = []
    seen = set()
    for pattern in (PERIOD_RATE, PERIOD_RATE_LOOSE):
        for match in pattern.finditer(text or ""):
            key = (match.group("start"), match.group("end"), match.group("rate"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "start": match.group("start"),
                    "end": match.group("end"),
                    "annual_rate": float(match.group("rate").replace(",", "")),
                }
            )
    return rows


def parse_dollar_rates(text: str) -> List[float]:
    rates = []
    for match in re.finditer(r"\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)", text or ""):
        value = float(match.group(1).replace(",", ""))
        if 1 <= value <= 200:
            rates.append(value)
    return rates


def _parse_named_date(value: str) -> Optional[datetime]:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    try:
        return datetime.strptime(cleaned, "%B %d, %Y")
    except ValueError:
        return None


def _format_named_date(value: datetime) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def filter_periods_from(periods: List[Dict[str, Any]], effective_from: str) -> List[Dict[str, Any]]:
    if not effective_from or not periods:
        return list(periods)
    try:
        start = datetime.strptime(str(effective_from)[:10], "%Y-%m-%d")
    except ValueError:
        return list(periods)
    kept = []
    for period in periods:
        end = _parse_named_date(period["end"])
        begin = _parse_named_date(period["start"])
        if not end or end < start:
            continue
        row = dict(period)
        if begin and begin < start:
            row["start"] = _format_named_date(start)
        kept.append(row)
    return kept or list(periods)


def implied_schedule_rsf(schedule_text: str) -> Optional[int]:
    match = re.search(
        r"\$([0-9]+(?:\.[0-9]+)?)/RSF/year = \$([0-9,]+(?:\.[0-9]+)?)/month",
        schedule_text or "",
        re.IGNORECASE,
    )
    if not match:
        return None
    rate = float(match.group(1))
    monthly = float(match.group(2).replace(",", ""))
    if not rate:
        return None
    return int(round(monthly * 12.0 / rate))


def score_rate_table(periods: List[Dict[str, Any]], hint_rates: Iterable[float]) -> int:
    if not periods:
        return -1
    rates = {round(period["annual_rate"], 2) for period in periods}
    hints = {round(rate, 2) for rate in hint_rates}
    score = len(periods) * 10
    overlap = rates & hints
    if overlap:
        score += 100 * len(overlap)
    elif hints:
        score -= 40
    return score


def format_rent_schedule(periods: List[Dict[str, Any]], rsf: int) -> str:
    parts = []
    for index, period in enumerate(periods, start=1):
        monthly = round(rsf * period["annual_rate"] / 12.0, 2)
        parts.append(
            f"Year {index} ({period['start']}–{period['end']}): "
            f"${period['annual_rate']:,.2f}/RSF/year = ${monthly:,.2f}/month"
        )
    return "; ".join(parts)


def derive_rent_schedule(
    source_text: str,
    context_texts: Optional[Iterable[str]] = None,
    rsf: Optional[int] = None,
    effective_from: Optional[str] = None,
) -> Optional[str]:
    texts = [source_text or ""] + [text for text in (context_texts or []) if text]
    hint_rates = []
    for text in texts:
        hint_rates.extend(parse_dollar_rates(text))
    best_periods: List[Dict[str, Any]] = []
    best_score = -1
    for text in texts:
        periods = parse_rate_periods(text)
        score = score_rate_table(periods, hint_rates)
        if score > best_score:
            best_score = score
            best_periods = periods
    if not best_periods:
        return None
    latest_rsf = rsf or next((parse_rsf(text) for text in texts if parse_rsf(text)), None)
    if effective_from:
        best_periods = filter_periods_from(best_periods, effective_from)
    if latest_rsf:
        schedule = format_rent_schedule(best_periods, latest_rsf)
        if effective_from:
            try:
                start = datetime.strptime(str(effective_from)[:10], "%Y-%m-%d")
                prefix = f"From {_format_named_date(start)} on {latest_rsf:,} RSF: "
                return prefix + schedule
            except ValueError:
                return schedule
        return schedule
    return "; ".join(
        f"{period['start']}–{period['end']}: ${period['annual_rate']:,.2f}/RSF/year"
        for period in best_periods
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
        remains = re.search(
            r"(?:remains|notice period(?: remains)?)\s+([A-Za-z]+|\d+)\s*(?:\(\s*(\d+)\s*\))?\s*months",
            text,
            re.IGNORECASE,
        )
        if remains:
            token = (remains.group(2) or remains.group(1) or "").strip().lower()
            months = int(token) if token.isdigit() else WORD_MONTHS.get(token)
            if months:
                return f"{months} months before the Expiry Date"
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


def is_execution_clause(clause_type: str = "", text: str = "") -> bool:
    name = clause_type or ""
    if any(name.lower() == skipped.lower() for skipped in SKIP_CLAUSE_TYPES):
        return True
    if re.search(r"\bexecution\b|\bsignature(?:s| block)?\b", name, re.IGNORECASE):
        return True
    return bool(re.search(r"^executed as of the date first written", text or "", re.IGNORECASE))


def extract_order_of_precedence(amendment_text: str) -> Optional[str]:
    match = re.search(
        r"(?:^|\n)\s*(?:\d+\.\s*)?(?:ORDER OF PRECEDENCE|PRIORITY AND CONTINUING EFFECT)\b[^\n]*\n"
        r"(?P<body>.+?)(?=\n\s*(?:\d+\.\s*)?(?:EXECUTION|EXECUTED)\b|\Z)",
        amendment_text or "",
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    body = re.sub(r"\s+", " ", match.group("body")).strip()
    return body or None


def extract_structural_clauses(
    amendment_text: str,
    effective_date: Optional[str] = None,
) -> List[dict]:
    """Pull boilerplate commercial terms GPT often drops; never include signatures."""
    extras = []
    precedence = extract_order_of_precedence(amendment_text)
    if precedence:
        extras.append(
            {
                "clause_type": "Order of Precedence",
                "clause_section": "Order of Precedence",
                "modification_type": "CONFIRMS",
                "original_value": "Not stated - amendment only provides new value",
                "new_value": precedence,
                "source_text": precedence[:1000],
                "confidence": "HIGH",
                "effective_date": effective_date,
            }
        )
    return extras


def _context_texts(
    rows: Iterable[dict],
    existing_originals: Optional[Dict[str, str]] = None,
    history_texts: Optional[Dict[str, List[str]]] = None,
) -> List[str]:
    texts: List[str] = []
    for row in rows:
        texts.append(row.get("new_value") or "")
        texts.append(row.get("source_text") or "")
        texts.append(row.get("governing_value") or "")
        texts.append(row.get("original_value") or "")
        for version in row.get("versions") or []:
            if isinstance(version, dict):
                texts.append(version.get("clause_value") or "")
    for value in (existing_originals or {}).values():
        texts.append(value or "")
    for values in (history_texts or {}).values():
        texts.extend(values or [])
    return [text for text in texts if text]


def expand_related_modifications(
    modifications: Iterable[dict],
    existing_originals: Optional[Dict[str, str]] = None,
    history_texts: Optional[Dict[str, List[str]]] = None,
) -> List[dict]:
    """Add dependent clause rows after GPT extracts a parent change."""
    rows = [
        dict(item)
        for item in (modifications or [])
        if item.get("clause_type") and not is_execution_clause(item.get("clause_type"), item.get("new_value") or "")
    ]
    existing_originals = existing_originals or {}
    present = {row["clause_type"] for row in rows}
    extras: List[dict] = []
    context = _context_texts(rows, existing_originals, history_texts)
    for parent in list(rows):
        source = parent.get("new_value") or parent.get("source_text") or ""
        for dependent in CLAUSE_DEPENDENTS.get(parent["clause_type"], []):
            if dependent in present:
                continue
            if dependent == "Rent Schedule":
                derived = derive_rent_schedule(
                    source,
                    context_texts=context,
                    rsf=parse_rsf(source),
                    effective_from=parent.get("effective_date"),
                )
            else:
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
            context.append(derived)
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
    target["derived_from"] = parent.get("clause_type")
    parent_excerpt = (
        parent.get("source_text")
        or parent.get("governing_source_text")
        or parent.get("governing_value")
        or ""
    )
    target["source_text"] = parent_excerpt
    target["governing_source_text"] = parent_excerpt
    target["governing_source_page"] = parent.get("governing_source_page") or parent.get("source_page")


def _latest_rsf_parent(clauses: List[dict]) -> Tuple[Optional[int], Optional[dict]]:
    candidates = []
    for clause in clauses:
        if clause.get("clause_type") not in {
            "Premises Description",
            "Base Rent",
            "Expansion of Premises",
        }:
            continue
        rsf = parse_rsf(clause.get("governing_value") or "")
        if rsf:
            candidates.append((clause.get("governing_amendment_number") or 0, rsf, clause))
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: (item[0], item[1]))
    _, rsf, parent = candidates[-1]
    return rsf, parent


def _apply_dependent(by_type: Dict[str, dict], updated: List[dict], parent: dict, dependent: str, derived: str) -> None:
    existing = by_type.get(dependent)
    parent_number = parent.get("governing_amendment_number") or 0
    if existing and existing.get("changed"):
        existing_number = existing.get("governing_amendment_number") or 0
        if parent_number < existing_number:
            return
        if (
            dependent == "Rent Schedule"
            and implied_schedule_rsf(existing.get("governing_value") or "")
            == implied_schedule_rsf(derived)
            and parent_number == existing_number
        ):
            return
    if existing:
        if not existing.get("changed"):
            existing["original_value"] = existing.get("original_value") or existing.get("governing_value") or ""
        existing["governing_value"] = derived
        existing["changed"] = True
        _copy_parent_source(existing, parent)
        return
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
            if dependent == "Rent Schedule":
                continue
            derived = derive_dependent_value(dependent, source)
            if derived:
                _apply_dependent(by_type, updated, parent, dependent, derived)

    latest_rsf, rsf_parent = _latest_rsf_parent(updated)
    base_rent = by_type.get("Base Rent") or {}
    expansion_only = bool(
        re.search(
            r"attributable to the Expansion Space|Expansion Space is charged|"
            r"Base Rent attributable to the Expansion",
            base_rent.get("governing_value") or "",
            re.IGNORECASE,
        )
    )
    base_hints = parse_dollar_rates(
        " ".join(_context_texts([base_rent] if base_rent else []))
    )
    if (
        latest_rsf
        and rsf_parent
        and (base_rent.get("changed") or base_hints)
        and not expansion_only
    ):
        context = _context_texts(updated)
        schedule = derive_rent_schedule(
            rsf_parent.get("governing_value") or "",
            context_texts=context,
            rsf=latest_rsf,
            effective_from=rsf_parent.get("effective_from"),
        )
        current = by_type.get("Rent Schedule")
        current_rsf = implied_schedule_rsf(current.get("governing_value") or "") if current else None
        if schedule and current_rsf != latest_rsf:
            _apply_dependent(by_type, updated, rsf_parent, "Rent Schedule", schedule)
        escalations = by_type.get("Rent Escalations")
        if escalations and not escalations.get("changed"):
            for text in context:
                derived = derive_rent_escalations(text)
                if derived and "fixed dollar" in derived:
                    _apply_dependent(by_type, updated, rsf_parent, "Rent Escalations", derived)
                    break
    return updated
