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
    DATE,
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
    r"entire premises|whole premises|for the entire|multiplied by|"
    r"remaining premises",
    re.IGNORECASE,
)
EXPANSION_ONLY_RENT = re.compile(
    r"attributable to the Expansion Space|Expansion Space is charged|"
    r"Base Rent attributable to the Expansion",
    re.IGNORECASE,
)
ADDITIONAL_RSF = re.compile(
    r"additional (\d{1,3}(?:,\d{3})+|\d+)\s+"
    r"(?:rentable square feet|rsf|sq\.?\s*ft|square feet)",
    re.IGNORECASE,
)
EXPANSION_TEASER = re.compile(
    rf"From\s+(?P<start>{DATE})\s+(?:to|through)\s+(?P<end>{DATE})"
    rf".{{0,220}}?\$?(?P<rate>\d{{1,3}}(?:\.\d+)?)\s+per rentable square foot",
    re.IGNORECASE | re.DOTALL,
)
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
LUMP_MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")


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


def _rate_scope_unclear(
    base_rent: str,
    expansion: Optional[dict],
    premises: Optional[dict] = None,
) -> bool:
    if EXPANSION_ONLY_RENT.search(base_rent or ""):
        return True
    premises_text = (premises or {}).get("governing_value") or ""
    has_expansion = bool(expansion and expansion.get("changed")) or bool(
        re.search(r"Expansion Space|additional \d", premises_text, re.IGNORECASE)
    )
    if not has_expansion:
        return False
    if not parse_dollar_rates(base_rent):
        return False
    return not WHOLE_PREMISES.search(base_rent or "")


def _as_date(value: Any) -> Optional[date]:
    text = _clean(value)
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    cleaned = re.sub(r"\s+", " ", text)
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _full_years(start: date, as_of: date) -> int:
    years = as_of.year - start.year
    if (as_of.month, as_of.day) < (start.month, start.day):
        years -= 1
    return max(0, years)


def _lump_rent(text: str, rsf: Optional[int]) -> Optional[Dict[str, float]]:
    if not text or not rsf:
        return None
    match = LUMP_MONEY.search(text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    if 1 <= amount <= 200:
        return {
            "monthly": round(rsf * amount / 12.0, 2),
            "annual": round(rsf * amount, 2),
            "psf": amount,
        }
    monthly_psf = amount * 12.0 / rsf
    annual_psf = amount / rsf
    if 8 <= monthly_psf <= 200:
        return {"monthly": amount, "annual": round(amount * 12.0, 2), "psf": monthly_psf}
    if 8 <= annual_psf <= 200:
        return {"monthly": round(amount / 12.0, 2), "annual": amount, "psf": annual_psf}
    return None


def _escalation_rate(text: str) -> Optional[float]:
    if not text or re.search(r"fixed dollar|none —", text, re.IGNORECASE):
        return None
    match = PERCENT.search(text)
    if not match:
        return None
    return float(match.group(1)) / 100.0


def _expansion_rent(
    premises_text: str,
    rent_text: str,
    original_rent: str,
    original_premises: str,
    escalations: str,
    commencement: str,
    as_of: str,
) -> Optional[Dict[str, Any]]:
    """Original premises + expansion area, never expansion rate × total RSF."""
    if not EXPANSION_ONLY_RENT.search(rent_text or ""):
        return None
    total_rsf = parse_rsf(premises_text or "")
    extra_match = ADDITIONAL_RSF.search(premises_text or "") or ADDITIONAL_RSF.search(
        rent_text or ""
    )
    extra_rsf = int(extra_match.group(1).replace(",", "")) if extra_match else None
    original_rsf = parse_rsf(original_premises or "")
    if not original_rsf and total_rsf and extra_rsf:
        original_rsf = total_rsf - extra_rsf
    lump = _lump_rent(original_rent or "", original_rsf)
    if not total_rsf or not extra_rsf or not original_rsf or not lump:
        return {
            "review": True,
            "reason": (
                "The amendment states an Expansion Space rate. Original premises rent "
                "and remaining RSF are needed before annual or monthly totals can be calculated. "
                "Do not multiply the expansion rate by the entire premises."
            ),
        }

    as_of_date = _as_date(as_of) or date.today()
    pct = _escalation_rate(escalations)
    start = _as_date(commencement)
    years = _full_years(start, as_of_date) if start and pct else 0
    factor = (1 + pct) ** years if pct and years else 1.0
    original_monthly = round(lump["monthly"] * factor, 2)
    original_psf = lump["psf"] * factor

    teaser = EXPANSION_TEASER.search(rent_text or "")
    in_teaser = False
    teaser_rate = None
    if teaser:
        teaser_rate = float(teaser.group("rate"))
        teaser_start = _as_date(teaser.group("start"))
        teaser_end = _as_date(teaser.group("end"))
        if teaser_start and teaser_end:
            in_teaser = teaser_start <= as_of_date <= teaser_end

    flags: List[str] = []
    if pct:
        flags.append(
            "Original Section 5 is a lump Base Rent, not a year-by-year schedule. "
            "Annual and monthly figures escalate that amount at the governing "
            "percentage from commencement. Confirm the original rent table if billing requires it."
        )

    if in_teaser and teaser_rate is not None:
        expansion_monthly = round(extra_rsf * teaser_rate / 12.0, 2)
        monthly = round(original_monthly + expansion_monthly, 2)
        annual = round(monthly * 12.0, 2)
        increase = (
            f" ({_money(lump['psf'])}/RSF × {1 + pct:.2f}^{years})"
            if pct and years
            else ""
        )
        formula = (
            f"{original_rsf:,} RSF original {_money(original_monthly)}/mo{increase} + "
            f"{extra_rsf:,} RSF × {_money(teaser_rate)} / RSF / year ÷ 12"
        )
    else:
        annual = round(total_rsf * original_psf, 2)
        monthly = round(annual / 12.0, 2)
        if pct and years:
            formula = (
                f"{total_rsf:,} RSF × {_money(lump['psf'])} × {1 + pct:.2f}^{years} "
                f"/ RSF / year (expansion teaser ended; same Section 5 rate as original Premises)"
            )
        else:
            formula = (
                f"{total_rsf:,} RSF × {_money(original_psf)} / RSF / year "
                "(expansion teaser ended; same Section 5 rate as original Premises)"
            )
    return {
        "review": False,
        "annual": annual,
        "monthly": monthly,
        "formula": formula,
        "flags": flags,
        "rsf": total_rsf,
        "expansion_rsf": extra_rsf,
    }


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
    commencement = _first_clause(clauses, ("Commencement Date", "Lease Commencement Date"))
    escalations = _first_clause(clauses, ("Rent Escalations",))
    premises_text = (premises or {}).get("governing_value") or ""
    rent_text = (base_rent or {}).get("governing_value") or ""
    schedule_text = (schedule or {}).get("governing_value") or ""
    rsf = _current_rsf(premises_text, rent_text, schedule_text)
    rate = _current_rate(rent_text, schedule_text)
    as_of_value = model.get("as_of") or date.today().isoformat()
    expansion_rent = _expansion_rent(
        premises_text,
        rent_text,
        (base_rent or {}).get("original_value") or "",
        (premises or {}).get("original_value") or "",
        (escalations or {}).get("governing_value") or "",
        (commencement or {}).get("governing_value") or "",
        as_of_value,
    )
    if expansion_rent and not expansion_rent.get("review"):
        # Expansion Space rate is not a whole-premises rate.
        computed_annual = expansion_rent["annual"]
        computed_monthly = expansion_rent["monthly"]
        rate = None
    else:
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

    if expansion_rent and expansion_rent.get("review"):
        flags.append(expansion_rent["reason"])
    elif _rate_scope_unclear(rent_text, expansion, premises) and not (
        expansion_rent and not expansion_rent.get("review")
    ):
        flags.append(
            "The governing rent rate does not clearly say it applies to the entire "
            "premises. Confirm whether the new rate covers all RSF or only an expansion area."
        )

    if expansion_rent and expansion_rent.get("review"):
        rows.append(
            _row(
                "Annual Base Rent",
                "Not calculated — expansion rate is not whole-premises rent",
                previous_rent,
                effective,
                STATUS_REVIEW,
                "Need original Premises rent + Expansion Space rent",
                calc_source,
                review=True,
            )
        )
    elif expansion_rent and not expansion_rent.get("review"):
        flags.extend(expansion_rent.get("flags") or [])
        rows.append(
            _row(
                "Annual Base Rent",
                _money(expansion_rent["annual"]),
                previous_rent,
                effective,
                STATUS_CALCULATED,
                expansion_rent["formula"],
                calc_source,
                "Derived calculation, not a dollar amount expressly stated in the amendment.",
            )
        )
        rows.append(
            _row(
                "Monthly Base Rent",
                _money(expansion_rent["monthly"]),
                "",
                effective,
                STATUS_CALCULATED,
                f"{expansion_rent['formula']} → {_money(expansion_rent['monthly'])}/mo",
                calc_source,
            )
        )
    elif rate and not rsf:
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
    """Build Current Position from the same full amendment chain as the Abstract."""
    from amendment_report import build_amendment_resolution_model

    resolution = build_amendment_resolution_model(
        lease,
        list(amendments or []),
        history_rows,
        as_of=as_of or date.today().isoformat(),
        prepared_for=prepared_for,
        amendment_clauses=amendment_clauses,
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
