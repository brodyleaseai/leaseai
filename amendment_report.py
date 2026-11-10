"""Client-facing Amendment Resolution Abstract.

The Amendment Resolution Graph answers one file question a normal abstract
does not: what language controls as of a stated date, after every amendment
has been applied, and what original language it replaced.

This module tracks that value and prints it as the client work product —
the exhibit they attach to estoppels, lender packages, billing files, and
audit workpapers.
"""

from __future__ import annotations

import html
import io
import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import config
from amendment_clause_links import (
    apply_related_clause_updates,
    extract_structural_clauses,
    parse_dollar_rates,
    parse_rsf,
)
from lease_report import _header_footer
from report_sources import clause_source, format_source_html

VALUE_STATEMENT = (
    "This Amendment Resolution Abstract states the controlling lease language "
    "as of a given date after every amendment in the chain has been applied, "
    "and records the original language each governing clause replaced."
)

CLIENT_USES = (
    "Estoppel, lender, and buyer packages; rent and recoveries billing; "
    "dispute and audit workpapers."
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pdf_text(value: Any, limit: int = 1600) -> str:
    text = html.escape(_clean(value) or "N/A")
    if len(text) > limit:
        text = text[:limit] + "…"
    return text.replace("\n", "<br/>")


_AMOUNT = re.compile(
    r"\$\s?[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?\s?%|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\b\d+(?:\.\d+)?\b"
)
_MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
_NAMED_DATE = re.compile(rf"(?:{_MONTH_NAMES})\s+\d{{1,2}},\s+\d{{4}}", re.IGNORECASE)
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_AREA_HINT = re.compile(r"sq\.?\s*ft|square feet|\brsf\b|premises|comprise", re.IGNORECASE)
_TOTAL_MONEY = re.compile(
    r"(?:total(?:ling)?(?:\s+\w+){0,4}|shall then be|then be)\b[^$]{0,80}"
    r"\$([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_EXPANSION_RENT = re.compile(
    r"attributable to the Expansion Space|Expansion Space is charged|"
    r"Base Rent attributable to the Expansion",
    re.IGNORECASE,
)
_ADDITIONAL_RSF = re.compile(
    r"additional (\d{1,3}(?:,\d{3})+|\d+)\s+"
    r"(?:rentable square feet|rsf|sq\.?\s*ft|square feet)",
    re.IGNORECASE,
)
_ADDITIONAL_MONEY = re.compile(
    r"additional\b.{0,40}$",
    re.IGNORECASE | re.DOTALL,
)


def _strip_dates(text: str) -> str:
    stripped = _NAMED_DATE.sub(" ", text or "")
    return _ISO_DATE.sub(" ", stripped)


def _looks_like_area(text: str) -> bool:
    return bool(_AREA_HINT.search(text or "")) or bool(parse_rsf(text or ""))


def _money_value(token: str) -> Optional[float]:
    try:
        return float(re.sub(r"[^\d.]", "", token or ""))
    except ValueError:
        return None


def summarize_clause_change(original: str, governing: str) -> str:
    """Pull the short before → after a reader can scan (5% → 3.5%)."""
    original = original or ""
    governing = governing or ""

    old_rsf = parse_rsf(original)
    new_rsf = parse_rsf(governing)
    if old_rsf and new_rsf and old_rsf != new_rsf and _looks_like_area(original):
        return f"{old_rsf:,} → {new_rsf:,}"

    total_match = _TOTAL_MONEY.search(governing)
    old_money = re.search(r"\$\s?([\d,]+(?:\.\d+)?)", original)
    if total_match and old_money:
        old_val = _money_value(old_money.group(1))
        new_val = _money_value(total_match.group(1))
        if old_val is not None and new_val is not None and old_val != new_val:
            return f"${old_money.group(1)} → ${total_match.group(1)}"

    if _EXPANSION_RENT.search(governing):
        rates = parse_dollar_rates(governing)
        extra = _ADDITIONAL_RSF.search(governing) or _ADDITIONAL_RSF.search(original)
        if rates:
            extra_bit = ""
            if extra:
                extra_bit = f"{int(extra.group(1).replace(',', '')):,} RSF at "
            return (
                f"Expansion Space {extra_bit}${rates[0]:.2f}/RSF/year; "
                "original Premises continue at existing rates"
            )

    original_nums = _AMOUNT.findall(_strip_dates(original))
    governing_nums = []
    for match in _AMOUNT.finditer(_strip_dates(governing)):
        token = match.group(0)
        prefix = _strip_dates(governing)[max(0, match.start() - 40) : match.start()]
        if "$" in token and _ADDITIONAL_MONEY.search(prefix):
            continue
        governing_nums.append(token)

    def _key(token: str) -> str:
        return re.sub(r"[\s,$]", "", token)

    def _kind(token: str) -> str:
        if "%" in token:
            return "pct"
        if "$" in token:
            return "money"
        return "num"

    def _pairs(old_nums: List[str], new_nums: List[str]) -> List[str]:
        found: List[str] = []
        used = set()
        for old in old_nums:
            old_key = _key(old)
            old_kind = _kind(old)
            old_val = _money_value(old) if old_kind == "money" else None
            for index, new in enumerate(new_nums):
                if index in used or old_kind != _kind(new):
                    continue
                if _key(new) == old_key:
                    continue
                if old_kind == "money":
                    new_val = _money_value(new)
                    if old_val and new_val:
                        ratio = max(old_val, new_val) / min(old_val, new_val)
                        if ratio > 20:
                            continue
                found.append(f"{old.strip()} → {new.strip()}")
                used.add(index)
                break
            if len(found) >= 3:
                break
        return found

    preferred = _pairs(
        [token for token in original_nums if _kind(token) in {"money", "pct"}],
        [token for token in governing_nums if _kind(token) in {"money", "pct"}],
    )
    pairs = preferred or _pairs(original_nums, governing_nums)
    if pairs:
        return "; ".join(pairs)
    if original and governing and original != governing:
        return "Wording changed — see Original vs Amendment below"
    return "No numeric change detected"


def amendment_label(number: Any, when: Any) -> str:
    if number in (None, ""):
        return "Amendment"
    if when:
        return f"Amendment No. {number} ({when})"
    return f"Amendment No. {number}"


def _amendment_lookup(amendments: Iterable[dict]) -> Dict[str, dict]:
    lookup: Dict[str, dict] = {}
    for amendment in amendments:
        for key in ("amendment_id", "id"):
            value = amendment.get(key)
            if value:
                lookup[str(value)] = amendment
    return lookup


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _row_when_iso(row: Optional[dict]) -> str:
    if not row:
        return ""
    for key in ("effective_from", "effective_date", "amendment_date", "created_at"):
        text = _clean(row.get(key))
        if text:
            return text[:10]
    return ""


def _version_rank(row: dict) -> tuple:
    """Latest row: higher version wins, then later date. Ignore stale is_current flags."""
    return (_as_int(row.get("version_number")), _row_when_iso(row))


def _sort_versions(rows: Iterable[dict]) -> List[dict]:
    return sorted(rows, key=_version_rank)


def abstract_filename(model: Dict[str, Any]) -> str:
    tenant = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        _clean(model.get("prepared_for")) or _clean(model.get("tenant_name")) or "client",
    )
    tenant = tenant.strip("-")[:40] or "client"
    as_of = _clean(model.get("as_of")) or date.today().isoformat()
    return f"Amendment-Resolution-Abstract-{tenant}-{as_of}.pdf"


_CHANGE_TYPES = {
    "MODIFIES",
    "SUPERSEDES",
    "ADDS",
    "DELETES",
    "CONDITIONALLY_MODIFIES",
}


def _clause_change_lookup(amendment_clauses: Optional[Iterable[dict]]) -> Dict[str, dict]:
    lookup: Dict[str, dict] = {}
    rows = [row for row in (amendment_clauses or []) if row.get("clause_type")]
    rows.sort(
        key=lambda row: (
            _row_when_iso(row) or "9999-12-31",
            _as_int(row.get("amendment_number")),
            _as_int(row.get("version_number")),
        )
    )
    for row in rows:
        lookup[row["clause_type"]] = row
    return lookup


def _modified_clause_names(
    amendments: Iterable[dict],
    clause_changes: Dict[str, dict],
) -> set:
    names = set(clause_changes)
    for amendment in amendments:
        for name in amendment.get("modified_clauses") or []:
            if name:
                names.add(name)
    return names


def _resolve_clause_values(
    original_value: str,
    governing_value: str,
    recorded_change: Optional[dict],
) -> tuple[str, str]:
    """Prefer the recorded amendment before/after when history collapsed."""
    recorded = recorded_change or {}
    recorded_original = _clean(recorded.get("original_value"))
    recorded_new = _clean(recorded.get("new_value"))
    if recorded_original and (
        not original_value
        or original_value == governing_value
        or (recorded_new and original_value == recorded_new)
    ):
        original_value = recorded_original
    if recorded_new and (not governing_value or governing_value == original_value):
        governing_value = recorded_new
    if (
        original_value
        and governing_value
        and original_value == governing_value
        and recorded_original
        and recorded_new
        and recorded_original != recorded_new
    ):
        original_value = recorded_original
        governing_value = recorded_new
    return original_value, governing_value


def _first_text(*values: Any) -> str:
    for value in values:
        text = _clean(value)
        if text:
            return text
    return ""


def _annotate_clause_sources(clause: Dict[str, Any]) -> Dict[str, Any]:
    if not _clean(clause.get("original_source_text")):
        clause["original_source_text"] = _clean(clause.get("original_value"))
    if not _clean(clause.get("governing_source_text")):
        clause["governing_source_text"] = _first_text(
            clause.get("source_text"),
            clause.get("governing_value"),
        )
    return clause


def build_amendment_resolution_model(
    lease: Optional[dict],
    amendments: Optional[Iterable[dict]],
    history_rows: Optional[Iterable[dict]],
    as_of: Optional[str] = None,
    prepared_for: Optional[str] = None,
    amendment_clauses: Optional[Iterable[dict]] = None,
) -> Dict[str, Any]:
    """Group clause history into original vs current governing values."""
    lease = lease or {}
    amendment_list = list(amendments or [])
    amendment_list.sort(key=lambda item: item.get("amendment_number") or 0)
    amendments_by_id = _amendment_lookup(amendment_list)
    clause_changes = _clause_change_lookup(amendment_clauses)
    modified_names = _modified_clause_names(amendment_list, clause_changes)

    by_type: Dict[str, List[dict]] = {}
    for row in history_rows or []:
        clause_type = row.get("clause_type")
        if not clause_type:
            continue
        by_type.setdefault(clause_type, []).append(row)

    clauses: List[dict] = []
    seen_types = set()
    for clause_type, rows in sorted(by_type.items()):
        seen_types.add(clause_type)
        versions = _sort_versions(rows)
        original = next(
            (
                row
                for row in versions
                if row.get("source_document_type") == "BASE_LEASE" or _as_int(row.get("version_number")) == 0
            ),
            versions[0],
        )
        current = versions[-1]
        original_value, governing_value = _resolve_clause_values(
            _clean(original.get("clause_value")),
            _clean(current.get("clause_value")),
            clause_changes.get(clause_type),
        )
        recorded = clause_changes.get(clause_type) or {}
        source_id = str(current.get("source_document_id") or recorded.get("amendment_id") or "")
        linked = amendments_by_id.get(source_id, {})
        amendment_number = linked.get("amendment_number")
        amendment_date = linked.get("amendment_date")
        source_is_amendment = (
            current.get("source_document_type") == "AMENDMENT"
            or clause_type in modified_names
            or bool(recorded)
        )
        if amendment_number in (None, "") and source_is_amendment:
            amendment_number = current.get("version_number") or 1
        if not amendment_date:
            amendment_date = current.get("effective_from") or recorded.get("effective_date")
        modification_type = (
            current.get("modification_type")
            or recorded.get("modification_type")
            or "Original"
        )
        changed = (
            original_value != governing_value
            or source_is_amendment
            or str(modification_type).upper() in _CHANGE_TYPES
        )
        label = amendment_label(amendment_number, amendment_date) if changed else "Original lease"
        clauses.append(
            {
                "clause_type": clause_type,
                "original_value": original_value or "N/A",
                "governing_value": governing_value or "N/A",
                "changed": changed,
                "original_source": original.get("source_document_type") or "BASE_LEASE",
                "governing_source": current.get("source_document_type") or (
                    "AMENDMENT" if changed else "BASE_LEASE"
                ),
                "governing_version": current.get("version_number"),
                "governing_amendment_number": amendment_number,
                "governing_amendment_date": amendment_date,
                "governing_label": label,
                "change_summary": summarize_clause_change(original_value, governing_value),
                "effective_from": current.get("effective_from") or recorded.get("effective_date"),
                "modification_type": modification_type,
                "original_source_text": _first_text(
                    original.get("source_text"),
                    recorded.get("original_value"),
                    original.get("clause_value"),
                    original_value,
                ),
                "governing_source_text": _first_text(
                    current.get("source_text"),
                    recorded.get("source_text"),
                    recorded.get("new_value"),
                    current.get("clause_value"),
                    governing_value,
                ),
                "original_source_page": original.get("source_page") or original.get("page"),
                "governing_source_page": (
                    current.get("source_page")
                    or recorded.get("source_page")
                    or current.get("page")
                ),
                "source_text": _first_text(
                    current.get("source_text"),
                    recorded.get("source_text"),
                    recorded.get("new_value"),
                ),
                "versions": versions,
            }
        )

    for amendment in amendment_list:
        extracted = amendment.get("extracted_data") or {}
        text = ""
        if isinstance(extracted, dict):
            text = extracted.get("amendment_text") or ""
            for mod in extracted.get("Clause_Modifications") or []:
                if not isinstance(mod, dict):
                    continue
                if (mod.get("clause_type") or "") == "Order of Precedence":
                    text = text or mod.get("new_value") or ""
        for extra in extract_structural_clauses(
            text or amendment.get("amendment_text") or "",
            amendment.get("effective_date") or amendment.get("amendment_date"),
        ):
            extra_type = extra["clause_type"]
            if extra_type in seen_types:
                continue
            clause_changes.setdefault(extra_type, {
                "amendment_id": amendment.get("amendment_id") or amendment.get("id"),
                "clause_type": extra_type,
                "modification_type": extra.get("modification_type"),
                "original_value": extra.get("original_value"),
                "new_value": extra.get("new_value"),
                "effective_date": extra.get("effective_date"),
            })
            modified_names.add(extra_type)

    for clause_type in sorted(modified_names - seen_types):
        recorded = clause_changes.get(clause_type) or {}
        linked = amendments_by_id.get(str(recorded.get("amendment_id") or ""), amendment_list[0] if amendment_list else {})
        original_value = _clean(recorded.get("original_value")) or "Not separately retained"
        governing_value = _clean(recorded.get("new_value")) or "N/A"
        clauses.append(
            {
                "clause_type": clause_type,
                "original_value": original_value,
                "governing_value": governing_value,
                "changed": True,
                "original_source": "BASE_LEASE",
                "governing_source": "AMENDMENT",
                "governing_version": linked.get("amendment_number") or 1,
                "governing_amendment_number": linked.get("amendment_number") or 1,
                "governing_amendment_date": linked.get("amendment_date"),
                "governing_label": amendment_label(
                    linked.get("amendment_number") or 1,
                    linked.get("amendment_date"),
                ),
                "change_summary": summarize_clause_change(original_value, governing_value),
                "effective_from": recorded.get("effective_date") or linked.get("amendment_date"),
                "modification_type": recorded.get("modification_type") or "MODIFIES",
                "original_source_text": _first_text(recorded.get("original_value"), original_value),
                "governing_source_text": _first_text(
                    recorded.get("source_text"),
                    recorded.get("new_value"),
                    governing_value,
                ),
                "source_text": _first_text(recorded.get("source_text"), recorded.get("new_value")),
                "versions": [],
            }
        )

    clauses = apply_related_clause_updates(clauses)
    for clause in clauses:
        _annotate_clause_sources(clause)
        if clause.get("changed"):
            clause["change_summary"] = summarize_clause_change(
                clause.get("original_value") or "",
                clause.get("governing_value") or "",
            )
    changed = [clause for clause in clauses if clause["changed"]]
    unchanged = [clause for clause in clauses if not clause["changed"]]
    for index, clause in enumerate(changed, start=1):
        clause["change_number"] = index
    as_of_value = as_of or date.today().isoformat()
    prepared = _clean(prepared_for) or _clean(lease.get("tenant_name")) or "Client"
    return {
        "property_address": lease.get("property_address") or "Unknown property",
        "tenant_name": lease.get("tenant_name") or "Unknown tenant",
        "prepared_for": prepared,
        "as_of": as_of_value,
        "amendments": amendment_list,
        "clauses": clauses,
        "changed_clauses": changed,
        "unchanged_clauses": unchanged,
        "value": {
            "product_name": "Amendment Resolution Graph",
            "deliverable_name": "Amendment Resolution Abstract",
            "statement": VALUE_STATEMENT,
            "client_uses": CLIENT_USES,
            "amendments_resolved": len(amendment_list),
            "clauses_tracked": len(clauses),
            "clauses_superseded": len(changed),
            "clauses_still_original": len(unchanged),
            "as_of": as_of_value,
            "prepared_for": prepared,
        },
    }


def generate_amendment_resolution_pdf(model: Dict[str, Any]) -> bytes:
    """Render the amendment resolution model as a client PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AmendmentReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#1976D2"),
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "AmendmentReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1976D2"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "AmendmentReportBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
    )
    label_style = ParagraphStyle(
        "AmendmentReportLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "AmendmentReportTableHeader",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.whitesmoke,
        alignment=TA_CENTER,
        leading=10,
    )
    source_style = ParagraphStyle(
        "AmendmentReportSource",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#546E7A"),
        alignment=TA_LEFT,
    )

    value = model.get("value") or {}
    story = []
    story.append(Paragraph(f"{config.APP_NAME} Amendment Resolution Abstract", title_style))
    story.append(Paragraph(_pdf_text(value.get("statement") or VALUE_STATEMENT), body_style))
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Paragraph(
            "Each controlling value is cited to the source document text. "
            "The Source Exhibit is the workpaper an auditor, lender, or buyer can attach.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        Paragraph(
            f"<b>Client uses:</b> {_pdf_text(value.get('client_uses') or CLIENT_USES)}",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    info = [
        [Paragraph("Prepared for", label_style), Paragraph(_pdf_text(model.get("prepared_for")), body_style)],
        [Paragraph("Property", label_style), Paragraph(_pdf_text(model.get("property_address")), body_style)],
        [Paragraph("Tenant / Customer", label_style), Paragraph(_pdf_text(model.get("tenant_name")), body_style)],
        [Paragraph("Controlling as of", label_style), Paragraph(_pdf_text(model.get("as_of")), body_style)],
        [
            Paragraph("Amendments resolved", label_style),
            Paragraph(_pdf_text(value.get("amendments_resolved", len(model.get("amendments") or []))), body_style),
        ],
        [
            Paragraph("Clauses superseded", label_style),
            Paragraph(_pdf_text(value.get("clauses_superseded", len(model.get("changed_clauses") or []))), body_style),
        ],
        [
            Paragraph("Clauses still original", label_style),
            Paragraph(_pdf_text(value.get("clauses_still_original", len(model.get("unchanged_clauses") or []))), body_style),
        ],
        [
            Paragraph("Clauses tracked", label_style),
            Paragraph(_pdf_text(value.get("clauses_tracked", len(model.get("clauses") or []))), body_style),
        ],
    ]
    info_table = Table(info, colWidths=[1.8 * inch, 5.0 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E3F2FD")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#90CAF9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)

    story.append(Paragraph("Exhibit A — Amendment chain", heading_style))
    amendments = model.get("amendments") or []
    if not amendments:
        story.append(
            Paragraph(
                "No amendments are on file. Current governing language is the original lease.",
                body_style,
            )
        )
    else:
        rows = [[
            Paragraph("No.", header_style),
            Paragraph("Date", header_style),
            Paragraph("Status", header_style),
            Paragraph("Clauses modified", header_style),
        ]]
        for amendment in amendments:
            modified = amendment.get("modified_clauses") or []
            modified_text = ", ".join(_clean(item) for item in modified if item) or "None recorded"
            rows.append(
                [
                    Paragraph(_pdf_text(amendment.get("amendment_number")), body_style),
                    Paragraph(_pdf_text(amendment.get("amendment_date")), body_style),
                    Paragraph(_pdf_text(amendment.get("status")), body_style),
                    Paragraph(_pdf_text(modified_text, limit=400), body_style),
                ]
            )
        timeline = Table(rows, colWidths=[0.55 * inch, 1.3 * inch, 1.7 * inch, 3.25 * inch])
        timeline.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#90CAF9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(timeline)

    story.append(Paragraph("Schedule A — Controlling language that replaced the original", heading_style))
    changed = model.get("changed_clauses") or []
    if not changed:
        story.append(
            Paragraph(
                "No clause has been superseded yet. The original lease language still governs.",
                body_style,
            )
        )
    else:
        for clause in changed:
            block = [
                Paragraph(
                    f"{_pdf_text(clause.get('change_number'))}. {_pdf_text(clause.get('clause_type'))} — "
                    f"{_pdf_text(clause.get('governing_label'))}",
                    label_style,
                ),
                Paragraph(
                    f"<b>Changed:</b> {_pdf_text(clause.get('change_summary'))}",
                    body_style,
                ),
                Paragraph(
                    f"{_pdf_text(clause.get('modification_type'))}"
                    + (
                        f", linked from {_pdf_text(clause.get('linked_from'))}"
                        if clause.get("linked_from")
                        else ""
                    )
                    + f", effective {_pdf_text(clause.get('effective_from'))}.",
                    body_style,
                ),
                Spacer(1, 0.06 * inch),
                Paragraph("<b>Original lease</b>", label_style),
                Paragraph(_pdf_text(clause.get("original_value")), body_style),
                Paragraph(
                    f"<i>Source: {format_source_html(clause_source(clause, 'original'))}</i>",
                    source_style,
                ),
                Spacer(1, 0.06 * inch),
                Paragraph(
                    f"<b>Now governed by {_pdf_text(clause.get('governing_label'))}</b>",
                    label_style,
                ),
                Paragraph(_pdf_text(clause.get("governing_value")), body_style),
                Paragraph(
                    f"<i>Source: {format_source_html(clause_source(clause, 'governing'))}</i>",
                    source_style,
                ),
                Spacer(1, 0.16 * inch),
            ]
            story.append(KeepTogether(block))

    story.append(Paragraph("Schedule B — Clauses still governed by the original lease", heading_style))
    unchanged = model.get("unchanged_clauses") or []
    if not unchanged:
        story.append(Paragraph("Every tracked clause has been amended.", body_style))
    else:
        for clause in unchanged:
            story.append(
                KeepTogether(
                    [
                        Paragraph(_pdf_text(clause.get("clause_type")), label_style),
                        Paragraph(_pdf_text(clause.get("governing_value")), body_style),
                        Paragraph(
                            f"<i>Source: {format_source_html(clause_source(clause, 'governing'))}</i>",
                            source_style,
                        ),
                        Spacer(1, 0.12 * inch),
                    ]
                )
            )

    story.append(Paragraph("Source Exhibit — where each controlling value came from", heading_style))
    story.append(
        Paragraph(
            "Document, page (if captured), and the excerpt used for the value. "
            "Derived figures name the parent clause.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    exhibit_rows = [[
        Paragraph("Clause", header_style),
        Paragraph("Document / page", header_style),
        Paragraph("Source excerpt", header_style),
    ]]
    for clause in model.get("clauses") or []:
        source = clause_source(clause, "governing")
        page_bit = f", p. {source['page']}" if source.get("page") else ""
        derived = (
            f"<br/>Derived from {_pdf_text(source.get('derived_from'))}"
            if source.get("derived_from")
            else ""
        )
        exhibit_rows.append(
            [
                Paragraph(_pdf_text(clause.get("clause_type")), label_style),
                Paragraph(f"{_pdf_text(source.get('document'))}{page_bit}{derived}", source_style),
                Paragraph(_pdf_text(source.get("excerpt") or "Source excerpt was not stored", limit=500), source_style),
            ]
        )
    if len(exhibit_rows) > 1:
        exhibit = Table(exhibit_rows, colWidths=[1.7 * inch, 1.9 * inch, 3.2 * inch], repeatRows=1)
        exhibit.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#90CAF9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(exhibit)

    generated = datetime.now().strftime("%B %d, %Y")
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            f"Prepared by {config.APP_NAME} Amendment Resolution Graph for "
            f"{_pdf_text(model.get('prepared_for'))}. Generated {generated}. "
            "This abstract is a file exhibit of resolved controlling terms. "
            "It is not a legal opinion.",
            body_style,
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
