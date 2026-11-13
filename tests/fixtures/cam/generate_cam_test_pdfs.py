#!/usr/bin/env python3
"""Generate the synthetic CAM lease + statement PDF pairs."""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenario  # noqa: E402
import scenario_ironwood  # noqa: E402


NAVY = colors.HexColor("#1a365d")
SLATE = colors.HexColor("#4a5568")
LIGHT = colors.HexColor("#edf2f7")
RULE = colors.HexColor("#cbd5e0")
RED = colors.HexColor("#9b2c2c")
GREEN = colors.HexColor("#276749")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Banner",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Times-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=NAVY,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="DocSub",
        fontName="Times-Italic",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=SLATE,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Article",
        fontName="Times-Bold",
        fontSize=12,
        leading=16,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Clause",
        fontName="Times-Roman",
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="CenterSmall",
        fontName="Times-Roman",
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Letterhead",
        fontName="Times-Bold",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=NAVY,
    ))
    styles.add(ParagraphStyle(
        name="LetterSub",
        fontName="Times-Roman",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=SLATE,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="BodyLeft",
        fontName="Times-Roman",
        fontSize=10,
        leading=13,
        alignment=TA_LEFT,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Times-Roman",
        fontSize=8.5,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        name="TableHead",
        fontName="Times-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="MoneyRight",
        fontName="Times-Roman",
        fontSize=8.5,
        leading=11,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="FlagNote",
        fontName="Times-Italic",
        fontSize=9,
        leading=12,
        textColor=RED,
        spaceBefore=4,
        spaceAfter=8,
    ))
    return styles


def _category_label(category: str) -> str:
    labels = {
        "UTILITIES": "Utilities",
        "JANITORIAL": "Janitorial",
        "HVAC": "HVAC",
        "ELEVATOR": "Elevator",
        "LANDSCAPING": "Landscaping",
        "SNOW_REMOVAL": "Snow removal",
        "SECURITY": "Security",
        "PARKING": "Parking",
        "INSURANCE": "Insurance",
        "MANAGEMENT_FEE": "Management fee",
        "MAINTENANCE": "Maintenance",
        "CAPITAL_IMPROVEMENTS": "Capital improvements",
        "STRUCTURAL_REPAIRS": "Structural repairs",
        "ROOF_REPLACEMENT": "Roof replacement",
        "LEGAL_FEES": "Legal fees",
        "DEPRECIATION": "Depreciation",
        "DEBT_SERVICE": "Debt service",
    }
    return labels.get(category, category.replace("_", " ").title())


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _banner(styles, label: str):
    table = Table(
        [[Paragraph(_escape(label), styles["Banner"])]],
        colWidths=[7.0 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RED),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return table


def _footer(canvas, doc, footer_text: str):
    canvas.saveState()
    canvas.setFillColor(RED)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(
        letter[0] / 2,
        0.45 * inch,
        "SYNTHETIC TEST DOCUMENT — FICTIONAL PARTIES — NOT A REAL LEASE OR INVOICE",
    )
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.75 * inch, 0.28 * inch, footer_text)
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.28 * inch, f"Page {doc.page}")
    canvas.restoreState()


DEFAULT_BASE_RENT_CLAUSES = [
    "4.1 Base Rent Schedule. Base Rent is calculated at Forty-Two and 00/100 "
    "Dollars ($42.00) per rentable square foot per year for Year 1, with a "
    "fixed three percent (3%) Annual Escalation Type (Fixed / CPI / Percentage) "
    "and Annual Escalation Rate or Cap of 3%. CPI Index Used: not applicable. "
    "Percentage Rent Clause: none. Gross Revenue Breakpoint: not applicable.",
    "Base Rent Year 1 (monthly): $43,750.00. "
    "Base Rent Year 2 (monthly): $45,062.50. "
    "Base Rent Year 3 (monthly): $46,414.38. "
    "Base Rent Year 4 (monthly): $47,806.81. "
    "Base Rent Year 5 (monthly): $49,241.01. "
    "Full Rent Schedule (all years): Year 1 $525,000.00; Year 2 $540,750.00; "
    "Year 3 $556,972.50; Year 4 $573,681.68; Year 5 $590,892.13.",
]

DEFAULT_SECURITY_CLAUSES = [
    "5.1 Security Deposit Amount: $87,500.00 (two months of Year 1 Base Rent). "
    "Security Deposit — Letter of Credit: not required. "
    "Security Deposit Reduction Schedule: none.",
    "5.2 Parking — Number of Stalls: 25 unreserved stalls. "
    "Parking — Monthly Cost per Stall: $150.00. Storage Space Included: none. "
    "Signage Rights: Tenant may place suite-entry signage; no exterior building "
    "signage without Landlord’s prior written consent. "
    "Roof / Exterior Access Rights: none except as required for Tenant’s "
    "permitted telecommunications equipment, subject to Landlord approval.",
]

DEFAULT_USE_CLAUSES = [
    "6.1 Permitted Use: general office use for a software analytics company "
    "and uses incidental thereto. Prohibited Uses / Exclusivity Clause: "
    "no retail, medical clinic, or industrial use. Co-Tenancy Clause: none.",
    "6.2 Subletting / Assignment Rights: Tenant may assign or sublet with "
    "Landlord’s prior written consent, not to be unreasonably withheld. "
    "Subletting — Landlord Consent Required: Yes.",
    "6.3 Tenant Improvement Allowance (TIA): $40.00 per RSF, equal to "
    "$500,000.00. TIA Conditions / Milestones: paid upon substantial "
    "completion of Tenant’s initial improvements and delivery of lien waivers. "
    "Alterations — Landlord Consent Threshold: any alteration exceeding "
    "$25,000.00 requires Landlord consent. "
    "ADA / Accessibility Compliance Responsibility: Landlord as to the "
    "Building common areas; Tenant as to the Premises.",
]

DEFAULT_TAX_CLAUSES = [
    "8.1 Property Tax Responsibility: included in Operating Expenses except "
    "to the extent listed as a CAM Exclusion. Property Insurance "
    "Responsibility: Landlord carries building insurance, included in "
    "Operating Expenses. Tenant Insurance Requirements: commercial general "
    "liability and property insurance covering Tenant’s contents. "
    "Tenant Liability Insurance Minimum: $2,000,000 per occurrence.",
    "8.2 Utilities Responsibility: Tenant pays electricity serving the "
    "Premises directly; common-area utilities are CAM. HVAC Responsibility "
    "(Landlord / Tenant): Landlord. HVAC Maintenance Obligation: Landlord, "
    "as a CAM expense for routine maintenance. Janitorial Responsibility: "
    "Landlord for common areas (CAM); Tenant for the Premises. "
    "Structural / Roof Repair Responsibility: Landlord, and such costs are "
    "CAM Exclusions (not pass-through).",
]

DEFAULT_RENEWAL_CLAUSES = [
    "9.1 Number of Renewal Options: two (2). Renewal Option Term Length: "
    "five (5) years each. Renewal Notice Deadline: twelve (12) months prior "
    "to the then-current expiration. Renewal Rent Basis (FMV / Fixed / CPI): "
    "Fair Market Value (FMV). Right of First Refusal: none. Right of First "
    "Offer: none. Expansion Option: none. Contraction / Reduction Option: none.",
    "9.2 Early Termination Right: none. Termination Notice Period: not "
    "applicable. Early Termination Fee / Penalty: not applicable.",
]


def build_lease(output_path: Path, S) -> None:
    styles = _styles()
    doc_kind = getattr(S, "DOC_KIND", "OFFICE LEASE AGREEMENT")
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"{doc_kind} — {S.PROPERTY_NAME} (Synthetic Test)",
        author="LeaseAI test fixtures",
    )
    story = []
    story.append(_banner(
        styles,
        "SYNTHETIC TEST DOCUMENT  ·  FICTIONAL PARTIES  ·  FOR LEASEAI CAM TESTING ONLY",
    ))
    story.append(Spacer(1, 14))
    story.append(Paragraph(_escape(doc_kind), styles["DocTitle"]))
    story.append(Paragraph(S.PROPERTY_NAME, styles["DocSub"]))
    story.append(Paragraph(_escape(S.PROPERTY_ADDRESS), styles["CenterSmall"]))
    story.append(Paragraph(f"{S.SUITE}, Floor {S.FLOOR}", styles["CenterSmall"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"This {doc_kind.title()} (the “Lease”) is entered into as of "
        f"{S.COMMENCEMENT_DATE} by and between <b>{_escape(S.LANDLORD_NAME)}</b> "
        f"(“Landlord”) and <b>{_escape(S.TENANT_NAME)}</b>, doing business as "
        f"{_escape(S.TENANT_TRADE_NAME)} (“Tenant”).",
        styles["Clause"],
    ))

    articles = [
        (
            "ARTICLE 1 — PARTIES AND NOTICE",
            [
                f"1.1 Landlord Legal Name. The Landlord Legal Name is {S.LANDLORD_NAME}. "
                f"The Landlord Registered Address and Landlord Contact / Notice Address is "
                f"{S.LANDLORD_NOTICE}.",
                f"1.2 Tenant Legal Name. The Tenant Legal Name is {S.TENANT_NAME}. "
                f"The Tenant Trade Name is {S.TENANT_TRADE_NAME}. The Tenant Registered "
                f"Address is {S.PROPERTY_ADDRESS}, {S.SUITE}. There is no Guarantor. "
                f"Guarantor Name(s): none.",
            ],
        ),
        (
            "ARTICLE 2 — PREMISES AND PROPERTY",
            [
                f"2.1 Property Civic Address. The Property Civic Address is "
                f"{S.PROPERTY_ADDRESS}, commonly known as {S.PROPERTY_NAME}. "
                f"The Property Legal Description is: {S.LEGAL_DESCRIPTION}. "
                f"Building Class: {S.BUILDING_CLASS}.",
                f"2.2 Premises. Landlord leases to Tenant {S.SUITE} on Floor {S.FLOOR} "
                f"(Floor(s) Occupied: {S.FLOOR}; Suite / Unit Number: {S.SUITE}). "
                f"The Premises Square Footage (RSF) is {S.PREMISES_RSF:,} rentable square feet. "
                f"The Building Total Square Footage is {S.BUILDING_RSF:,} rentable square feet. "
                f"Building Square Footage: {S.BUILDING_RSF:,} RSF.",
            ],
        ),
        (
            "ARTICLE 3 — TERM",
            [
                f"3.1 Lease Type. This is a {S.LEASE_TYPE} lease. "
                f"{getattr(S, 'LEASE_TYPE_DETAIL', '')}".strip(),
                f"3.2 Dates. Lease Commencement Date: {S.COMMENCEMENT_DATE}. "
                f"Rent Commencement Date: {S.RENT_COMMENCEMENT_DATE}. "
                f"Lease Expiration Date: {S.EXPIRATION_DATE}. "
                f"Lease Term (Total Months): {S.TERM_MONTHS} months. "
                f"Free Rent Period (months): 0 (none).",
            ],
        ),
        (
            "ARTICLE 4 — BASE RENT",
            getattr(S, "BASE_RENT_CLAUSES", DEFAULT_BASE_RENT_CLAUSES),
        ),
        (
            "ARTICLE 5 — SECURITY DEPOSIT AND PARKING",
            getattr(S, "SECURITY_CLAUSES", DEFAULT_SECURITY_CLAUSES),
        ),
        (
            "ARTICLE 6 — USE, ASSIGNMENT, AND IMPROVEMENTS",
            getattr(S, "USE_CLAUSES", DEFAULT_USE_CLAUSES),
        ),
        (
            "ARTICLE 7 — OPERATING EXPENSES AND CAM / OPERATING COST CHARGES",
            [
                f"7.1 Base Year for Operating Expenses. The Base Year for Operating "
                f"Expenses and the CAM Base Year is calendar year {S.CAM_BASE_YEAR}. "
                f"There is no Operating Expense Stop Amount and no CAM Stop Amount "
                f"under this Lease (CAM Stop Amount: none / not applicable).",
                f"7.2 Tenant’s Pro-Rata Share. Tenant’s Premises Square Footage (RSF) is "
                f"{S.PREMISES_RSF:,} and the Building Total Square Footage / Building "
                f"Square Footage is {S.BUILDING_RSF:,}. Tenant’s pro-rata share of CAM / "
                f"Operating Cost Charges is {S.TENANT_PRORATA_PERCENT:.2f}% "
                f"({S.PREMISES_RSF:,} ÷ {S.BUILDING_RSF:,} = {S.TENANT_PRORATA_SHARE:.4f}).",
                f"7.3 CAM Base Amount. Tenant’s CAM Base Amount for CAM Base Year "
                f"{S.CAM_BASE_YEAR} is {S.money(S.CAM_BASE_AMOUNT)}.",
                f"7.4 CAM Annual Increase Cap (%). Tenant’s CAM / Operating Cost Charges "
                f"for any calendar year after the Base Year are subject to a CAM Annual "
                f"Increase Cap (%) / CAM Escalation Cap of {S.CAM_CAP_PERCENTAGE_WORDS} of the CAM "
                f"Base Amount. The CAM cap percentage is {S.CAM_CAP_PERCENTAGE:.1f}%. "
                f"The maximum Tenant CAM charge in any year is therefore "
                f"{S.money(S.CAP_CEILING)} (being the CAM Base Amount of "
                f"{S.money(S.CAM_BASE_AMOUNT)} plus {S.CAM_CAP_PERCENTAGE:.0f}%). Has CAM Cap: Yes.",
                f"7.5 CAM Exclusions. {S.CAM_EXCLUSIONS_CLAUSE}",
                f"7.6 Payment and Reconciliation. CAM Payment Frequency: {S.CAM_PAYMENT_FREQUENCY}. "
                f"Tenant shall pay estimated CAM monthly together with Base Rent. "
                f"Landlord shall deliver an annual CAM reconciliation statement "
                f"{S.RECONCILIATION_DEADLINE.lower()}.",
                f"7.7 Tenant Audit Right. Tenant Audit Right: Yes. Tenant is ALLOWED to "
                f"audit Landlord’s books and records relating to Operating Expenses. "
                f"Audit Deadline: {S.AUDIT_DEADLINE}.",
            ],
        ),
        (
            "ARTICLE 8 — TAXES, INSURANCE, UTILITIES, AND MAINTENANCE",
            getattr(S, "TAX_CLAUSES", DEFAULT_TAX_CLAUSES),
        ),
        (
            "ARTICLE 9 — RENEWAL, EXPANSION, AND TERMINATION",
            getattr(S, "RENEWAL_CLAUSES", DEFAULT_RENEWAL_CLAUSES),
        ),
        (
            "ARTICLE 10 — LEGAL AND COMPLIANCE",
            [
                f"10.1 Hazardous Materials Clause: Tenant shall not introduce hazardous "
                f"materials except customary office products. Governing Law Jurisdiction: "
                f"{S.GOVERNING_LAW}. SNDA Agreement Required: Yes, Landlord shall use "
                f"commercially reasonable efforts to obtain an SNDA from any mortgagee. "
                f"Estoppel Certificate Obligation: Tenant shall execute an estoppel "
                f"within fifteen (15) days after request.",
                "10.2 Force Majeure Clause: neither party is liable for delay caused by "
                "events beyond its reasonable control. Dispute Resolution Mechanism: "
                f"state court in {S.DISPUTE_VENUE}; mediation required before "
                "litigation. Holdover Provision (rate & notice): 150% of then-current "
                "Base Rent, month-to-month. Demolition / Redevelopment Clause: none.",
                "10.3 Default Cure Period (Tenant): ten (10) days for monetary default; "
                "thirty (30) days for non-monetary default. Default Cure Period "
                "(Landlord): thirty (30) days.",
            ],
        ),
    ]

    for title, clauses in articles:
        story.append(Paragraph(_escape(title), styles["Article"]))
        for clause in clauses:
            story.append(Paragraph(_escape(clause), styles["Clause"]))

    story.append(Paragraph("ARTICLE 11 — SIGNATURES", styles["Article"]))
    story.append(Paragraph(
        "IN WITNESS WHEREOF, Landlord and Tenant have executed this Lease as of the "
        "date first written above.",
        styles["Clause"],
    ))
    sig = [
        [
            Paragraph(f"<b>LANDLORD</b><br/>{_escape(S.LANDLORD_NAME)}<br/><br/>"
                      f"By: ___________________________<br/>"
                      f"Name: {_escape(S.LANDLORD_SIGNER)}<br/>"
                      f"Date: {S.COMMENCEMENT_DATE}", styles["BodyLeft"]),
            Paragraph(f"<b>TENANT</b><br/>{_escape(S.TENANT_NAME)}<br/><br/>"
                      f"By: ___________________________<br/>"
                      f"Name: {_escape(S.TENANT_SIGNER)}<br/>"
                      f"Date: {S.COMMENCEMENT_DATE}", styles["BodyLeft"]),
        ]
    ]
    sig_table = Table(sig, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(sig_table)

    doc.build(
        story,
        onFirstPage=lambda c, d: _footer(c, d, S.PROPERTY_NAME),
        onLaterPages=lambda c, d: _footer(c, d, S.PROPERTY_NAME),
    )


def _line_row(styles, scenario_mod, number, description, category, amount, flag=False):
    color_style = "FlagNote" if flag else "TableCell"
    return [
        Paragraph(str(number), styles["TableCell"]),
        Paragraph(_escape(description), styles[color_style] if flag else styles["TableCell"]),
        Paragraph(_category_label(category), styles["TableCell"]),
        Paragraph(scenario_mod.money(amount), styles["MoneyRight"]),
    ]


def build_statement(output_path: Path, S) -> None:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title=f"{S.RECONCILIATION_YEAR} Annual CAM Reconciliation Statement (Synthetic Test)",
        author="LeaseAI test fixtures",
    )
    story = []
    story.append(_banner(
        styles,
        "SYNTHETIC TEST DOCUMENT  ·  FICTIONAL LANDLORD  ·  FOR LEASEAI CAM TESTING ONLY",
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(_escape(S.LANDLORD_NAME), styles["Letterhead"]))
    story.append(Paragraph(
        f"{_escape(S.LANDLORD_NOTICE)}<br/>Accounting / CAM Reconciliations",
        styles["LetterSub"],
    ))
    story.append(Paragraph(
        "ANNUAL OPERATING EXPENSE / CAM RECONCILIATION STATEMENT",
        styles["DocTitle"],
    ))
    story.append(Paragraph(
        f"Calendar Year {S.RECONCILIATION_YEAR}  ·  Statement Date: {S.STATEMENT_DATE}",
        styles["DocSub"],
    ))

    header_info = [
        [Paragraph("<b>Property</b>", styles["TableCell"]),
         Paragraph(_escape(f"{S.PROPERTY_NAME}, {S.PROPERTY_ADDRESS}"), styles["TableCell"])],
        [Paragraph("<b>Tenant</b>", styles["TableCell"]),
         Paragraph(_escape(f"{S.TENANT_NAME} ({S.SUITE})"), styles["TableCell"])],
        [Paragraph("<b>Period</b>", styles["TableCell"]),
         Paragraph(_escape(S.STATEMENT_PERIOD), styles["TableCell"])],
        [Paragraph("<b>Premises RSF</b>", styles["TableCell"]),
         Paragraph(f"{S.PREMISES_RSF:,} RSF", styles["TableCell"])],
        [Paragraph("<b>Building RSF</b>", styles["TableCell"]),
         Paragraph(f"{S.BUILDING_RSF:,} RSF", styles["TableCell"])],
        [Paragraph("<b>Tenant Pro-Rata Share</b>", styles["TableCell"]),
         Paragraph(f"{S.TENANT_PRORATA_PERCENT:.2f}%", styles["TableCell"])],
    ]
    info = Table(header_info, colWidths=[1.8 * inch, 5.4 * inch])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info)
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f"Dear {S.TENANT_TRADE_NAME} Accounts Payable:",
        styles["BodyLeft"],
    ))
    story.append(Paragraph(
        f"Enclosed is the {S.RECONCILIATION_YEAR} annual CAM / operating-expense "
        f"reconciliation for your premises at {S.PROPERTY_NAME}. Total building "
        f"operating expenses for the year are {S.money(S.BUILDING_TOTAL_CHARGES)}. "
        f"Your {S.TENANT_PRORATA_PERCENT:.2f}% tenant share billed is "
        f"{S.money(S.TENANT_SHARE_BILLED)}. Estimated CAM paid during {S.RECONCILIATION_YEAR} "
        f"was {S.money(S.ESTIMATED_CAM_PAID)}. Balance due: {S.money(S.BALANCE_DUE_BILLED)}.",
        styles["Clause"],
    ))

    story.append(Paragraph("BUILDING OPERATING EXPENSE DETAIL", styles["Article"]))

    header = [
        Paragraph("#", styles["TableHead"]),
        Paragraph("Description", styles["TableHead"]),
        Paragraph("Category", styles["TableHead"]),
        Paragraph("Amount", styles["TableHead"]),
    ]
    rows = [header]
    line_no = 1
    for description, category, amount in S.ALLOWABLE_LINE_ITEMS:
        rows.append(_line_row(styles, S, line_no, description, category, amount, flag=False))
        line_no += 1
    for description, category, amount in S.EXCLUDED_LINE_ITEMS:
        rows.append(_line_row(styles, S, line_no, description, category, amount, flag=True))
        line_no += 1

    rows.append([
        Paragraph("", styles["TableCell"]),
        Paragraph("<b>Total Building CAM Charges</b>", styles["TableCell"]),
        Paragraph("", styles["TableCell"]),
        Paragraph(f"<b>{S.money(S.BUILDING_TOTAL_CHARGES)}</b>", styles["MoneyRight"]),
    ])

    table = Table(rows, colWidths=[0.4 * inch, 4.3 * inch, 1.5 * inch, 1.1 * inch])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.3, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
    ]
    first_excluded_row = 1 + len(S.ALLOWABLE_LINE_ITEMS)
    last_excluded_row = first_excluded_row + len(S.EXCLUDED_LINE_ITEMS) - 1
    style_cmds.append(
        ("BACKGROUND", (0, first_excluded_row), (-1, last_excluded_row), colors.HexColor("#fff5f5"))
    )
    table.setStyle(TableStyle(style_cmds))
    story.append(table)
    story.append(Paragraph(
        "Italicized / shaded rows are capital, structural, legal, depreciation, or debt-service "
        "items. They are included in this landlord statement on purpose so LeaseAI can flag them "
        "against the lease CAM Exclusions.",
        styles["FlagNote"],
    ))

    story.append(Paragraph("TENANT SHARE SUMMARY", styles["Article"]))
    summary = [
        [Paragraph("<b>Item</b>", styles["TableHead"]),
         Paragraph("<b>Amount</b>", styles["TableHead"])],
        [Paragraph("Total Building Charges (from CAM statement)", styles["TableCell"]),
         Paragraph(S.money(S.BUILDING_TOTAL_CHARGES), styles["MoneyRight"])],
        [Paragraph(
            f"Tenant Share Billed ({S.TENANT_PRORATA_PERCENT:.2f}% of building total)",
            styles["TableCell"],
        ),
         Paragraph(S.money(S.TENANT_SHARE_BILLED), styles["MoneyRight"])],
        [Paragraph(
            f"Less: estimated CAM paid in {S.RECONCILIATION_YEAR} "
            f"({S.money(S.ESTIMATED_MONTHLY)} × 12)",
            styles["TableCell"],
        ),
         Paragraph(S.money(S.ESTIMATED_CAM_PAID), styles["MoneyRight"])],
        [Paragraph("<b>Balance Due from Tenant</b>", styles["TableCell"]),
         Paragraph(f"<b>{S.money(S.BALANCE_DUE_BILLED)}</b>", styles["MoneyRight"])],
    ]
    summary_table = Table(summary, colWidths=[5.5 * inch, 1.8 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fff5f5")),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Please remit the balance due within thirty (30) days of the statement date. "
        f"Questions may be directed to CAM Accounting at {_escape(S.LANDLORD_NAME)}.",
        styles["Clause"],
    ))
    story.append(Paragraph(
        f"Sincerely,<br/><br/>{_escape(S.ACCOUNTING_SIGNER)}<br/>"
        f"{_escape(S.ACCOUNTING_TITLE)}<br/>"
        f"{_escape(S.LANDLORD_NAME)}",
        styles["BodyLeft"],
    ))

    doc.build(
        story,
        onFirstPage=lambda c, d: _footer(c, d, f"{S.PROPERTY_NAME} CAM {S.RECONCILIATION_YEAR}"),
        onLaterPages=lambda c, d: _footer(c, d, f"{S.PROPERTY_NAME} CAM {S.RECONCILIATION_YEAR}"),
    )


def main() -> None:
    for S in (scenario, scenario_ironwood):
        S.FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        build_lease(S.LEASE_PDF, S)
        build_statement(S.STATEMENT_PDF, S)
        print(f"Wrote {S.LEASE_PDF}")
        print(f"Wrote {S.STATEMENT_PDF}")
        print(
            f"Expected: billed {S.money(S.TENANT_SHARE_BILLED)} vs "
            f"calculated {S.money(S.CALCULATED_TENANT_SHARE)} "
            f"({S.money(S.VARIANCE_OVERCHARGE)} overcharge)"
        )


if __name__ == "__main__":
    main()
