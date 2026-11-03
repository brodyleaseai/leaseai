"""Client-facing Amendment Resolution report.

Builds a structured model of original vs current governing clauses, then
renders a branded PDF the customer can keep with the lease file.
"""

from __future__ import annotations

import html
import io
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


def build_amendment_resolution_model(
    lease: Optional[dict],
    amendments: Optional[Iterable[dict]],
    history_rows: Optional[Iterable[dict]],
    as_of: Optional[str] = None,
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
    return {
        "property_address": lease.get("property_address") or "Unknown property",
        "tenant_name": lease.get("tenant_name") or "Unknown tenant",
        "as_of": as_of or date.today().isoformat(),
        "amendments": amendment_list,
        "clauses": clauses,
        "changed_clauses": changed,
        "unchanged_clauses": unchanged,
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

    story = []
    story.append(Paragraph(f"{config.APP_NAME} Amendment Resolution Report", title_style))
    story.append(
        Paragraph(
            "This report shows how amendments changed the original lease and which "
            "clause language currently governs.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    info = [
        [Paragraph("Property", label_style), Paragraph(_pdf_text(model.get("property_address")), body_style)],
        [Paragraph("Tenant / Customer", label_style), Paragraph(_pdf_text(model.get("tenant_name")), body_style)],
        [Paragraph("Governing as of", label_style), Paragraph(_pdf_text(model.get("as_of")), body_style)],
        [
            Paragraph("Amendments on file", label_style),
            Paragraph(_pdf_text(len(model.get("amendments") or [])), body_style),
        ],
        [
            Paragraph("Clauses changed", label_style),
            Paragraph(_pdf_text(len(model.get("changed_clauses") or [])), body_style),
        ],
        [
            Paragraph("Clauses still original", label_style),
            Paragraph(_pdf_text(len(model.get("unchanged_clauses") or [])), body_style),
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

    story.append(Paragraph("Amendment timeline", heading_style))
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

    story.append(Paragraph("Current governing clauses that replace the original", heading_style))
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

    story.append(Paragraph("Clauses still governed by the original lease", heading_style))
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
            f"Prepared by {config.APP_NAME} for the lease file. Generated {generated}.",
            body_style,
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
