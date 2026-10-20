"""
LeaseAI - CAM Reconciliation PDF Report Generator
Phase 2B Session 2: Professional PDF reports for CAM reconciliation audits

This module generates:
- Executive summary of CAM reconciliation
- Variance breakdown by category
- Line-item comparison tables
- Lease terms reference
- Charts and visualizations
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import Dict, List, Optional
import io


class CAMReconciliationPDFReport:
    """
    Generate professional PDF reports for CAM reconciliation audits
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        
        # Only add styles if they don't already exist
        if 'CustomTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ))
        
        if 'SectionHeader' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=12,
                spaceBefore=12,
                fontName='Helvetica-Bold'
            ))
        
        if 'SubsectionHeader' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SubsectionHeader',
                parent=self.styles['Heading3'],
                fontSize=12,
                textColor=colors.HexColor('#2c5aa0'),
                spaceAfter=8,
                fontName='Helvetica-Bold'
            ))
        
        # Use custom name to avoid conflict with built-in BodyText
        if 'CAMBodyText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CAMBodyText',
                parent=self.styles['Normal'],
                fontSize=10,
                leading=14,
                alignment=TA_JUSTIFY
            ))
        
        if 'SummaryText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SummaryText',
                fontSize=11,
                leading=16,
                textColor=colors.black
            ))
    
    def generate_report(
        self,
        lease_data: Dict,
        reconciliation: Dict,
        line_items: List[Dict],
        cam_provisions: Dict,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Generate complete CAM reconciliation PDF report
        
        Args:
            lease_data: Lease information
            reconciliation: Reconciliation data
            line_items: List of CAM line items with variances
            cam_provisions: CAM provisions from lease
            output_path: Optional file path to save PDF
            
        Returns:
            PDF bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        # Build report content
        story = []
        
        # Page 1: Executive Summary
        story.extend(self._create_cover_page(lease_data, reconciliation))
        story.append(PageBreak())
        
        # Page 2: Variance Summary
        story.extend(self._create_variance_summary(reconciliation, line_items, cam_provisions))
        story.append(PageBreak())
        
        # Page 3: Line Item Details
        story.extend(self._create_line_item_table(line_items))
        
        if len(line_items) > 15:
            story.append(PageBreak())
        
        # Page 4: Lease Terms Reference
        story.extend(self._create_lease_terms_section(cam_provisions))
        
        # Build PDF
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def _create_cover_page(self, lease_data: Dict, reconciliation: Dict) -> List:
        """Create cover page with executive summary"""
        elements = []
        
        # Title
        elements.append(Paragraph("CAM Reconciliation Audit Report", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Property & tenant info
        property_info = [
            ['<b>Property:</b>', lease_data.get('property_address', 'N/A')],
            ['<b>Tenant:</b>', lease_data.get('tenant_name', 'N/A')],
            ['<b>Reconciliation Period:</b>', f"Year {reconciliation.get('reconciliation_year', 'N/A')}"],
            ['<b>Statement Date:</b>', reconciliation.get('statement_date', 'N/A')],
            ['<b>Report Generated:</b>', datetime.now().strftime('%B %d, %Y')]
        ]
        
        info_table = Table(property_info, colWidths=[2*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f4788')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.4*inch))
        
        # Financial Summary Box
        variance = reconciliation.get('variance_amount', 0)
        variance_pct = reconciliation.get('variance_percentage', 0)
        
        # Determine color based on variance
        if abs(variance) < 100:
            color = colors.HexColor('#d4edda')  # Green
            status_text = "✓ ACCURATE"
            status_color = colors.HexColor('#155724')
        elif abs(variance) < 500:
            color = colors.HexColor('#fff3cd')  # Yellow
            status_text = "⚠ MINOR VARIANCE"
            status_color = colors.HexColor('#856404')
        elif abs(variance) < 2000:
            color = colors.HexColor('#ffe5d0')  # Orange
            status_text = "⚠ MODERATE VARIANCE"
            status_color = colors.HexColor('#cc5500')
        else:
            color = colors.HexColor('#f8d7da')  # Red
            status_text = "⚠ SIGNIFICANT VARIANCE"
            status_color = colors.HexColor('#721c24')
        
        summary_data = [
            ['<b>Landlord Total Charges</b>', f"${reconciliation.get('landlord_total_charges', 0):,.2f}"],
            ['<b>Calculated Total Charges</b>', f"${reconciliation.get('calculated_total_charges', 0):,.2f}"],
            ['', ''],
            ['<b>Landlord Tenant Share</b>', f"${reconciliation.get('landlord_tenant_share', 0):,.2f}"],
            ['<b>Calculated Tenant Share</b>', f"${reconciliation.get('calculated_tenant_share', 0):,.2f}"],
            ['', ''],
            ['<b><font size="12">Variance Amount</font></b>', f'<b><font size="12" color="{status_color}">${variance:,.2f}</font></b>'],
            ['<b>Variance Percentage</b>', f'{variance_pct:.2f}%'],
            ['', ''],
            ['<b><font size="13">Status:</font></b>', f'<b><font size="13" color="{status_color}">{status_text}</font></b>']
        ]
        
        summary_table = Table(summary_data, colWidths=[3.5*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), color),
            ('BOX', (0, 0), (-1, -1), 2, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Recommendation
        elements.append(Paragraph("<b>Recommendation:</b>", self.styles['SubsectionHeader']))
        
        if abs(variance) < 100:
            recommendation = "The landlord's CAM reconciliation is accurate and within acceptable tolerance. Recommend accepting the charges as billed."
        elif abs(variance) < 500:
            recommendation = "Minor variance detected. Review the line-item breakdown for any obvious errors. May accept if differences are immaterial."
        elif abs(variance) < 2000:
            recommendation = "Moderate variance detected. Recommend reviewing the detailed line items and requesting clarification from landlord on discrepancies before payment."
        else:
            recommendation = f"Significant ${abs(variance):,.2f} variance detected. Strongly recommend disputing the charges and conducting a thorough audit. See detailed analysis on following pages."
        
        elements.append(Paragraph(recommendation, self.styles['CAMBodyText']))
        
        return elements
    
    def _create_variance_summary(self, reconciliation: Dict, line_items: List[Dict], cam_provisions: Dict) -> List:
        """Create variance summary by category"""
        elements = []
        
        elements.append(Paragraph("Variance Analysis by Category", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Group line items by category
        category_totals = {}
        for item in line_items:
            cat = item.get('category', 'OTHER')
            amt = float(item.get('amount', 0))
            variance = float(item.get('variance', 0))
            
            if cat not in category_totals:
                category_totals[cat] = {'total': 0, 'variance': 0, 'count': 0}
            
            category_totals[cat]['total'] += amt
            category_totals[cat]['variance'] += variance
            category_totals[cat]['count'] += 1
        
        # Build category table
        category_data = [['Category', 'Total Amount', 'Variance', 'Line Items']]
        
        for cat in sorted(category_totals.keys()):
            data = category_totals[cat]
            category_data.append([
                cat.replace('_', ' ').title(),
                f"${data['total']:,.2f}",
                f"${data['variance']:,.2f}",
                str(data['count'])
            ])
        
        category_table = Table(category_data, colWidths=[2.5*inch, 1.75*inch, 1.75*inch, 1*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        elements.append(category_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Key findings
        elements.append(Paragraph("Key Findings:", self.styles['SubsectionHeader']))
        
        findings = []
        
        # Find largest variances
        sorted_cats = sorted(category_totals.items(), key=lambda x: abs(x[1]['variance']), reverse=True)
        if sorted_cats and abs(sorted_cats[0][1]['variance']) > 100:
            cat_name = sorted_cats[0][0].replace('_', ' ').title()
            variance_amt = sorted_cats[0][1]['variance']
            findings.append(f"• Largest variance in <b>{cat_name}</b>: ${abs(variance_amt):,.2f}")
        
        # Check for excluded items
        excluded = cam_provisions.get('excluded_items', [])
        if excluded:
            findings.append(f"• Lease excludes: {', '.join(excluded)}")
        
        # Check CAM cap
        if cam_provisions.get('has_cam_cap'):
            cap_pct = cam_provisions.get('cam_cap_percentage', 0)
            findings.append(f"• Annual CAM increase capped at {cap_pct}%")
        
        if not findings:
            findings.append("• No significant issues identified")
        
        for finding in findings:
            elements.append(Paragraph(finding, self.styles['CAMBodyText']))
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _create_line_item_table(self, line_items: List[Dict]) -> List:
        """Create detailed line item comparison table"""
        elements = []
        
        elements.append(Paragraph("Detailed Line Item Breakdown", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        if not line_items:
            elements.append(Paragraph("No line items available.", self.styles['CAMBodyText']))
            return elements
        
        # Build table data
        table_data = [['#', 'Description', 'Category', 'Amount', 'Variance', 'Status']]
        
        for idx, item in enumerate(line_items, 1):
            desc = item.get('description', 'N/A')[:40]  # Truncate long descriptions
            cat = item.get('category', 'OTHER').replace('_', ' ')[:15]
            amt = float(item.get('amount', 0))
            variance = float(item.get('variance', 0))
            
            if abs(variance) < 50:
                status = '✓'
            elif abs(variance) < 200:
                status = '⚠'
            else:
                status = '✗'
            
            table_data.append([
                str(idx),
                desc,
                cat,
                f"${amt:,.2f}",
                f"${variance:,.2f}" if variance != 0 else '-',
                status
            ])
        
        line_table = Table(table_data, colWidths=[0.3*inch, 2.5*inch, 1.2*inch, 1*inch, 1*inch, 0.5*inch])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        elements.append(line_table)
        
        return elements
    
    def _create_lease_terms_section(self, cam_provisions: Dict) -> List:
        """Create lease terms reference section"""
        elements = []
        
        elements.append(Paragraph("Lease Terms Reference", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        terms_data = [
            ['<b>CAM Base Year:</b>', str(cam_provisions.get('cam_base_year', 'Not specified'))],
            ['<b>CAM Stop Amount:</b>', f"${cam_provisions.get('cam_stop_amount', 0):,.2f}" if cam_provisions.get('cam_stop_amount') else 'None'],
            ['<b>Tenant Pro-Rata Share:</b>', f"{cam_provisions.get('tenant_prorata_share', 0)*100:.2f}%" if cam_provisions.get('tenant_prorata_share') else 'Not specified'],
            ['<b>Tenant SF / Building SF:</b>', f"{cam_provisions.get('tenant_square_footage', 0):,} SF / {cam_provisions.get('building_square_footage', 0):,} SF"],
            ['<b>CAM Cap:</b>', f"Yes - {cam_provisions.get('cam_cap_percentage', 0)}% annual max" if cam_provisions.get('has_cam_cap') else 'No cap'],
            ['<b>Payment Frequency:</b>', cam_provisions.get('cam_payment_frequency', 'Not specified')],
            ['<b>Reconciliation Deadline:</b>', cam_provisions.get('reconciliation_deadline', 'Not specified')],
            ['<b>Audit Rights:</b>', 'Yes' if cam_provisions.get('tenant_audit_right') else 'No'],
        ]
        
        if cam_provisions.get('excluded_items'):
            excluded_str = ', '.join(cam_provisions['excluded_items'])
            terms_data.append(['<b>Excluded Items:</b>', excluded_str])
        
        terms_table = Table(terms_data, colWidths=[2.5*inch, 4*inch])
        terms_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(terms_table)
        
        return elements


def generate_cam_pdf_report(
    lease_data: Dict,
    reconciliation: Dict,
    line_items: List[Dict],
    cam_provisions: Dict,
    output_path: Optional[str] = None
) -> bytes:
    """
    Convenience function to generate CAM reconciliation PDF report
    
    Returns:
        PDF bytes (also saves to output_path if provided)
    """
    generator = CAMReconciliationPDFReport()
    return generator.generate_report(
        lease_data,
        reconciliation,
        line_items,
        cam_provisions,
        output_path
    )
