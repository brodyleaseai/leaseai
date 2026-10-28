"""
PDF Report Generation for Lease Abstracts
Generates professional, branded multi-page PDF reports with color-coded confidence indicators.
"""
import io
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import config
from lease_field_recovery import extracted_display_value

# A single ReportLab table row cannot be taller than the page frame (~654pt).
MAX_VALUE_CHARS = 1400
ROWS_PER_TABLE = 10
FIELD_COL_WIDTHS = [2.0 * inch, 4.0 * inch, 0.9 * inch]


def _xml(text) -> str:
    return escape(str(text if text is not None else "")).replace("\n", "<br/>")


def iter_value_chunks(text: str, max_chars: int = MAX_VALUE_CHARS):
    """Split a clause so each table row stays shorter than one page."""
    value = str(text if text is not None else "NOT FOUND").strip() or "NOT FOUND"
    if len(value) <= max_chars:
        yield value
        return
    start = 0
    while start < len(value):
        end = min(start + max_chars, len(value))
        if end < len(value):
            split_at = value.rfind(" ", start, end)
            if split_at > start + (max_chars // 2):
                end = split_at
        chunk = value[start:end].strip()
        if chunk:
            yield chunk
        start = end


def _style_fields_table(table, row_count: int):
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        *[("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F5F5"))
          for i in range(2, row_count, 2)],
    ]))
    return table


def _make_colored_box(box_color: str):
    """
    Create a small colored box indicator using a ReportLab Table.
    
    Args:
        box_color: Hex color string (e.g., "#00C853")
    
    Returns:
        Table flowable with colored background
    """
    box = Table([[""]], colWidths=[0.18 * inch], rowHeights=[0.18 * inch])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(box_color)),
        ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor(box_color)),
    ]))
    return box


def _confidence_color(conf):
    """
    Map confidence score to color code.
    
    Args:
        conf: Confidence value (float, string "HIGH"/"MEDIUM"/"LOW", or None)
    
    Returns:
        Hex color string
    """
    if conf is None:
        return "#9E9E9E"  # Gray for unknown
    
    # Handle string confidence levels
    if isinstance(conf, str):
        conf_upper = conf.upper()
        if conf_upper == "HIGH":
            return "#00C853"  # Green
        elif conf_upper == "MEDIUM":
            return "#FFB300"  # Amber
        elif conf_upper in ["LOW", "NOT_FOUND"]:
            return "#D50000"  # Red
        else:
            return "#9E9E9E"  # Gray for unknown strings
    
    # Handle numeric confidence scores
    try:
        score = float(conf)
        if score >= 0.85:
            return "#00C853"  # Green
        elif score >= 0.60:
            return "#FFB300"  # Amber
        else:
            return "#D50000"  # Red
    except (ValueError, TypeError):
        return "#9E9E9E"  # Gray for unparseable values


def _header_footer(canvas_obj, doc):
    """
    Draw header and footer on each page.
    
    Args:
        canvas_obj: ReportLab canvas
        doc: Document template
    """
    canvas_obj.saveState()
    
    # Header
    canvas_obj.setFont('Helvetica-Bold', 10)
    canvas_obj.drawString(0.75 * inch, letter[1] - 0.5 * inch, config.APP_NAME)
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.drawRightString(
        letter[0] - 0.75 * inch,
        letter[1] - 0.5 * inch,
        f"{config.COMPANY_NAME} | {config.COMPANY_LOCATION}"
    )
    
    # Footer
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.drawCentredString(
        letter[0] / 2.0,
        0.5 * inch,
        f"Page {doc.page} | Generated {datetime.now().strftime('%B %d, %Y')}"
    )
    
    canvas_obj.restoreState()


def generate_lease_abstract_pdf(lease_data: dict, extracted_fields: dict) -> bytes:
    """
    Generate a comprehensive PDF lease abstract report.
    
    Args:
        lease_data: Dictionary with lease metadata (property_address, tenant_name, etc.)
        extracted_fields: Dictionary of extracted lease fields with confidence scores
    
    Returns:
        PDF content as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#1976D2"),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#1976D2"),
        spaceAfter=8,
        spaceBefore=12
    )
    
    # Title Page
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph(f"{config.APP_NAME} Lease Abstract", title_style))
    story.append(Spacer(1, 0.25 * inch))
    
    # Property Information Box
    info_label = ParagraphStyle(
        "InfoLabel",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        alignment=TA_RIGHT,
    )
    info_value = ParagraphStyle(
        "InfoValue",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_LEFT,
    )
    property_info = [
        [Paragraph("Property:", info_label), Paragraph(_xml(extracted_display_value(extracted_fields, "Property Civic Address") or lease_data.get("property_address", "N/A")), info_value)],
        [Paragraph("Tenant:", info_label), Paragraph(_xml(extracted_display_value(extracted_fields, "Tenant Legal Name") or lease_data.get("tenant_name", "N/A")), info_value)],
        [Paragraph("Generated:", info_label), Paragraph(_xml(datetime.now().strftime("%B %d, %Y at %I:%M %p")), info_value)],
    ]
    
    prop_table = Table(property_info, colWidths=[1.5 * inch, 4.5 * inch])
    prop_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E3F2FD")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#90CAF9")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    
    story.append(prop_table)
    story.append(Spacer(1, 0.5 * inch))
    
    # Calculate confidence statistics (moved before page break)
    total_fields = len(extracted_fields)
    high_count = 0
    medium_count = 0
    low_count = 0
    
    for field_info in extracted_fields.values():
        if isinstance(field_info, dict):
            confidence = field_info.get("confidence", None)
            if isinstance(confidence, str):
                conf_upper = confidence.upper()
                if conf_upper == "HIGH":
                    high_count += 1
                elif conf_upper == "MEDIUM":
                    medium_count += 1
                elif conf_upper in ["LOW", "NOT_FOUND"]:
                    low_count += 1
            elif isinstance(confidence, (int, float)):
                score = float(confidence)
                if score >= 0.85:
                    high_count += 1
                elif score >= 0.60:
                    medium_count += 1
                else:
                    low_count += 1
    
    high_pct = (high_count / total_fields * 100) if total_fields > 0 else 0
    medium_pct = (medium_count / total_fields * 100) if total_fields > 0 else 0
    low_pct = (low_count / total_fields * 100) if total_fields > 0 else 0
    
    # Confidence Summary Box - Redesigned for clarity
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=TA_LEFT
    )
    
    summary_header_style = ParagraphStyle(
        'SummaryHeaderStyle',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.whitesmoke,  # White text for header
        alignment=TA_CENTER
    )
    
    summary_data = [
        [Paragraph("Extraction Quality Summary", summary_header_style)],  # White text
        [Paragraph(f"<b>Total Fields:</b> {total_fields} fields extracted", summary_style)],
        [""],  # Spacer
        [Paragraph("<b>Confidence Distribution:</b>", summary_style)],
        [Paragraph(f"<font color='#1B5E20'>● HIGH:</font> {high_count} fields ({high_pct:.1f}%)", summary_style)],
        [Paragraph(f"<font color='#F57F17'>● MEDIUM:</font> {medium_count} fields ({medium_pct:.1f}%)", summary_style)],
        [Paragraph(f"<font color='#B71C1C'>● LOW / NOT FOUND:</font> {low_count} fields ({low_pct:.1f}%)", summary_style)],
    ]
    
    summary_table = Table(summary_data, colWidths=[6.0*inch])
    summary_table.setStyle(TableStyle([
        # Header row - white text to match main table
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#1976D2")),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.whitesmoke),  # White text
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("FONTSIZE", (0, 0), (0, 0), 11),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 10),
        
        # Total fields row
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#E3F2FD")),
        ("ALIGN", (0, 1), (0, 1), "LEFT"),
        ("TOPPADDING", (0, 1), (0, 1), 8),
        ("BOTTOMPADDING", (0, 1), (0, 1), 8),
        
        # Spacer row
        ("BACKGROUND", (0, 2), (0, 2), colors.white),
        ("TOPPADDING", (0, 2), (0, 2), 4),
        ("BOTTOMPADDING", (0, 2), (0, 2), 4),
        
        # Distribution header
        ("BACKGROUND", (0, 3), (0, 3), colors.HexColor("#E3F2FD")),
        ("ALIGN", (0, 3), (0, 3), "LEFT"),
        ("TOPPADDING", (0, 3), (0, 3), 6),
        ("BOTTOMPADDING", (0, 3), (0, 3), 6),
        
        # Distribution rows
        ("BACKGROUND", (0, 4), (0, 4), colors.HexColor("#E8F5E9")),
        ("BACKGROUND", (0, 5), (0, 5), colors.HexColor("#FFF8E1")),
        ("BACKGROUND", (0, 6), (0, 6), colors.HexColor("#FFEBEE")),
        ("ALIGN", (0, 4), (0, 6), "LEFT"),
        ("TOPPADDING", (0, 4), (0, 6), 6),
        ("BOTTOMPADDING", (0, 4), (0, 6), 6),
        
        # All rows
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#90CAF9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    
    story.append(summary_table)
    story.append(PageBreak())
    
    # Extracted Fields Section (now on page 2)
    story.append(Paragraph("Extracted Lease Data", heading_style))
    story.append(Spacer(1, 0.25 * inch))
    
    # Build field rows with proper header styling
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,  # Smaller font to fit "Confidence" fully
        fontName='Helvetica-Bold',
        textColor=colors.whitesmoke,
        alignment=TA_CENTER,
        leading=11
    )
    
    header_row = [
        Paragraph("Field Name", header_style),
        Paragraph("Extracted Value", header_style),
        Paragraph("Confidence", header_style),
    ]
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=TA_LEFT
    )
    
    field_name_style = ParagraphStyle(
        'FieldNameStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    )
    
    data_rows = []
    for field_name, field_info in extracted_fields.items():
        if isinstance(field_info, dict):
            value = field_info.get("reviewed_value") or field_info.get("raw_value") or field_info.get("value", "NOT FOUND")
            confidence = field_info.get("confidence", None)
        else:
            value = str(field_info)
            confidence = None
        
        display_value = str(value) if value else "NOT FOUND"
        label = str(field_name).replace("_", " ")
        color_hex = _confidence_color(confidence)
        chunks = list(iter_value_chunks(display_value))
        for index, chunk in enumerate(chunks):
            data_rows.append([
                Paragraph(_xml(label if index == 0 else f"{label} (continued)"), field_name_style),
                Paragraph(_xml(chunk), cell_style),
                _make_colored_box(color_hex) if index == 0 else "",
            ])
    
    # One 80-row table cannot hold a clause taller than the page frame.
    for start in range(0, len(data_rows), ROWS_PER_TABLE):
        chunk_rows = [header_row] + data_rows[start:start + ROWS_PER_TABLE]
        fields_table = Table(
            chunk_rows,
            colWidths=FIELD_COL_WIDTHS,
            repeatRows=1,
            splitByRow=1,
        )
        _style_fields_table(fields_table, len(chunk_rows))
        story.append(fields_table)
        story.append(Spacer(1, 0.12 * inch))
    
    story.append(Spacer(1, 0.35 * inch))
    
    # Build the PDF
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


if __name__ == "__main__":
    # Test generation
    test_lease = {
        "property_address": "123 Main Street, Vancouver, BC",
        "tenant_name": "Acme Corporation"
    }
    
    test_fields = {
        "lease_commencement_date": {"value": "January 1, 2024", "confidence": 0.95},
        "lease_expiration_date": {"value": "December 31, 2028", "confidence": 0.92},
        "base_rent": {"value": "$5,000/month", "confidence": 0.88},
        "security_deposit": {"value": "$10,000", "confidence": 0.75},
        "landlord_name": {"value": "Property Holdings LLC", "confidence": 0.65},
        "permitted_use": {"value": "General office purposes", "confidence": 0.50},
    }
    
    pdf = generate_lease_abstract_pdf(test_lease, test_fields)
    
    with open("test_abstract.pdf", "wb") as f:
        f.write(pdf)
    
    print("Test PDF generated: test_abstract.pdf")
