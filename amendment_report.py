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
from lease_report import _header_footer

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


def _sort_versions(rows: Iterable[dict]) -> List[dict]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("version_number") is None,
            row.get("version_number") if isinstance(row.get("version_number"), int) else 0,
        ),
    )


def abstract_filename(model: Dict[str, Any]) -> str:
    tenant = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        _clean(model.get("prepared_for")) or _clean(model.get("tenant_name")) or "client",
    )
    tenant = tenant.strip("-")[:40] or "client"
    as_of = _clean(model.get("as_of")) or date.today().isoformat()
    return f"Amendment-Resolution-Abstract-{tenant}-{as_of}.pdf"


def build_amendment_resolution_model(
    lease: Optional[dict],
    amendments: Optional[Iterable[dict]],
    history_rows: Optional[Iterable[dict]],
    as_of: Optional[str] = None,
    prepared_for: Optional[str] = None,
) -> Dict[str, Any]:
    """Group clause history into original vs current governing values."""
    lease = lease or {}
    amendment_list = list(amendments or [])
    amendment_list.sort(key=lambda item: item.get("amendment_number") or 0)

    by_type: Dict[str, List[dict]] = {}
    for row in history_rows or []:
        clause_type = row.get("clause_type")
        if not clause_type:
            continue
        by_type.setdefault(clause_type, []).append(row)

    clauses: List[dict] = []
    for clause_type, rows in sorted(by_type.items()):
        versions = _sort_versions(rows)
        original = next(
            (
                row
                for row in versions
                if row.get("source_document_type") == "BASE_LEASE" or row.get("version_number") == 0
            ),
            versions[0],
        )
        current = next((row for row in versions if row.get("is_current")), versions[-1])
        original_value = _clean(original.get("clause_value"))
        governing_value = _clean(current.get("clause_value"))
        clauses.append(
            {
                "clause_type": clause_type,
                "original_value": original_value or "N/A",
                "governing_value": governing_value or "N/A",
                "changed": original_value != governing_value,
                "original_source": original.get("source_document_type") or "BASE_LEASE",
                "governing_source": current.get("source_document_type") or "BASE_LEASE",
                "governing_version": current.get("version_number"),
                "effective_from": current.get("effective_from"),
                "modification_type": current.get("modification_type") or "Original",
                "versions": versions,
            }
        )

    changed = [clause for clause in clauses if clause["changed"]]
    unchanged = [clause for clause in clauses if not clause["changed"]]
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

    value = model.get("value") or {}
    story = []
    story.append(Paragraph(f"{config.APP_NAME} Amendment Resolution Abstract", title_style))
    story.append(Paragraph(_pdf_text(value.get("statement") or VALUE_STATEMENT), body_style))
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
            Paragraph("#", header_style),
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
        timeline = Table(rows, colWidths=[0.6 * inch, 1.3 * inch, 1.6 * inch, 3.3 * inch])
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
                Paragraph(_pdf_text(clause.get("clause_type")), label_style),
                Paragraph(
                    f"Now governed by {_pdf_text(clause.get('governing_source'))} "
                    f"v{_pdf_text(clause.get('governing_version'))} "
                    f"({_pdf_text(clause.get('modification_type'))}), "
                    f"effective {_pdf_text(clause.get('effective_from'))}.",
                    body_style,
                ),
                Spacer(1, 0.06 * inch),
                Paragraph("<b>Original lease</b>", label_style),
                Paragraph(_pdf_text(clause.get("original_value")), body_style),
                Spacer(1, 0.06 * inch),
                Paragraph("<b>Current governing language</b>", label_style),
                Paragraph(_pdf_text(clause.get("governing_value")), body_style),
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
                        Spacer(1, 0.12 * inch),
                    ]
                )
            )

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
