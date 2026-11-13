"""
LeaseAI CAM reconciliation workpaper.

Produces a tenant-facing PDF that a client can send to a landlord or
accountant: billed vs allowed, calculation walkthrough, every statement
line with Allow/Challenge, and the lease terms used.
"""

from datetime import datetime
from typing import Dict, List, Optional
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import config
from cam_engine import analyze_line_items

NAVY = colors.HexColor("#1a237e")
NAVY_TEXT = colors.HexColor("#1f4788")
LIGHT_NAVY = colors.HexColor("#e8eaf6")
GREEN_BG = colors.HexColor("#e8f5e9")
GREEN_FG = colors.HexColor("#1b5e20")
RED_BG = colors.HexColor("#ffebee")
RED_FG = colors.HexColor("#b71c1c")
AMBER_BG = colors.HexColor("#fff8e1")
ROW_ALT = colors.HexColor("#f5f5f5")
GRID = colors.HexColor("#cfd8dc")
MUTED = colors.HexColor("#546e7a")

CATEGORY_LABELS = {
    "UTILITIES": "Utilities",
    "MAINTENANCE": "Maintenance",
    "REPAIRS": "Repairs",
    "INSURANCE": "Insurance",
    "PROPERTY_TAX": "Property tax",
    "MANAGEMENT_FEE": "Management fee",
    "SECURITY": "Security",
    "LANDSCAPING": "Landscaping",
    "SNOW_REMOVAL": "Snow removal",
    "JANITORIAL": "Janitorial",
    "HVAC": "HVAC",
    "ELEVATOR": "Elevator",
    "PARKING": "Parking",
    "ADMIN": "Admin",
    "OTHER": "Other",
    "CAPITAL_IMPROVEMENTS": "Capital improvements",
    "STRUCTURAL_REPAIRS": "Structural repairs",
    "ROOF_REPLACEMENT": "Roof replacement",
    "DEPRECIATION": "Depreciation",
    "DEBT_SERVICE": "Debt service",
    "MORTGAGE_PAYMENTS": "Mortgage",
    "LEGAL_FEES": "Legal fees",
}


def _xml(value) -> str:
    return (
        str(value if value is not None else "")
        .replace("−", "-")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _money(value) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _as_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _category_label(category: Optional[str]) -> str:
    raw = (category or "OTHER").strip()
    mapped = CATEGORY_LABELS.get(raw.upper().replace(" ", "_"))
    if mapped:
        return mapped
    return raw.replace("_", " ")


def _exclusion_display(provisions: Dict) -> List[str]:
    """Lease exclusion language for page 4 — one list, original casing."""
    description = (provisions.get("exclusions_description") or "").strip()
    if description:
        parts = [part.strip(" \t•-") for part in description.split(",") if part.strip(" \t•-")]
        return parts or [description]
    labels = []
    seen = set()
    for item in provisions.get("excluded_items") or []:
        label = _category_label(str(item))
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return labels


def _audit_right_label(provisions: Dict) -> str:
    if provisions.get("tenant_audit_right") is True:
        return "Yes"
    if provisions.get("tenant_audit_right") is False:
        return "Not specified" if not provisions.get("audit_deadline") else "No"
    return "Not specified"


def _cap_label(provisions: Dict) -> str:
    cap = provisions.get("cam_cap_percentage")
    has_cap = bool(provisions.get("has_cam_cap") or cap)
    if not has_cap:
        return "No yearly increase cap on file"
    cap_display = f"{cap:g}%" if cap not in (None, "") else "a set percentage"
    base = provisions.get("cam_base_amount")
    if base:
        ceiling = _as_float(base) * (1 + _as_float(cap, 0) / 100.0)
        return (
            f"Yes. Tenant CAM may not rise more than {cap_display} above the "
            f"base-year amount of {_money(base)} (ceiling {_money(ceiling)})."
        )
    return (
        f"The lease limits yearly CAM increases to {cap_display}. That limit was not "
        f"used here because the base-year tenant CAM amount (the starting number the "
        f"{cap_display} is applied to) is not on this file."
    )


def _share_pct(share) -> str:
    value = _as_float(share, None)
    if value is None:
        return "Not specified"
    if value > 1:
        value = value / 100.0
    return f"{value * 100:.2f}%"


def _sf(value) -> str:
    number = _as_float(value, None)
    if not number:
        return "Not specified"
    return f"{int(number):,}"


class CAMReconciliationPDFReport:
    """Generate a professional tenant-side CAM workpaper."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        additions = [
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=16,
                leading=20,
                textColor=NAVY,
                spaceAfter=4,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            ),
            ParagraphStyle(
                name="ReportSubtitle",
                parent=self.styles["Normal"],
                fontSize=9,
                leading=12,
                textColor=MUTED,
                spaceAfter=12,
                alignment=TA_CENTER,
            ),
            ParagraphStyle(
                name="SectionHead",
                parent=self.styles["Heading2"],
                fontSize=11,
                leading=14,
                textColor=NAVY_TEXT,
                spaceAfter=8,
                spaceBefore=14,
                fontName="Helvetica-Bold",
            ),
            ParagraphStyle(
                name="BodyNormal",
                parent=self.styles["Normal"],
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
            ),
            ParagraphStyle(
                name="FinePrint",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                textColor=MUTED,
            ),
            ParagraphStyle(
                name="TableCell",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
            ),
            ParagraphStyle(
                name="TableCellRight",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                alignment=TA_RIGHT,
            ),
            ParagraphStyle(
                name="TableCellBold",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                fontName="Helvetica-Bold",
            ),
            ParagraphStyle(
                name="HeaderCell",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                textColor=colors.white,
                fontName="Helvetica-Bold",
            ),
            ParagraphStyle(
                name="HeaderCellRight",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                textColor=colors.white,
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            ),
            ParagraphStyle(
                name="ChallengeCell",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                textColor=RED_FG,
                fontName="Helvetica-Bold",
            ),
            ParagraphStyle(
                name="AllowCell",
                parent=self.styles["Normal"],
                fontSize=8,
                leading=10,
                textColor=GREEN_FG,
                fontName="Helvetica-Bold",
            ),
        ]
        for style in additions:
            if style.name not in self.styles:
                self.styles.add(style)

    def generate_report(
        self,
        lease_data: Dict,
        reconciliation: Dict,
        line_items: List[Dict],
        cam_provisions: Dict,
        output_path: Optional[str] = None,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.65 * inch,
            leftMargin=0.65 * inch,
            topMargin=0.85 * inch,
            bottomMargin=0.7 * inch,
            title="CAM Reconciliation Workpaper",
            author=config.APP_NAME,
        )
        analyzed = self._analyzed_items(line_items, cam_provisions)
        story = []
        story.extend(self._create_cover_page(lease_data, reconciliation, analyzed, cam_provisions))
        story.append(PageBreak())
        story.extend(self._create_calculation_section(reconciliation, cam_provisions))
        story.extend(self._create_category_section(analyzed))
        story.append(PageBreak())
        story.extend(self._create_line_item_section(analyzed))
        story.append(PageBreak())
        story.extend(self._create_lease_terms_section(cam_provisions))
        story.extend(self._create_disclaimer())
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        if output_path:
            with open(output_path, "wb") as handle:
                handle.write(pdf_bytes)
        return pdf_bytes

    def _header_footer(self, canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, letter[1] - 0.48 * inch, letter[0], 0.48 * inch, fill=1, stroke=0)
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(0.65 * inch, letter[1] - 0.30 * inch, config.APP_NAME)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(
            letter[0] - 0.65 * inch,
            letter[1] - 0.30 * inch,
            "CAM Reconciliation Workpaper",
        )
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, 0, letter[0], 0.42 * inch, fill=1, stroke=0)
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawString(
            0.65 * inch,
            0.18 * inch,
            "Confidential — prepared for the tenant. Not a legal opinion.",
        )
        canvas_obj.drawRightString(
            letter[0] - 0.65 * inch,
            0.18 * inch,
            f"Page {doc.page}  |  {datetime.now().strftime('%B %d, %Y')}",
        )
        canvas_obj.restoreState()

    def _analyzed_items(self, line_items: List[Dict], cam_provisions: Dict) -> List[Dict]:
        items = line_items or []
        if items and any("should_challenge" in item for item in items):
            return items
        return analyze_line_items(items, cam_provisions or {})

    def _create_cover_page(
        self,
        lease_data: Dict,
        reconciliation: Dict,
        line_items: List[Dict],
        cam_provisions: Dict,
    ) -> List:
        billed = _as_float(reconciliation.get("landlord_tenant_share"))
        allowed = _as_float(reconciliation.get("calculated_tenant_share"))
        variance = _as_float(reconciliation.get("variance_amount"), billed - allowed)
        variance_pct = _as_float(reconciliation.get("variance_percentage"))
        if not variance_pct and billed:
            variance_pct = (variance / billed) * 100
        building_billed = _as_float(
            reconciliation.get("landlord_total_charges"),
            reconciliation.get("total_building_charges"),
        )
        excluded = _as_float(reconciliation.get("excluded_building_charges"))
        allowable = reconciliation.get("allowable_building_charges")
        if allowable in (None, ""):
            allowable = building_billed - excluded
        challenged = [item for item in line_items if item.get("should_challenge")]
        overcharged = variance > 0.01
        credited = variance < -0.01

        if abs(variance) < 100:
            status = "ACCEPT"
            status_bg = GREEN_BG
            status_fg = GREEN_FG
            status_hex = "#1b5e20"
            rec = (
                f"The billed tenant share is within $100 of the amount allowed by the lease. "
                f"Recommend accepting the {reconciliation.get('reconciliation_year', '')} true-up."
            )
        else:
            status = "CHALLENGE"
            status_bg = RED_BG
            status_fg = RED_FG
            status_hex = "#b71c1c"
            direction = "overcharge" if overcharged else "credit"
            rec = (
                f"Do not pay the {direction} of {_money(abs(variance))} until the landlord "
                f"removes lease-excluded costs and recasts the tenant share. Attach this "
                f"workpaper to the dispute letter or accountant review."
            )

        variance_label = "Overcharge" if overcharged else ("Credit due tenant" if credited else "Variance")
        elements = [
            Paragraph("CAM Reconciliation Workpaper", self.styles["ReportTitle"]),
            Paragraph(
                "Tenant-side review of the landlord's year-end common area / operating expense statement",
                self.styles["ReportSubtitle"],
            ),
            Paragraph("PURPOSE", self.styles["SectionHead"]),
            Paragraph(
                "This workpaper compares the landlord's year-end CAM statement to the CAM terms in "
                "the lease. It is prepared for the tenant to decide whether to pay, withhold, or "
                "challenge the billed true-up, and to attach to correspondence with the landlord or "
                "the tenant's accountant. Figures are taken from the uploaded statement and the "
                "extracted lease; they are not a legal opinion.",
                self.styles["BodyNormal"],
            ),
        ]

        facts = [
            self._kv("Property", lease_data.get("property_address") or "Not specified"),
            self._kv("Tenant (prepared for)", lease_data.get("tenant_name") or "Not specified"),
            self._kv("Landlord", lease_data.get("landlord_name") or "Not specified"),
            self._kv("Reconciliation year", reconciliation.get("reconciliation_year") or "Not specified"),
            self._kv("Statement date", self._statement_date(reconciliation)),
            self._kv("Report date", datetime.now().strftime("%B %d, %Y")),
        ]
        facts_table = Table(facts, colWidths=[1.7 * inch, 5.0 * inch])
        facts_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_NAVY),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(Paragraph("ENGAGEMENT FACTS", self.styles["SectionHead"]))
        elements.append(facts_table)

        elements.append(Paragraph("CONCLUSION", self.styles["SectionHead"]))
        headline = [[
            Paragraph(
                f'<font color="{status_hex}"><b>Recommendation: {status}</b></font>',
                self.styles["BodyNormal"],
            )
        ]]
        headline_table = Table(headline, colWidths=[6.7 * inch])
        headline_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("BOX", (0, 0), (-1, -1), 0.8, status_fg),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(headline_table)
        elements.append(Spacer(1, 0.08 * inch))
        elements.append(Paragraph(rec, self.styles["BodyNormal"]))
        elements.append(Spacer(1, 0.1 * inch))

        summary_header = [
            Paragraph("<b>Item</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Building</b>", self.styles["HeaderCellRight"]),
            Paragraph("<b>Tenant share</b>", self.styles["HeaderCellRight"]),
        ]
        summary_rows = [
            summary_header,
            [
                Paragraph("Landlord billed", self.styles["TableCell"]),
                Paragraph(_money(building_billed), self.styles["TableCellRight"]),
                Paragraph(_money(billed), self.styles["TableCellRight"]),
            ],
            [
                Paragraph("Lease-excluded costs removed", self.styles["TableCell"]),
                Paragraph(_money(excluded), self.styles["TableCellRight"]),
                Paragraph("—", self.styles["TableCellRight"]),
            ],
            [
                Paragraph("Allowable CAM after exclusions", self.styles["TableCellBold"]),
                Paragraph(_money(allowable), self.styles["TableCellRight"]),
                Paragraph(_money(allowed), self.styles["TableCellRight"]),
            ],
            [
                Paragraph(variance_label, self.styles["TableCellBold"]),
                Paragraph("—", self.styles["TableCellRight"]),
                Paragraph(
                    f"<b>{_money(abs(variance))}</b> ({abs(variance_pct):.1f}%)",
                    self.styles["TableCellRight"],
                ),
            ],
        ]
        summary = Table(summary_rows, colWidths=[3.3 * inch, 1.7 * inch, 1.7 * inch])
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BACKGROUND", (0, -1), (-1, -1), RED_BG if overcharged else GREEN_BG),
            ("GRID", (0, 0), (-1, -1), 0.4, GRID),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, ROW_ALT]),
        ]))
        elements.append(summary)

        findings = [
            f"{len(line_items)} statement lines reviewed; {len(challenged)} flagged as excluded by the lease."
        ]
        if excluded:
            findings.append(
                f"Excluded building costs of {_money(excluded)} are not CAM and are stripped "
                f"before applying the tenant's {_share_pct(cam_provisions.get('tenant_prorata_share'))} share."
            )
        if reconciliation.get("cam_cap_applied"):
            findings.append(
                "The annual increase cap binds after exclusions and reduces the tenant share further."
            )
        elif cam_provisions.get("has_cam_cap") or cam_provisions.get("cam_cap_percentage"):
            cap = cam_provisions.get("cam_cap_percentage")
            cap_display = f"{cap:g}%" if cap not in (None, "") else "a set percentage"
            if cam_provisions.get("cam_base_amount"):
                findings.append(
                    f"The lease limits yearly CAM increases to {cap_display} above the "
                    f"base-year tenant CAM amount. The allowed share is under that ceiling, "
                    f"so the cap does not change this year's total."
                )
            else:
                findings.append(
                    f"The lease limits yearly CAM increases to {cap_display}. That limit "
                    f"was not used because the base-year tenant CAM amount is not on this "
                    f"file. The overcharge is from lease-excluded costs, then the tenant's share."
                )
        elements.append(Paragraph("KEY FINDINGS", self.styles["SectionHead"]))
        for finding in findings:
            elements.append(Paragraph(f"- {finding}", self.styles["BodyNormal"]))
        return elements

    def _create_calculation_section(self, reconciliation: Dict, cam_provisions: Dict) -> List:
        elements = [Paragraph("HOW THE TENANT SHARE WAS CALCULATED", self.styles["SectionHead"])]
        elements.append(Paragraph(
            "LeaseAI applies the lease in this order: drop excluded building costs, multiply "
            "the remainder by the tenant's share of the building, then apply any CAM stop or "
            "yearly increase cap. A yearly cap is measured against the base-year tenant CAM "
            "amount, never against this year's billed share.",
            self.styles["BodyNormal"],
        ))
        elements.append(Spacer(1, 0.08 * inch))
        steps = list(reconciliation.get("calculations") or [])
        if not steps:
            billed_building = _as_float(reconciliation.get("landlord_total_charges"))
            excluded = _as_float(reconciliation.get("excluded_building_charges"))
            allowable = _as_float(
                reconciliation.get("allowable_building_charges"),
                billed_building - excluded,
            )
            share = _share_pct(cam_provisions.get("tenant_prorata_share"))
            steps = [
                {
                    "step": "Excluded costs removed from building total",
                    "formula": f"{_money(billed_building)} − {_money(excluded)}",
                    "result": allowable,
                },
                {
                    "step": "Pro-rata calculation",
                    "formula": f"{_money(allowable)} × {share}",
                    "result": reconciliation.get("calculated_tenant_share"),
                },
            ]
        header = [
            Paragraph("<b>#</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Step</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Formula</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Result</b>", self.styles["HeaderCellRight"]),
        ]
        rows = [header]
        for index, step in enumerate(steps, 1):
            rows.append([
                Paragraph(str(index), self.styles["TableCell"]),
                Paragraph(_xml(step.get("step")), self.styles["TableCell"]),
                Paragraph(_xml(step.get("formula")), self.styles["TableCell"]),
                Paragraph(_money(step.get("result")), self.styles["TableCellRight"]),
            ])
        table = Table(rows, colWidths=[0.35 * inch, 2.4 * inch, 2.7 * inch, 1.25 * inch])
        table.setStyle(self._grid_style(len(rows)))
        return [KeepTogether(elements + [table])]

    def _create_category_section(self, line_items: List[Dict]) -> List:
        if not line_items:
            return []
        buckets: Dict[str, Dict] = {}
        for item in line_items:
            label = _category_label(item.get("category"))
            bucket = buckets.setdefault(label, {"amount": 0.0, "challenged": 0.0, "count": 0})
            amount = _as_float(item.get("amount", item.get("landlord_amount")))
            bucket["amount"] += amount
            bucket["count"] += 1
            if item.get("should_challenge"):
                bucket["challenged"] += amount
        elements = [Paragraph("CATEGORY ROLLFORWARD", self.styles["SectionHead"])]
        header = [
            Paragraph("<b>Category</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Billed</b>", self.styles["HeaderCellRight"]),
            Paragraph("<b>Challenged</b>", self.styles["HeaderCellRight"]),
            Paragraph("<b>Allowed</b>", self.styles["HeaderCellRight"]),
        ]
        rows = [header]
        for label in sorted(buckets, key=lambda key: buckets[key]["challenged"], reverse=True):
            data = buckets[label]
            allowed = data["amount"] - data["challenged"]
            rows.append([
                Paragraph(_xml(label), self.styles["TableCell"]),
                Paragraph(_money(data["amount"]), self.styles["TableCellRight"]),
                Paragraph(_money(data["challenged"]), self.styles["TableCellRight"]),
                Paragraph(_money(allowed), self.styles["TableCellRight"]),
            ])
        table = Table(rows, colWidths=[2.5 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])
        table.setStyle(self._grid_style(len(rows)))
        elements.append(table)
        return elements

    def _create_line_item_section(self, line_items: List[Dict]) -> List:
        elements = [Paragraph("STATEMENT LINE ITEMS", self.styles["SectionHead"])]
        if not line_items:
            elements.append(Paragraph(
                "No line items were parsed from the landlord statement. Upload the year-end "
                "CAM PDF and parse it before generating this workpaper.",
                self.styles["BodyNormal"],
            ))
            return elements
        elements.append(Paragraph(
            f"All {len(line_items)} numbered lines from the landlord statement are listed. "
            "Challenge means the lease excludes that cost from CAM; Allow means it remains in "
            "the building pool used for the tenant share.",
            self.styles["BodyNormal"],
        ))
        elements.append(Spacer(1, 0.08 * inch))
        header = [
            Paragraph("<b>#</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Description</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Category</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Landlord amount</b>", self.styles["HeaderCellRight"]),
            Paragraph("<b>Flag</b>", self.styles["HeaderCell"]),
            Paragraph("<b>Reason</b>", self.styles["HeaderCell"]),
        ]
        rows = [header]
        challenge_rows = []
        for offset, item in enumerate(line_items, 1):
            challenge = bool(item.get("should_challenge"))
            flag_style = self.styles["ChallengeCell"] if challenge else self.styles["AllowCell"]
            reason = item.get("dispute_reason") or item.get("notes") or ("Excluded per lease" if challenge else "Included in CAM")
            line_no = item.get("line_number") or offset
            rows.append([
                Paragraph(_xml(line_no), self.styles["TableCell"]),
                Paragraph(_xml(item.get("description") or "Untitled"), self.styles["TableCell"]),
                Paragraph(_xml(_category_label(item.get("category"))), self.styles["TableCell"]),
                Paragraph(_money(item.get("amount", item.get("landlord_amount"))), self.styles["TableCellRight"]),
                Paragraph("Challenge" if challenge else "Allow", flag_style),
                Paragraph(_xml(reason), self.styles["TableCell"]),
            ])
            if challenge:
                challenge_rows.append(offset)
        table = Table(
            rows,
            colWidths=[0.35 * inch, 1.9 * inch, 1.15 * inch, 1.15 * inch, 0.8 * inch, 1.35 * inch],
            repeatRows=1,
        )
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ]
        for row_index in challenge_rows:
            style_commands.append(("BACKGROUND", (0, row_index), (-1, row_index), RED_BG))
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        return elements

    def _create_lease_terms_section(self, cam_provisions: Dict) -> List:
        provisions = cam_provisions or {}
        tenant_sf = _sf(provisions.get("tenant_square_footage"))
        building_sf = _sf(provisions.get("building_square_footage"))
        terms = [
            self._kv("CAM Base Year", provisions.get("cam_base_year") or "Not specified"),
            self._kv(
                "CAM Base Amount (tenant share)",
                _money(provisions.get("cam_base_amount")) if provisions.get("cam_base_amount") else "Not specified",
            ),
            self._kv("Tenant pro-rata share", _share_pct(provisions.get("tenant_prorata_share"))),
            self._kv("Premises / building RSF", f"{tenant_sf} / {building_sf}"),
            self._kv("CAM cap", _cap_label(provisions)),
            self._kv(
                "CAM stop",
                _money(provisions.get("cam_stop_amount")) if provisions.get("cam_stop_amount") else "None",
            ),
            self._kv("Tenant audit right", _audit_right_label(provisions)),
            self._kv("Audit deadline", provisions.get("audit_deadline") or "Not specified"),
        ]
        table = Table(terms, colWidths=[2.3 * inch, 4.4 * inch])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_NAVY),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements = [
            Paragraph("LEASE TERMS APPLIED", self.styles["SectionHead"]),
            Paragraph(
                "These are the CAM terms LeaseAI used. Blank fields were not stored on the "
                "lease abstract; the workpaper does not invent them, except deriving share "
                "from RSF when the percentage was missing.",
                self.styles["BodyNormal"],
            ),
            Spacer(1, 0.06 * inch),
            table,
        ]
        exclusion_lines = _exclusion_display(provisions)
        if exclusion_lines:
            elements.append(Paragraph("EXCLUSIONS IN THE LEASE", self.styles["SectionHead"]))
            elements.append(Paragraph(
                "Costs the lease removes from the CAM pool before the tenant share is calculated:",
                self.styles["BodyNormal"],
            ))
            for item in exclusion_lines:
                elements.append(Paragraph(f"- {_xml(item)}", self.styles["BodyNormal"]))
        return elements

    def _create_disclaimer(self) -> List:
        return [
            Paragraph("USE OF THIS WORKPAPER", self.styles["SectionHead"]),
            Paragraph(
                "This document is a calculation workpaper, not a legal opinion and not a substitute "
                "for counsel. Send it with a dispute letter when the recommendation is CHALLENGE. "
                "The tenant should confirm that the uploaded statement is complete and that the "
                "lease abstract used for exclusions, share, and cap is current.",
                self.styles["FinePrint"],
            ),
        ]

    def _kv(self, label: str, value) -> List:
        return [
            Paragraph(f"<b>{_xml(label)}</b>", self.styles["TableCell"]),
            Paragraph(_xml(value), self.styles["TableCell"]),
        ]

    def _statement_date(self, reconciliation: Dict) -> str:
        raw = reconciliation.get("statement_date")
        if hasattr(raw, "strftime"):
            return raw.strftime("%B %d, %Y")
        if isinstance(raw, str) and raw:
            try:
                return datetime.fromisoformat(raw[:10]).strftime("%B %d, %Y")
            except ValueError:
                return raw
        return "Not specified"

    def _grid_style(self, row_count: int) -> TableStyle:
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ])


def generate_cam_pdf_report(
    lease_data: Dict,
    reconciliation: Dict,
    line_items: List[Dict],
    cam_provisions: Dict,
    output_path: Optional[str] = None,
) -> bytes:
    """Generate the tenant CAM workpaper PDF."""
    generator = CAMReconciliationPDFReport()
    return generator.generate_report(
        lease_data or {},
        reconciliation or {},
        line_items or [],
        cam_provisions or {},
        output_path,
    )


def cam_report_filename(lease_data: Dict, year) -> str:
    property_name = (lease_data or {}).get("property_address") or "Property"
    slug = "".join(ch if ch.isalnum() else "_" for ch in property_name)[:40].strip("_")
    return f"CAM_Reconciliation_{slug}_{year}.pdf"
