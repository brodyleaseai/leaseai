"""
LeaseAI - CAM Reconciliation PDF Report Generator
Phase 2B Session 2 - REDESIGNED: Clean, professional PDF reports

Generates professional CAM reconciliation audit reports with:
- Clean executive summary
- Variance analysis
- Line item details
- Lease terms reference
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
from typing import Dict, List, Optional
import io


class CAMReconciliationPDFReport:
    """Generate professional PDF reports for CAM reconciliation audits"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        
        # Only add if doesn't exist
        if 'ReportTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='ReportTitle',
                parent=self.styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=20,
                spaceBefore=10,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ))
        
        if 'SectionHead' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHead',
                parent=self.styles['Heading2'],
                fontSize=13,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=10,
                spaceBefore=15,
                fontName='Helvetica-Bold'
            ))
        
        if 'SubHead' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SubHead',
                fontSize=11,
                textColor=colors.HexColor('#2c5aa0'),
                spaceAfter=6,
                spaceBefore=8,
                fontName='Helvetica-Bold'
            ))
        
        if 'BodyNormal' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='BodyNormal',
                parent=self.styles['Normal'],
                fontSize=10,
                leading=13,
                alignment=TA_JUSTIFY
            ))
        
        if 'TableCell' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='TableCell',
                parent=self.styles['Normal'],
                fontSize=10,
                leading=12
            ))
        
        if 'TableCellBold' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='TableCellBold',
                parent=self.styles['Normal'],
                fontSize=10,
                leading=12,
                fontName='Helvetica-Bold'
            ))
    
    def generate_report(
        self,
        lease_data: Dict,
        reconciliation: Dict,
        line_items: List[Dict],
        cam_provisions: Dict,
        output_path: Optional[str] = None
    ) -> bytes:
        """Generate complete CAM reconciliation PDF report"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Page 1: Executive Summary
        story.extend(self._create_cover_page(lease_data, reconciliation))
        story.append(PageBreak())
        
        # Page 2: Variance Summary (if line items exist)
        if line_items:
            story.extend(self._create_variance_summary(reconciliation, line_items, cam_provisions))
            story.append(PageBreak())
        
        # Page 3: Line Items
        story.extend(self._create_line_item_section(line_items))
        
        # Page 4: Lease Terms
        if line_items:
            story.append(PageBreak())
        story.extend(self._create_lease_terms_section(cam_provisions))
        
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def _create_cover_page(self, lease_data: Dict, reconciliation: Dict) -> List:
        """Create executive summary page"""
        elements = []
        
        # Title
        elements.append(Paragraph("CAM RECONCILIATION AUDIT REPORT", self.styles['ReportTitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Property Info Box
        prop_data = [
            [Paragraph("<b>Property:</b>", self.styles['TableCell']), 
             Paragraph(lease_data.get('property_address', 'N/A'), self.styles['TableCell'])],
            [Paragraph("<b>Tenant:</b>", self.styles['TableCell']), 
             Paragraph(lease_data.get('tenant_name', 'N/A'), self.styles['TableCell'])],
            [Paragraph("<b>Period:</b>", self.styles['TableCell']), 
             Paragraph(f"Year {reconciliation.get('reconciliation_year', 'N/A')}", self.styles['TableCell'])],
            [Paragraph("<b>Report Date:</b>", self.styles['TableCell']), 
             Paragraph(datetime.now().strftime('%B %d, %Y'), self.styles['TableCell'])],
        ]
        
        prop_table = Table(prop_data, colWidths=[1.5*inch, 5*inch])
        prop_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(prop_table)
        elements.append(Spacer(1, 0.25*inch))
        
        # Financial Summary
        elements.append(Paragraph("FINANCIAL SUMMARY", self.styles['SectionHead']))
        elements.append(Spacer(1, 0.1*inch))
        
        variance = reconciliation.get('variance_amount', 0)
        variance_pct = reconciliation.get('variance_percentage', 0)
        
        # Determine status
        if abs(variance) < 100:
            status = "ACCURATE"
            status_color = colors.HexColor('#2e7d32')
            bg = colors.HexColor('#e8f5e9')
        elif abs(variance) < 500:
            status = "MINOR VARIANCE"
            status_color = colors.HexColor('#f57c00')
            bg = colors.HexColor('#fff9e6')
        elif abs(variance) < 2000:
            status = "MODERATE VARIANCE"
            status_color = colors.HexColor('#e65100')
            bg = colors.HexColor('#fff3e0')
        else:
            status = "SIGNIFICANT VARIANCE"
            status_color = colors.HexColor('#c62828')
            bg = colors.HexColor('#ffebee')
        
        finance_data = [
            [Paragraph("<b>Landlord's Charges:</b>", self.styles['TableCell']), 
             Paragraph(f"${reconciliation.get('landlord_tenant_share', 0):,.2f}", self.styles['TableCell'])],
            [Paragraph("<b>Calculated Per Lease:</b>", self.styles['TableCell']), 
             Paragraph(f"${reconciliation.get('calculated_tenant_share', 0):,.2f}", self.styles['TableCell'])],
            [Paragraph("<b>Variance:</b>", self.styles['TableCellBold']), 
             Paragraph(f"<b>${abs(variance):,.2f} ({abs(variance_pct):.1f}%)</b>", self.styles['TableCellBold'])],
        ]
        
        finance_table = Table(finance_data, colWidths=[3*inch, 3.5*inch])
        finance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdbdbd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEABOVE', (0, 2), (-1, 2), 1.5, colors.HexColor('#757575')),
        ]))
        
        elements.append(finance_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Status
        status_para = Paragraph(
            f'<para align="center"><b><font size="13" color="{status_color}">STATUS: {status}</font></b></para>',
            self.styles['BodyNormal']
        )
        elements.append(status_para)
        elements.append(Spacer(1, 0.2*inch))
        
        # Recommendation
        elements.append(Paragraph("RECOMMENDATION", self.styles['SubHead']))
        
        if abs(variance) < 100:
            rec = "The landlord's CAM reconciliation is <b>accurate</b>. The variance of ${:,.2f} is within acceptable tolerance. <b>Recommend accepting</b> the charges as billed.".format(abs(variance))
        elif abs(variance) < 500:
            rec = "A minor variance of ${:,.2f} ({:.1f}%) detected. <b>Review recommended</b> but likely acceptable if immaterial.".format(abs(variance), abs(variance_pct))
        elif abs(variance) < 2000:
            rec = "A moderate variance of ${:,.2f} ({:.1f}%) identified. <b>Request clarification</b> from landlord before payment.".format(abs(variance), abs(variance_pct))
        else:
            rec = "A significant variance of ${:,.2f} ({:.1f}%) detected. <b>Strongly recommend disputing</b> and conducting a thorough audit.".format(abs(variance), abs(variance_pct))
        
        elements.append(Paragraph(rec, self.styles['BodyNormal']))
        
        return elements
    
    def _create_variance_summary(self, reconciliation: Dict, line_items: List[Dict], cam_provisions: Dict) -> List:
        """Create variance analysis by category"""
        elements = []
        
        elements.append(Paragraph("VARIANCE ANALYSIS BY CATEGORY", self.styles['SectionHead']))
        elements.append(Spacer(1, 0.15*inch))
        
        # Group by category
        categories = {}
        for item in line_items:
            cat = item.get('category', 'OTHER')
            amt = float(item.get('amount', 0))
            var = float(item.get('variance', 0))
            
            if cat not in categories:
                categories[cat] = {'total': 0, 'variance': 0, 'count': 0}
            categories[cat]['total'] += amt
            categories[cat]['variance'] += var
            categories[cat]['count'] += 1
        
        # Build table
        cat_data = [[
            Paragraph("<b>CATEGORY</b>", self.styles['TableCellBold']),
            Paragraph("<b>AMOUNT</b>", self.styles['TableCellBold']),
            Paragraph("<b>VARIANCE</b>", self.styles['TableCellBold']),
            Paragraph("<b>ITEMS</b>", self.styles['TableCellBold'])
        ]]
        
        for cat in sorted(categories.keys(), key=lambda x: abs(categories[x]['variance']), reverse=True):
            data = categories[cat]
            cat_data.append([
                Paragraph(cat.replace('_', ' ').title(), self.styles['TableCell']),
                Paragraph(f"${data['total']:,.2f}", self.styles['TableCell']),
                Paragraph(f"${data['variance']:,.2f}", self.styles['TableCell']),
                Paragraph(str(data['count']), self.styles['TableCell'])
            ])
        
        cat_table = Table(cat_data, colWidths=[2.8*inch, 1.6*inch, 1.6*inch, 0.5*inch])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        elements.append(cat_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Key Findings
        elements.append(Paragraph("KEY FINDINGS", self.styles['SubHead']))
        
        findings = []
        flagged = sum(1 for item in line_items if item.get('should_challenge', False))
        if flagged > 0:
            findings.append(f"• {flagged} line items flagged for review")
        
        excluded = cam_provisions.get('excluded_items', [])
        if excluded:
            findings.append(f"• Lease excludes: {', '.join(excluded)}")
        
        if cam_provisions.get('has_cam_cap'):
            cap = cam_provisions.get('cam_cap_percentage', 0)
            findings.append(f"• CAM increases capped at {cap}% annually")
        
        if not findings:
            findings.append("• No significant issues identified")
        
        for f in findings:
            elements.append(Paragraph(f, self.styles['BodyNormal']))
        
        return elements
    
    def _create_line_item_section(self, line_items: List[Dict]) -> List:
        """Create line item details"""
        elements = []
        
        elements.append(Paragraph("LINE ITEM DETAILS", self.styles['SectionHead']))
        elements.append(Spacer(1, 0.15*inch))
        
        if not line_items:
            no_data = Paragraph(
                "<i>No detailed line item data available. Upload a landlord CAM statement in the " +
                "CAM Reconciliation module and use 'Parse CAM Statement with AI' to perform a " +
                "comprehensive line-by-line analysis.</i>",
                self.styles['BodyNormal']
            )
            elements.append(no_data)
            return elements
        
        # Build line items table
        item_data = [[
            Paragraph("<b>#</b>", self.styles['TableCellBold']),
            Paragraph("<b>DESCRIPTION</b>", self.styles['TableCellBold']),
            Paragraph("<b>CATEGORY</b>", self.styles['TableCellBold']),
            Paragraph("<b>AMOUNT</b>", self.styles['TableCellBold']),
            Paragraph("<b>STATUS</b>", self.styles['TableCellBold'])
        ]]
        
        for idx, item in enumerate(line_items[:20], 1):  # Limit to 20 items
            desc = item.get('description', 'N/A')
            if len(desc) > 45:
                desc = desc[:42] + '...'
            
            cat = item.get('category', 'OTHER').replace('_', ' ')
            amt = float(item.get('amount', 0))
            var = float(item.get('variance', 0))
            
            if abs(var) < 50:
                flag = 'OK'
            elif abs(var) < 200:
                flag = 'Review'
            else:
                flag = 'Flag'
            
            item_data.append([
                Paragraph(str(idx), self.styles['TableCell']),
                Paragraph(desc, self.styles['TableCell']),
                Paragraph(cat, self.styles['TableCell']),
                Paragraph(f"${amt:,.2f}", self.styles['TableCell']),
                Paragraph(flag, self.styles['TableCell'])
            ])
        
        item_table = Table(item_data, colWidths=[0.3*inch, 2.7*inch, 1.4*inch, 1*inch, 0.6*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (4, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        elements.append(item_table)
        
        if len(line_items) > 20:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f"<i>Showing first 20 of {len(line_items)} line items</i>", self.styles['BodyNormal']))
        
        return elements
    
    def _create_lease_terms_section(self, cam_provisions: Dict) -> List:
        """Create lease terms reference"""
        elements = []
        
        elements.append(Paragraph("LEASE TERMS REFERENCE", self.styles['SectionHead']))
        elements.append(Spacer(1, 0.15*inch))
        
        # CAM Terms
        terms_data = [
            [Paragraph("<b>CAM Base Year:</b>", self.styles['TableCell']), 
             Paragraph(str(cam_provisions.get('cam_base_year', 'Not specified')), self.styles['TableCell'])],
            [Paragraph("<b>Tenant Pro-Rata Share:</b>", self.styles['TableCell']), 
             Paragraph(f"{cam_provisions.get('tenant_prorata_share', 0)*100:.2f}%" if cam_provisions.get('tenant_prorata_share') else 'Not specified', self.styles['TableCell'])],
            [Paragraph("<b>Tenant SF / Building SF:</b>", self.styles['TableCell']), 
             Paragraph(f"{cam_provisions.get('tenant_square_footage', 0):,} / {cam_provisions.get('building_square_footage', 0):,} SF", self.styles['TableCell'])],
            [Paragraph("<b>CAM Cap:</b>", self.styles['TableCell']), 
             Paragraph(f"Yes - {cam_provisions.get('cam_cap_percentage', 0)}% max" if cam_provisions.get('has_cam_cap') else 'No cap', self.styles['TableCell'])],
            [Paragraph("<b>Audit Rights:</b>", self.styles['TableCell']), 
             Paragraph('Yes' if cam_provisions.get('tenant_audit_right') else 'No', self.styles['TableCell'])],
        ]
        
        terms_table = Table(terms_data, colWidths=[2.5*inch, 4*inch])
        terms_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(terms_table)
        
        # Exclusions
        excluded = cam_provisions.get('excluded_items', [])
        if excluded:
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph("EXCLUDED ITEMS (Per Lease)", self.styles['SubHead']))
            for item in excluded:
                elements.append(Paragraph(f"• {item}", self.styles['BodyNormal']))
        
        return elements


def generate_cam_pdf_report(
    lease_data: Dict,
    reconciliation: Dict,
    line_items: List[Dict],
    cam_provisions: Dict,
    output_path: Optional[str] = None
) -> bytes:
    """Convenience function to generate CAM PDF report"""
    generator = CAMReconciliationPDFReport()
    return generator.generate_report(lease_data, reconciliation, line_items, cam_provisions, output_path)
