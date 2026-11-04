"""Client-facing ASC 842 / IFRS 16 compliance report."""

from __future__ import annotations

import html
import io
import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config
from asc842_engine import ASC842ComplianceEngine
from lease_report import _header_footer

REPORT_STATEMENT = (
    "This compliance report states the ASC 842 / IFRS 16 measurement of the selected "
    "lease: classification, initial Right-of-Use asset and lease liability, amortization "
    "schedules, journal entries, and the quantitative disclosures a controller files "
    "with the financial statements."
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pdf_text(value: Any, limit: int = 1200) -> str:
    text = html.escape(_clean(value) or "N/A")
    if len(text) > limit:
        text = text[:limit] + "…"
    return text.replace("\n", "<br/>")


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _rate_label(value: Any) -> str:
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if rate > 1:
        rate = rate / 100
    return f"{rate * 100:.2f}%"


def report_filename(model: Dict[str, Any]) -> str:
    tenant = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        _clean(model.get("prepared_for")) or _clean(model.get("tenant_name")) or "client",
    )
    tenant = tenant.strip("-")[:40] or "client"
    as_of = _clean(model.get("as_of")) or datetime.now().date().isoformat()
    return f"ASC842-IFRS16-Compliance-Report-{tenant}-{as_of}.pdf"


def lease_inputs_from_calculation(calc: Optional[dict]) -> Dict[str, Any]:
    """Rebuild engine inputs from a saved asc842_calculations row."""
    calc = calc or {}
    raw = calc.get("calculation_data")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed:
                return parsed
        except json.JSONDecodeError:
            pass
    if isinstance(raw, dict) and raw:
        return raw

    rate = calc.get("discount_rate") or 0
    try:
        rate = float(rate)
        if rate > 1:
            rate = rate / 100
    except (TypeError, ValueError):
        rate = 0.05
    return {
        "commencement_date": calc.get("lease_commencement_date") or calc.get("commencement_date"),
        "end_date": calc.get("lease_end_date") or calc.get("end_date"),
        "monthly_payment": calc.get("monthly_base_rent") or calc.get("monthly_payment") or 0,
        "discount_rate": rate,
        "initial_direct_costs": calc.get("initial_direct_costs") or 0,
        "lease_incentives": calc.get("lease_incentives") or 0,
        "prepayments": calc.get("prepayments") or 0,
        "residual_value_guarantee": calc.get("residual_value_guarantee") or 0,
        "has_renewal_option": calc.get("has_renewal_option") or False,
        "renewal_term_months": calc.get("renewal_term_months") or 0,
        "renewal_reasonably_certain": calc.get("renewal_reasonably_certain") or False,
        "has_purchase_option": calc.get("has_purchase_option") or False,
        "purchase_option_price": calc.get("purchase_option_price") or 0,
        "purchase_reasonably_certain": calc.get("purchase_reasonably_certain") or False,
        "has_termination_option": calc.get("has_termination_option") or False,
        "termination_penalty": calc.get("termination_penalty") or 0,
        "has_variable_payments": calc.get("has_variable_payments") or False,
        "variable_payment_index_rate": calc.get("variable_payment_index_rate") or 0,
        "annual_rent_increases": calc.get("annual_rent_increases") or 0,
    }


def _current_noncurrent(results: Dict[str, Any]) -> tuple[float, float]:
    schedule = results.get("liability_schedule") or []
    current = sum(
        float(row.get("principal_reduction") or 0)
        for row in schedule
        if int(row.get("period") or 0) <= 12
    )
    total = float(results.get("initial_liability") or 0)
    return round(current, 2), round(max(total - current, 0), 2)


def _aligned_initial_entry(entry: dict, rou_asset: Any, current: float, non_current: float) -> dict:
    aligned = dict(entry or {})
    lines = []
    for line in aligned.get("lines") or []:
        account = str(line.get("account") or "")
        updated = dict(line)
        if "Non-Current" in account:
            updated["credit"] = non_current
            updated["debit"] = 0
        elif "Current" in account:
            updated["credit"] = current
            updated["debit"] = 0
        elif "ROU Asset" in account:
            updated["debit"] = float(rou_asset or 0)
            updated["credit"] = 0
        lines.append(updated)
    if not lines:
        lines = [
            {"account": "ROU Asset - Lease", "debit": float(rou_asset or 0), "credit": 0},
            {"account": "Lease Liability - Current", "debit": 0, "credit": current},
            {"account": "Lease Liability - Non-Current", "debit": 0, "credit": non_current},
        ]
    aligned["lines"] = lines
    return aligned


def journal_entry_rows(entry: dict) -> List[Dict[str, Any]]:
    """Normalize engine `lines` or dashboard `debits`/`credits` into print rows."""
    rows: List[Dict[str, Any]] = []
    for line in entry.get("lines") or []:
        rows.append(
            {
                "account": line.get("account") or "Account",
                "debit": float(line.get("debit") or 0),
                "credit": float(line.get("credit") or 0),
            }
        )
    for debit in entry.get("debits") or []:
        rows.append(
            {
                "account": debit.get("account") or "Account",
                "debit": float(debit.get("amount") or debit.get("debit") or 0),
                "credit": 0.0,
            }
        )
    for credit in entry.get("credits") or []:
        rows.append(
            {
                "account": credit.get("account") or "Account",
                "debit": 0.0,
                "credit": float(credit.get("amount") or credit.get("credit") or 0),
            }
        )
    return rows


def build_asc842_report_model(
    lease: Optional[dict],
    calc: Optional[dict] = None,
    lease_inputs: Optional[dict] = None,
    prepared_for: Optional[str] = None,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the engine and assemble the client report model."""
    lease = lease or {}
    inputs = dict(lease_inputs or lease_inputs_from_calculation(calc))
    engine = ASC842ComplianceEngine(inputs)
    results = engine.run_full_calculation()
    prepared = (
        _clean(prepared_for)
        or _clean(lease.get("tenant_name"))
        or _clean((calc or {}).get("tenant_name"))
        or "Client"
    )
    as_of_value = as_of or datetime.now().date().isoformat()
    disclosures = dict(results.get("disclosures") or {})
    current, non_current = _current_noncurrent(results)
    balance = dict(disclosures.get("balance_sheet_impact") or {})
    balance["current_liability"] = current
    balance["non_current_liability"] = non_current
    disclosures["balance_sheet_impact"] = balance
    initial_entry = _aligned_initial_entry(
        results.get("initial_journal_entry") or {},
        results.get("initial_rou_asset") or engine.initial_rou_asset,
        current,
        non_current,
    )
    return {
        "property_address": lease.get("property_address")
        or (lease.get("leases") or {}).get("property_address")
        or "Unknown property",
        "tenant_name": lease.get("tenant_name")
        or (lease.get("leases") or {}).get("tenant_name")
        or "Unknown tenant",
        "prepared_for": prepared,
        "as_of": as_of_value,
        "standard": "ASC 842 / IFRS 16",
        "classification": results.get("classification") or engine.lease_classification,
        "classification_reasons": results.get("classification_reasons") or [],
        "initial_rou_asset": results.get("initial_rou_asset") or engine.initial_rou_asset,
        "initial_liability": results.get("initial_liability") or engine.initial_liability,
        "lease_term_months": results.get("lease_term_months") or engine.lease_term_months,
        "discount_rate": inputs.get("discount_rate"),
        "commencement_date": inputs.get("commencement_date"),
        "end_date": inputs.get("end_date"),
        "monthly_payment": inputs.get("monthly_payment"),
        "inputs": inputs,
        "results": results,
        "disclosures": disclosures,
        "initial_journal_entry": initial_entry,
        "monthly_journal_entries": engine.journal_entries or results.get("monthly_journal_entries") or [],
        "liability_schedule": results.get("liability_schedule") or [],
        "rou_asset_schedule": results.get("rou_asset_schedule") or [],
        "warnings": results.get("warnings") or [],
        "errors": results.get("errors") or [],
        "engine": engine,
    }


def _schedule_csv(rows: Iterable[dict]) -> str:
    records = list(rows or [])
    if not records:
        return ""
    import pandas as pd

    return pd.DataFrame(records).to_csv(index=False)


def build_asc842_report_package(
    lease: Optional[dict],
    calc: Optional[dict] = None,
    lease_inputs: Optional[dict] = None,
    prepared_for: Optional[str] = None,
) -> Dict[str, Any]:
    model = build_asc842_report_model(
        lease,
        calc=calc,
        lease_inputs=lease_inputs,
        prepared_for=prepared_for,
    )
    pdf_bytes = generate_asc842_compliance_pdf(model)
    return {
        "model": model,
        "pdf_bytes": pdf_bytes,
        "filename": report_filename(model),
        "liability_csv": _schedule_csv(model.get("liability_schedule")),
        "rou_csv": _schedule_csv(model.get("rou_asset_schedule")),
    }


def generate_asc842_compliance_pdf(model: Dict[str, Any]) -> bytes:
    """Render the compliance model as a branded PDF."""
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
        "Asc842Title",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1976D2"),
        spaceAfter=10,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "Asc842Heading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1976D2"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Asc842Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
    )
    label_style = ParagraphStyle(
        "Asc842Label",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "Asc842TableHeader",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.whitesmoke,
        alignment=TA_CENTER,
        leading=10,
    )

    story = []
    story.append(Paragraph(f"{config.APP_NAME} ASC 842 / IFRS 16 Compliance Report", title_style))
    story.append(Paragraph(_pdf_text(REPORT_STATEMENT), body_style))
    story.append(Spacer(1, 0.16 * inch))

    info = [
        [Paragraph("Prepared for", label_style), Paragraph(_pdf_text(model.get("prepared_for")), body_style)],
        [Paragraph("Property", label_style), Paragraph(_pdf_text(model.get("property_address")), body_style)],
        [Paragraph("Tenant / Customer", label_style), Paragraph(_pdf_text(model.get("tenant_name")), body_style)],
        [Paragraph("Standard", label_style), Paragraph(_pdf_text(model.get("standard")), body_style)],
        [Paragraph("Classification", label_style), Paragraph(_pdf_text(model.get("classification")), body_style)],
        [Paragraph("Commencement", label_style), Paragraph(_pdf_text(model.get("commencement_date")), body_style)],
        [Paragraph("End date", label_style), Paragraph(_pdf_text(model.get("end_date")), body_style)],
        [Paragraph("Lease term", label_style), Paragraph(_pdf_text(f"{model.get('lease_term_months')} months"), body_style)],
        [Paragraph("Incremental borrowing rate", label_style), Paragraph(_pdf_text(_rate_label(model.get("discount_rate"))), body_style)],
        [Paragraph("Initial ROU asset", label_style), Paragraph(_pdf_text(_money(model.get("initial_rou_asset"))), body_style)],
        [Paragraph("Initial lease liability", label_style), Paragraph(_pdf_text(_money(model.get("initial_liability"))), body_style)],
        [Paragraph("Report date", label_style), Paragraph(_pdf_text(model.get("as_of")), body_style)],
    ]
    info_table = Table(info, colWidths=[2.1 * inch, 4.7 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E3F2FD")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#90CAF9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(info_table)

    story.append(Paragraph("1. Classification", heading_style))
    reasons = model.get("classification_reasons") or ["No classification reason recorded"]
    story.append(
        Paragraph(
            f"This lease is classified as <b>{_pdf_text(model.get('classification'))}</b> "
            f"because: {_pdf_text('; '.join(str(item) for item in reasons))}.",
            body_style,
        )
    )

    story.append(Paragraph("2. Initial measurement", heading_style))
    disclosures = model.get("disclosures") or {}
    initial = disclosures.get("initial_measurement") or {}
    measure = [
        [
            Paragraph("Component", header_style),
            Paragraph("Amount", header_style),
        ],
        [Paragraph("Lease liability (PV of payments)", body_style), Paragraph(_money(initial.get("lease_liability") or model.get("initial_liability")), body_style)],
        [Paragraph("Initial direct costs", body_style), Paragraph(_money(initial.get("initial_direct_costs")), body_style)],
        [Paragraph("Prepayments", body_style), Paragraph(_money(initial.get("prepayments")), body_style)],
        [Paragraph("Lease incentives", body_style), Paragraph(_money(initial.get("lease_incentives")), body_style)],
        [Paragraph("Right-of-use asset", body_style), Paragraph(_money(initial.get("rou_asset") or model.get("initial_rou_asset")), body_style)],
    ]
    measure_table = Table(measure, colWidths=[4.4 * inch, 2.4 * inch])
    measure_table.setStyle(_plain_table_style())
    story.append(measure_table)

    story.append(Paragraph("3. Maturity analysis of undiscounted lease payments", heading_style))
    maturity = (disclosures.get("maturity_analysis") or {}) if isinstance(disclosures, dict) else {}
    if not maturity:
        story.append(Paragraph("No future payments were scheduled for this lease.", body_style))
    else:
        years = sorted(maturity.keys())
        first_five = years[:5]
        thereafter = sum(float(maturity[year]) for year in years[5:])
        rows = [[Paragraph("Year", header_style), Paragraph("Undiscounted payments", header_style)]]
        for year in first_five:
            rows.append([Paragraph(_pdf_text(year), body_style), Paragraph(_money(maturity[year]), body_style)])
        if thereafter:
            rows.append([Paragraph("Thereafter", body_style), Paragraph(_money(thereafter), body_style)])
        rows.append(
            [
                Paragraph("Total undiscounted payments", label_style),
                Paragraph(_money(sum(float(maturity[year]) for year in years)), body_style),
            ]
        )
        maturity_table = Table(rows, colWidths=[3.4 * inch, 3.4 * inch])
        maturity_table.setStyle(_plain_table_style())
        story.append(maturity_table)

    story.append(Paragraph("4. Expense and balance-sheet impact", heading_style))
    expense = disclosures.get("lease_expense_summary") or {}
    balance = disclosures.get("balance_sheet_impact") or {}
    impact = [
        [Paragraph("Item", header_style), Paragraph("Amount", header_style)],
        [Paragraph("Total interest expense", body_style), Paragraph(_money(expense.get("total_interest_expense")), body_style)],
        [Paragraph("Total ROU amortization", body_style), Paragraph(_money(expense.get("total_depreciation_expense")), body_style)],
        [Paragraph("Total lease expense (finance presentation)", body_style), Paragraph(_money(expense.get("total_lease_expense")), body_style)],
        [Paragraph("Current lease liability (next 12 months)", body_style), Paragraph(_money(balance.get("current_liability")), body_style)],
        [Paragraph("Non-current lease liability", body_style), Paragraph(_money(balance.get("non_current_liability")), body_style)],
    ]
    impact_table = Table(impact, colWidths=[4.4 * inch, 2.4 * inch])
    impact_table.setStyle(_plain_table_style())
    story.append(impact_table)

    story.append(Paragraph("5. Initial recognition journal entry", heading_style))
    story.extend(_journal_block(model.get("initial_journal_entry") or {}, body_style, label_style, header_style))

    story.append(Paragraph("6. Subsequent journal entries (first 6 months)", heading_style))
    monthly = list(model.get("monthly_journal_entries") or [])
    if not monthly:
        story.append(Paragraph("No monthly journal entries were generated.", body_style))
    else:
        shown = monthly[:18]
        for entry in shown:
            story.extend(_journal_block(entry, body_style, label_style, header_style))
        if len(monthly) > 18:
            story.append(
                Paragraph(
                    f"Showing the first 6 months ({len(shown)} entries) of {len(monthly)} generated entries. "
                    "The remaining periods follow the same interest, amortization, and payment pattern.",
                    body_style,
                )
            )

    story.append(Paragraph("7. Lease liability amortization (first 12 months)", heading_style))
    story.append(_schedule_table(
        model.get("liability_schedule") or [],
        [
            ("period", "Period"),
            ("date", "Date"),
            ("opening_balance", "Opening"),
            ("interest_expense", "Interest"),
            ("payment", "Payment"),
            ("closing_balance", "Closing"),
        ],
        body_style,
        header_style,
        money_cols={"opening_balance", "interest_expense", "payment", "closing_balance"},
    ))

    story.append(Paragraph("8. Right-of-use asset amortization (first 12 months)", heading_style))
    story.append(_schedule_table(
        model.get("rou_asset_schedule") or [],
        [
            ("period", "Period"),
            ("date", "Date"),
            ("opening_balance", "Opening"),
            ("depreciation_expense", "Amortization"),
            ("net_book_value", "Net book value"),
        ],
        body_style,
        header_style,
        money_cols={"opening_balance", "depreciation_expense", "net_book_value"},
    ))

    warnings = model.get("warnings") or []
    if warnings:
        story.append(Paragraph("Assumptions and warnings", heading_style))
        for warning in warnings:
            story.append(Paragraph(f"• {_pdf_text(warning)}", body_style))

    generated = datetime.now().strftime("%B %d, %Y")
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            f"Prepared by {config.APP_NAME} ASC 842 / IFRS 16 engine for "
            f"{_pdf_text(model.get('prepared_for'))}. Generated {generated}. "
            "This report is a file exhibit of calculated lease measurements. "
            "It is not a legal opinion or an audit report.",
            body_style,
        )
    )
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()


def _plain_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#90CAF9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _journal_block(entry: dict, body_style, label_style, header_style) -> List:
    rows = journal_entry_rows(entry)
    if not rows:
        return [Paragraph("No journal lines were recorded.", body_style), Spacer(1, 0.08 * inch)]
    table_rows = [[
        Paragraph("Account", header_style),
        Paragraph("Debit", header_style),
        Paragraph("Credit", header_style),
    ]]
    for row in rows:
        table_rows.append(
            [
                Paragraph(_pdf_text(row["account"]), body_style),
                Paragraph(_money(row["debit"]) if row["debit"] else "", body_style),
                Paragraph(_money(row["credit"]) if row["credit"] else "", body_style),
            ]
        )
    table = Table(table_rows, colWidths=[3.8 * inch, 1.5 * inch, 1.5 * inch])
    table.setStyle(_plain_table_style())
    title = entry.get("description") or entry.get("entry_type") or "Journal entry"
    when = entry.get("date") or ""
    return [
        KeepTogether(
            [
                Paragraph(f"<b>{_pdf_text(title)}</b> {_pdf_text(when)}", label_style),
                table,
                Spacer(1, 0.1 * inch),
            ]
        )
    ]


def _schedule_table(
    records: List[dict],
    columns: List[tuple],
    body_style,
    header_style,
    money_cols: set,
    limit: int = 12,
):
    if not records:
        return Paragraph("No schedule rows were generated.", body_style)
    header = [Paragraph(label, header_style) for _, label in columns]
    rows = [header]
    width = 6.8 * inch / max(len(columns), 1)
    for record in records[:limit]:
        cells = []
        for key, _label in columns:
            value = record.get(key)
            if key in money_cols:
                value = _money(value)
            cells.append(Paragraph(_pdf_text(value), body_style))
        rows.append(cells)
    table = Table(rows, colWidths=[width] * len(columns))
    table.setStyle(_plain_table_style())
    note = ""
    if len(records) > limit:
        note = f" Showing first {limit} of {len(records)} periods. Download the CSV for the full schedule."
    return KeepTogether([table, Paragraph(note, body_style) if note else Spacer(1, 0.04 * inch)])
