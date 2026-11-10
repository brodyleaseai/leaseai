"""Current Lease Position — calculated file on the Amendment Resolution Graph.

The Resolution Abstract says which language governs. This report says what
those terms mean in money and dates, and labels every number as extracted,
amended, calculated, or review required.
"""

from __future__ import annotations

import html
import io
import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config
from amendment_clause_links import (
    implied_schedule_rsf,
    parse_dollar_rates,
    parse_rate_periods,
    parse_rsf,
)
from lease_report import _header_footer
from report_sources import clause_source, format_source_line

STATUS_EXTRACTED = "Extracted"
STATUS_AMENDED = "Amended"
STATUS_CALCULATED = "Calculated"
STATUS_REVIEW = "Review required"

VALUE_STATEMENT = (
    "This Current Lease Position states the governing terms as of a given date "
    "and the financial figures derived from them. Calculated amounts are "
    "arithmetic on resolved inputs. They are not dollar amounts expressly "
    "stated by the parties unless the Status column says Extracted or Amended."
)

CLIENT_USES = (
    "Billing files, estoppels, lender and buyer packages, and audit workpapers."
)

POSITION_FIELDS: Sequence[Tuple[str, Tuple[str, ...]]] = (
    ("Premises / RSF", ("Premises Description", "Expansion of Premises", "Premises")),
    ("Base Rent (stated)", ("Base Rent",)),
    ("Rent Schedule", ("Rent Schedule",)),
    ("Rent Escalations", ("Rent Escalations",)),
    ("Commencement Date", ("Commencement Date", "Lease Commencement Date")),
    ("Expiration Date", ("Lease Expiration Date", "Expiration Date", "Lease End Date")),
    ("Proportionate Share", ("Proportionate Share", "Tenant's Proportionate Share", "Pro Rata Share")),
    ("Renewal Notice Deadline", ("Renewal Notice Deadline",)),
    ("Security Deposit", ("Security Deposit",)),
    ("CAM Cap", ("CAM Cap", "CAM Annual Increase Cap")),
)

STATED_MONTHLY = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(?:per month|/month|/mo\b)",
    re.IGNORECASE,
)
STATED_ANNUAL = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(?:per (?:annum|year)|/year|annual)",
    re.IGNORECASE,
)
SCHEDULE_MONTHLY = re.compile(
    r"=\s*\$([0-9,]+(?:\.[0-9]+)?)/month",
    re.IGNORECASE,
)
WHOLE_PREMISES = re.compile(
    r"entire premises|whole premises|in total|multiplied by|rentable square feet|remaining premises",
    re.IGNORECASE,
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pdf_text(value: Any, limit: int = 800) -> str:
    text = html.escape(_clean(value) or "—")
    if len(text) > limit:
        text = text[:limit] + "…"
    return text.replace("\n", "<br/>")


def _money(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}"


def _clause_map(model: Optional[dict]) -> Dict[str, dict]:
    return {
        clause.get("clause_type"): clause
        for clause in (model or {}).get("clauses") or []
        if clause.get("clause_type")
    }


def _first_clause(clauses: Dict[str, dict], names: Iterable[str]) -> Optional[dict]:
    for name in names:
        if name in clauses:
            return clauses[name]
    return None


def _status_for_clause(clause: Optional[dict]) -> str:
    if not clause:
        return STATUS_EXTRACTED
    if clause.get("linked_from") or clause.get("derived_from"):
        return STATUS_CALCULATED
    if clause.get("changed"):
        return STATUS_AMENDED
    return STATUS_EXTRACTED


def _money_value(match: Optional[re.Match]) -> Optional[float]:
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _current_rate(base_rent: str, schedule: str) -> Optional[float]:
    periods = parse_rate_periods(base_rent) or parse_rate_periods(schedule)
    if periods:
        return periods[0]["annual_rate"]
    rates = parse_dollar_rates(base_rent) or parse_dollar_rates(schedule)
    return rates[-1] if rates else None


def _current_rsf(*texts: str) -> Optional[int]:
    for text in texts:
        value = parse_rsf(text or "") or implied_schedule_rsf(text or "")
        if value:
            return value
    return None


def _schedule_monthly(schedule: str) -> Optional[float]:
    match = SCHEDULE_MONTHLY.search(schedule or "")
    return _money_value(match)


def _amounts_differ(left: Optional[float], right: Optional[float]) -> bool:
    if left is None or right is None:
        return False
    tolerance = max(1.0, abs(left) * 0.01)
    return abs(left - right) > tolerance


def _rate_scope_unclear(base_rent: str, expansion: Optional[dict]) -> bool:
    if not expansion or not expansion.get("changed"):
        return False
    if not parse_dollar_rates(base_rent):
        return False
    return not WHOLE_PREMISES.search(base_rent or "")


def _row(
    field: str,
    current: str,
    previous: str = "",
    effective: str = "",
    status: str = STATUS_EXTRACTED,
    calculation: str = "",
    source: str = "",
    notes: str = "",
    review: bool = False,
) -> Dict[str, str]:
    return {
        "field": field,
        "current_value": current or "—",
        "previous_value": previous or "—",
        "effective_date": effective or "—",
        "status": STATUS_REVIEW if review else status,
        "calculation": calculation or "—",
        "source": source or "—",
        "notes": notes,
    }


def _clause_row(label: str, clause: dict) -> Dict[str, str]:
    source = format_source_line(clause_source(clause, "governing"), limit=160)
    calculation = ""
    if clause.get("linked_from") or clause.get("derived_from"):
        parent = clause.get("linked_from") or clause.get("derived_from")
        calculation = f"Derived from {parent}"
    return _row(
        label,
        _clean(clause.get("governing_value")),
        _clean(clause.get("original_value")) if clause.get("changed") else "",
        _clean(clause.get("effective_from") or clause.get("governing_amendment_date")),
        _status_for_clause(clause),
        calculation,
        source,
    )


def build_current_lease_position(resolution: Optional[dict]) -> Dict[str, Any]:
    """Turn a resolution model into the Current Lease Position workpaper."""
    model = resolution or {}
    clauses = _clause_map(model)
    rows: List[Dict[str, str]] = []
    flags: List[str] = []

    for label, names in POSITION_FIELDS:
        clause = _first_clause(clauses, names)
        if not clause:
            continue
        rows.append(_clause_row(label, clause))

    premises = _first_clause(clauses, ("Premises Description", "Expansion of Premises", "Premises"))
    base_rent = _first_clause(clauses, ("Base Rent",))
    schedule = _first_clause(clauses, ("Rent Schedule",))
    expansion = clauses.get("Expansion of Premises")
    premises_text = (premises or {}).get("governing_value") or ""
    rent_text = (base_rent or {}).get("governing_value") or ""
    schedule_text = (schedule or {}).get("governing_value") or ""
    rsf = _current_rsf(premises_text, rent_text, schedule_text)
    rate = _current_rate(rent_text, schedule_text)
    computed_annual = round(rsf * rate, 2) if rsf and rate else None
    computed_monthly = round(computed_annual / 12.0, 2) if computed_annual is not None else None
    schedule_monthly = _schedule_monthly(schedule_text)
    stated_monthly = _money_value(STATED_MONTHLY.search(rent_text))
    stated_annual = _money_value(STATED_ANNUAL.search(rent_text))
    source_bits = []
    if base_rent:
        source_bits.append(format_source_line(clause_source(base_rent, "governing"), limit=120))
    if premises:
        source_bits.append(format_source_line(clause_source(premises, "governing"), limit=120))
    calc_source = " · ".join(part for part in source_bits if part)
    effective = _clean(
        (base_rent or {}).get("effective_from")
        or (premises or {}).get("effective_from")
        or (schedule or {}).get("effective_from")
    )
    previous_rent = _clean((base_rent or {}).get("original_value")) if (base_rent or {}).get("changed") else ""

    if _rate_scope_unclear(rent_text, expansion):
        flags.append(
            "The governing rent rate does not clearly say it applies to the entire "
            "premises. Confirm whether the new rate covers all RSF or only an expansion area."
        )

    if rate and not rsf:
        flags.append(
            "A governing rent rate was found, but premises RSF is missing, so annual "
            "and monthly rent were not calculated."
        )
        rows.append(
            _row(
                "Annual Base Rent",
                "Not calculated — RSF missing",
                previous_rent,
                effective,
                STATUS_REVIEW,
                f"Need RSF × {_money(rate)}/RSF",
                calc_source,
                review=True,
            )
        )
    elif rsf and not rate and not schedule_monthly:
        flags.append(
            "Premises RSF is known, but no per-square-foot rate was found, so annual "
            "rent was not calculated from area."
        )
    elif computed_annual is not None:
        mismatch = False
        if _amounts_differ(computed_monthly, stated_monthly) or _amounts_differ(computed_annual, stated_annual):
            mismatch = True
            flags.append(
                "A stated rent total does not match RSF × rate. Both figures are shown; "
                "do not treat either as final without review."
            )
        if schedule_monthly and _amounts_differ(computed_monthly, schedule_monthly):
            mismatch = True
            flags.append(
                "The derived rent schedule monthly amount does not match RSF × rate."
            )
        formula = f"{rsf:,} RSF × {_money(rate)} / RSF / year"
        rows.append(
            _row(
                "Annual Base Rent",
                _money(computed_annual),
                previous_rent,
                effective,
                STATUS_REVIEW if mismatch else STATUS_CALCULATED,
                formula,
                calc_source,
                "Derived calculation, not a dollar amount expressly stated in the amendment."
                if not stated_annual
                else "",
                review=mismatch,
            )
        )
        rows.append(
            _row(
                "Monthly Base Rent",
                _money(computed_monthly),
                "",
                effective,
                STATUS_REVIEW if mismatch else STATUS_CALCULATED,
                f"{formula} ÷ 12 = {_money(computed_monthly)}",
                calc_source,
                review=mismatch,
            )
        )

    review_rows = [row for row in rows if row["status"] == STATUS_REVIEW]
    calculated_rows = [row for row in rows if row["status"] == STATUS_CALCULATED]
    as_of_value = model.get("as_of") or date.today().isoformat()
    prepared = _clean(model.get("prepared_for")) or _clean(model.get("tenant_name")) or "Client"
    return {
        "property_address": model.get("property_address") or "Unknown property",
        "tenant_name": model.get("tenant_name") or "Unknown tenant",
        "prepared_for": prepared,
        "as_of": as_of_value,
        "amendments": model.get("amendments") or [],
        "rows": rows,
        "review_flags": flags,
        "value": {
            "product_name": "Amendment Resolution Graph",
            "deliverable_name": "Current Lease Position",
            "statement": VALUE_STATEMENT,
            "client_uses": CLIENT_USES,
            "amendments_resolved": len(model.get("amendments") or []),
            "fields_reported": len(rows),
            "calculated_fields": len(calculated_rows),
            "review_required": len(review_rows) + len(flags),
            "as_of": as_of_value,
            "prepared_for": prepared,
        },
    }


def build_position_from_graph(
    lease: Optional[dict],
    amendments: Optional[Iterable[dict]] = None,
    history_rows: Optional[Iterable[dict]] = None,
    as_of: Optional[str] = None,
    prepared_for: Optional[str] = None,
    amendment_clauses: Optional[Iterable[dict]] = None,
) -> Dict[str, Any]:
    """Resolve the graph as of a date, then build the position report."""
    from asc842_amendment import resolution_as_of

    resolution = resolution_as_of(
        lease,
        amendments,
        history_rows,
        as_of or date.today().isoformat(),
        amendment_clauses=amendment_clauses,
        prepared_for=prepared_for,
    )
    return build_current_lease_position(resolution)


def position_filename(model: Dict[str, Any]) -> str:
    client = re.sub(r"[^A-Za-z0-9]+", "-", _clean(model.get("prepared_for")) or "Client").strip("-")
    as_of = _clean(model.get("as_of")) or date.today().isoformat()
    return f"Current-Lease-Position-{client}-{as_of}.pdf"


def generate_current_lease_position_pdf(model: Dict[str, Any]) -> bytes:
    """Render the Current Lease Position as a client PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PositionTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1976D2"),
        spaceAfter=8,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "PositionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1976D2"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "PositionBody",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        alignment=TA_LEFT,
    )
    label_style = ParagraphStyle(
        "PositionLabel",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "PositionHeader",
        parent=styles["Normal"],
        fontSize=7,
        fontName="Helvetica-Bold",
        textColor=colors.whitesmoke,
        alignment=TA_CENTER,
        leading=9,
    )
    cell_style = ParagraphStyle(
        "PositionCell",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
    )

    value = model.get("value") or {}
    story = []
    story.append(Paragraph(f"{config.APP_NAME} Current Lease Position", title_style))
    story.append(Paragraph(_pdf_text(value.get("statement") or VALUE_STATEMENT), body_style))
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Paragraph(
            f"<b>Client uses:</b> {_pdf_text(value.get('client_uses') or CLIENT_USES)}",
            body_style,
        )
    )
    story.append(Spacer(1, 0.12 * inch))

    info = [
        [Paragraph("Prepared for", label_style), Paragraph(_pdf_text(model.get("prepared_for")), body_style)],
        [Paragraph("Property", label_style), Paragraph(_pdf_text(model.get("property_address")), body_style)],
        [Paragraph("Tenant / Customer", label_style), Paragraph(_pdf_text(model.get("tenant_name")), body_style)],
        [Paragraph("Position as of", label_style), Paragraph(_pdf_text(model.get("as_of")), body_style)],
        [
            Paragraph("Amendments applied", label_style),
            Paragraph(_pdf_text(value.get("amendments_resolved")), body_style),
        ],
        [
            Paragraph("Calculated fields", label_style),
            Paragraph(_pdf_text(value.get("calculated_fields")), body_style),
        ],
        [
            Paragraph("Review required", label_style),
            Paragraph(_pdf_text(value.get("review_required")), body_style),
        ],
    ]
    info_table = Table(info, colWidths=[1.7 * inch, 5.3 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E3F2FD")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#90CAF9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)

    story.append(Paragraph("Current terms", heading_style))
    story.append(
        Paragraph(
            "Status Extracted or Amended means the value comes from governing document text. "
            "Status Calculated means LeaseAI derived the figure from resolved inputs. "
            "Status Review required means a human must confirm the inputs before relying on the number.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.08 * inch))

    table_rows = [[
        Paragraph("Field", header_style),
        Paragraph("Current", header_style),
        Paragraph("Previous", header_style),
        Paragraph("Effective", header_style),
        Paragraph("Status", header_style),
        Paragraph("Calculation / source", header_style),
    ]]
    for row in model.get("rows") or []:
        table_rows.append(
            [
                Paragraph(_pdf_text(row.get("field")), label_style),
                Paragraph(_pdf_text(row.get("current_value"), limit=280), cell_style),
                Paragraph(_pdf_text(row.get("previous_value"), limit=160), cell_style),
                Paragraph(_pdf_text(row.get("effective_date")), cell_style),
                Paragraph(_pdf_text(row.get("status")), cell_style),
                Paragraph(
                    _pdf_text(row.get("calculation"))
                    + "<br/>"
                    + _pdf_text(row.get("source"), limit=220),
                    cell_style,
                ),
            ]
        )
    if len(table_rows) > 1:
        table = Table(
            table_rows,
            colWidths=[1.15 * inch, 1.35 * inch, 1.05 * inch, 0.85 * inch, 0.85 * inch, 1.85 * inch],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#90CAF9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No governing terms are on file for this lease yet.", body_style))

    flags = model.get("review_flags") or []
    if flags or any(row.get("status") == STATUS_REVIEW for row in model.get("rows") or []):
        story.append(Paragraph("Review required", heading_style))
        for flag in flags:
            story.append(Paragraph(f"• {_pdf_text(flag)}", body_style))
        story.append(Spacer(1, 0.08 * inch))

    generated = datetime.now().strftime("%B %d, %Y")
    story.append(Spacer(1, 0.16 * inch))
    story.append(
        Paragraph(
            f"Prepared by {config.APP_NAME} Amendment Resolution Graph for "
            f"{_pdf_text(model.get('prepared_for'))}. Generated {generated}. "
            "Calculated figures are derived from governing terms. They are not a legal opinion "
            "and are not amounts expressly stated by the parties unless marked Extracted or Amended.",
            body_style,
        )
    )
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
