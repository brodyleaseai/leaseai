"""Source citations for client reports.

Enterprise abstracts need more than a number. Each extracted or governing
value should say which document it came from, the page if known, and the
excerpt the model used.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, Iterable, List, Optional

PAGE_MARK = re.compile(
    r"(?:---\s*)?(?:page|p\.?)\s*(\d{1,4})\b",
    re.IGNORECASE,
)

NOT_FOUND = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "—", "-"}


def _clean(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return "" if text.upper() in NOT_FOUND else text


def _first(*values: Any) -> str:
    for value in values:
        text = _clean(value)
        if text:
            return text
    return ""


def detect_page(text: str, explicit: Any = None) -> Optional[str]:
    if explicit not in (None, ""):
        digits = re.search(r"\d+", str(explicit))
        if digits:
            return digits.group(0)
    match = PAGE_MARK.search(text or "")
    return match.group(1) if match else None


def document_label(
    source_type: Any = None,
    amendment_number: Any = None,
    amendment_date: Any = None,
    fallback: str = "Original lease",
) -> str:
    kind = str(source_type or "").upper()
    if kind in {"AMENDMENT", "AMD"} or amendment_number not in (None, ""):
        if amendment_date:
            return f"Amendment No. {amendment_number} ({amendment_date})"
        if amendment_number not in (None, ""):
            return f"Amendment No. {amendment_number}"
        return "Amendment"
    if kind in {"BASE_LEASE", "ORIGINAL", "LEASE", ""}:
        return fallback
    return str(source_type).replace("_", " ").title() or fallback


def field_source(field: Any, default_document: str = "Original lease") -> Dict[str, str]:
    """Normalize GPT output, DB rows, or plain strings into a citation."""
    if not isinstance(field, dict):
        value = _clean(field)
        return {
            "value": value or "NOT FOUND",
            "document": default_document,
            "page": "",
            "excerpt": "",
            "derived_from": "",
            "notes": "",
            "found": bool(value),
        }
    value = _first(
        field.get("value"),
        field.get("reviewed_value"),
        field.get("raw_value"),
        field.get("governing_value"),
    )
    excerpt = _first(
        field.get("source_snippet"),
        field.get("source_text"),
        field.get("excerpt"),
        field.get("clause_value"),
    )
    document = _first(
        field.get("document"),
        field.get("governing_label"),
        document_label(
            field.get("source_document_type") or field.get("governing_source"),
            field.get("governing_amendment_number") or field.get("amendment_number"),
            field.get("governing_amendment_date") or field.get("amendment_date"),
            fallback=default_document,
        ),
        default_document,
    )
    derived = _first(field.get("derived_from"), field.get("linked_from"))
    notes = _first(field.get("notes"), field.get("derivation"))
    page = detect_page(
        " ".join(part for part in (excerpt, notes, str(field.get("source_page") or "")) if part),
        field.get("source_page") or field.get("page"),
    )
    return {
        "value": value or "NOT FOUND",
        "document": document or default_document,
        "page": page or "",
        "excerpt": excerpt,
        "derived_from": derived,
        "notes": notes,
        "found": bool(value),
    }


def format_source_line(source: Dict[str, str], limit: int = 220) -> str:
    """One-line cite: document, page, excerpt."""
    if not source.get("found"):
        return "No source — value not found in the document"
    parts = [source.get("document") or "Source document"]
    if source.get("page"):
        parts.append(f"p. {source['page']}")
    if source.get("derived_from"):
        parts.append(f"derived from {source['derived_from']}")
    line = ", ".join(parts)
    excerpt = source.get("excerpt") or ""
    if excerpt and excerpt != source.get("value"):
        clipped = excerpt if len(excerpt) <= limit else excerpt[: limit - 1] + "…"
        line = f"{line} — “{clipped}”"
    elif excerpt:
        line = f"{line} — source text retained"
    else:
        line = f"{line} — source excerpt was not stored"
    return line


def format_source_html(source: Dict[str, str], limit: int = 220) -> str:
    return html.escape(format_source_line(source, limit=limit))


def with_page_prefix(excerpt: str, page: Any = None) -> str:
    """Keep the page number in source_text when the table has no page column."""
    text = excerpt or ""
    found = detect_page(text, page)
    if found and not detect_page(text):
        return f"Page {found}. {text}"
    return text


def clause_source(clause: Optional[dict], side: str = "governing") -> Dict[str, str]:
    """Citation for an Amendment Resolution clause."""
    row = clause or {}
    if side == "original":
        return field_source(
            {
                "value": row.get("original_value"),
                "source_text": row.get("original_source_text") or row.get("original_value"),
                "document": "Original lease",
                "source_page": row.get("original_source_page"),
            },
            default_document="Original lease",
        )
    document = row.get("governing_label") or document_label(
        row.get("governing_source"),
        row.get("governing_amendment_number"),
        row.get("governing_amendment_date"),
    )
    return field_source(
        {
            "value": row.get("governing_value"),
            "source_text": (
                row.get("governing_source_text")
                or row.get("source_text")
                or row.get("governing_value")
            ),
            "document": document,
            "source_page": row.get("governing_source_page"),
            "derived_from": row.get("linked_from") or row.get("derived_from"),
            "notes": row.get("notes"),
        },
        default_document=document or "Source document",
    )


def fields_from_review_rows(
    rows: Optional[Iterable[dict]],
    default_document: str = "Original lease",
) -> Dict[str, Dict[str, Any]]:
    """Map extracted_fields table rows onto the abstract payload, keeping source text."""
    mapped: Dict[str, Dict[str, Any]] = {}
    for row in rows or []:
        name = row.get("field_name")
        if not name:
            continue
        mapped[name] = {
            "value": _first(row.get("reviewed_value"), row.get("raw_value")) or "NOT FOUND",
            "confidence": row.get("confidence") or row.get("confidence_score"),
            "source_text": row.get("source_text") or "",
            "source_page": row.get("source_page") or row.get("page"),
            "notes": row.get("notes") or "",
            "document": default_document,
        }
    return mapped


def source_exhibit_rows(
    extracted_fields: Optional[Dict[str, Any]],
    default_document: str = "Original lease",
) -> List[Dict[str, str]]:
    rows = []
    for name, field in (extracted_fields or {}).items():
        source = field_source(field, default_document=default_document)
        rows.append(
            {
                "field_name": str(name),
                "value": source["value"],
                "document": source["document"],
                "page": source["page"] or "—",
                "excerpt": source["excerpt"] or ("—" if not source["found"] else "Source excerpt was not stored"),
                "derived_from": source["derived_from"],
                "citation": format_source_line(source),
            }
        )
    return rows
