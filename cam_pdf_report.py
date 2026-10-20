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
        
        # Title with better spacing
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("CAM RECONCILIATION AUDIT REPORT", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Property & tenant info in cleaner table
        property_info = [
            ['<b>Property:</b>', lease_data.get('property_address', 'N/A')],
            ['<b>Tenant:</b>', lease_data.get('tenant_name', 'N/A')],
            ['<b>Period:</b>', f"Year {reconciliation.get('reconciliation_year', 'N/A')}"],
            ['<b>Statement Date:</b>', reconciliation.get('statement_date', 'N/A')],
            ['<b>Report Date:</b>', datetime.now().strftime('%B %d, %Y')]
        ]
        
        info_table = Table(property_info, colWidths=[1.5*inch, 5*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f4788')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.6*inch))
        
        # Financial Summary Section Header
        elements.append(Paragraph("FINANCIAL SUMMARY", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Financial Summary Box - cleaner design
        variance = reconciliation.get('variance_amount', 0)
        variance_pct = reconciliation.get('variance_percentage', 0)
        
        # Determine status and color
        if abs(variance) < 100:
            bg_color = colors.HexColor('#e8f5e9')  # Light green
            status_text = "ACCURATE"
            status_icon = "[OK]"
            status_color = colors.HexColor('#2e7d32')  # Dark green
        elif abs(variance) < 500:
            bg_color = colors.HexColor('#fff9e6')  # Light yellow
            status_text = "MINOR VARIANCE"
            status_icon = "[!]"
            status_color = colors.HexColor('#f57c00')  # Orange
        elif abs(variance) < 2000:
            bg_color = colors.HexColor('#fff3e0')  # Light orange
            status_text = "MODERATE VARIANCE"
            status_icon = "[!!]"
            status_color = colors.HexColor('#e65100')  # Dark orange
        else:
            bg_color = colors.HexColor('#ffebee')  # Light red
            status_text = "SIGNIFICANT VARIANCE"
            status_icon = "[!!!]"
            status_color = colors.HexColor('#c62828')  # Dark red
        
        # Build summary table with better layout
        summary_data = [
            ['<b>LANDLORD CHARGES</b>', ''],
            ['   Total Building Charges:', f"${reconciliation.get('landlord_total_charges', 0):,.2f}"],
            ['   Your Share (Billed):', f"${reconciliation.get('landlord_tenant_share', 0):,.2f}"],
            ['', ''],
            ['<b>CALCULATED CHARGES</b>', ''],
            ['   Total Building Charges:', f"${reconciliation.get('calculated_total_charges', 0):,.2f}"],
            ['   Your Share (Per Lease):', f"${reconciliation.get('calculated_tenant_share', 0):,.2f}"],
            ['', ''],
            ['', ''],
            ['<b><font size="13">VARIANCE:</font></b>', f'<b><font size="13">${abs(variance):,.2f}</font></b>'],
            ['<b>Percentage:</b>', f'<b>{abs(variance_pct):.2f}%</b>'],
        ]
        
        summary_table = Table(summary_data, colWidths=[3.8*inch, 2.7*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#bdbdbd')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            # Section headers
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 4), (-1, 4), 11),
            # Variance row highlight
            ('BACKGROUND', (0, 9), (-1, 10), colors.white),
            ('TOPPADDING', (0, 9), (-1, 10), 12),
            ('BOTTOMPADDING', (0, 9), (-1, 10), 12),
            ('LINEABOVE', (0, 9), (-1, 9), 2, colors.HexColor('#757575')),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Status Badge
        status_data = [[f'<b><font size="14" color="{status_color}">{status_icon} STATUS: {status_text}</font></b>']]
        status_table = Table(status_data, colWidths=[6.5*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 2, status_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        elements.append(status_table)
        elements.append(Spacer(1, 0.4*inch))
        
        # Recommendation Section
        elements.append(Paragraph("RECOMMENDATION", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.15*inch))
        
        if abs(variance) < 100:
            recommendation = "The landlord's CAM reconciliation is <b>accurate</b> and within acceptable tolerance. The variance of ${:,.2f} represents less than 1% of the total charges. <b>Recommend accepting</b> the charges as billed.".format(abs(variance))
        elif abs(variance) < 500:
            recommendation = "A <b>minor variance</b> of ${:,.2f} ({:.1f}%) has been detected. This may be due to rounding differences or minor calculation discrepancies. <b>Review recommended</b> but likely acceptable if differences are immaterial to your business.".format(abs(variance), abs(variance_pct))
        elif abs(variance) < 2000:
            recommendation = "A <b>moderate variance</b> of ${:,.2f} ({:.1f}%) has been identified. We recommend <b>requesting clarification</b> from the landlord regarding the specific line items causing the discrepancy before making payment. See detailed analysis on the following pages.".format(abs(variance), abs(variance_pct))
        else:
            recommendation = "A <b>significant variance</b> of ${:,.2f} ({:.1f}%) has been detected. This represents a material discrepancy that warrants immediate attention. We <b>strongly recommend disputing</b> these charges and conducting a thorough audit. Consider exercising your lease audit rights. Detailed line-item analysis follows.".format(abs(variance), abs(variance_pct))
        
        elements.append(Paragraph(recommendation, self.styles['CAMBodyText']))
        
        return elements
    
    def _create_variance_summary(self, reconciliation: Dict, line_items: List[Dict], cam_provisions: Dict) -> List:
        """Create variance summary by category"""
        elements = []
        
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("VARIANCE ANALYSIS BY CATEGORY", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
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
        
        if category_totals:
            # Build category table
            category_data = [['<b>CATEGORY</b>', '<b>TOTAL AMOUNT</b>', '<b>VARIANCE</b>', '<b>ITEMS</b>']]
            
            for cat in sorted(category_totals.keys(), key=lambda x: abs(category_totals[x]['variance']), reverse=True):
                data = category_totals[cat]
                category_data.append([
                    cat.replace('_', ' ').title(),
                    f"${data['total']:,.2f}",
                    f"${data['variance']:,.2f}",
                    str(data['count'])
                ])
            
            # Add total row
            total_amt = sum(d['total'] for d in category_totals.values())
            total_var = sum(d['variance'] for d in category_totals.values())
            total_items = sum(d['count'] for d in category_totals.values())
            category_data.append(['<b>TOTAL</b>', f"<b>${total_amt:,.2f}</b>", f"<b>${total_var:,.2f}</b>", f"<b>{total_items}</b>"])
            
            category_table = Table(category_data, colWidths=[2.5*inch, 1.75*inch, 1.75*inch, 0.5*inch])
            category_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
                # Total row
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#757575')),
            ]))
            
            elements.append(category_table)
        else:
            elements.append(Paragraph("<i>No line item data available for category analysis.</i>", self.styles['CAMBodyText']))
        
        elements.append(Spacer(1, 0.4*inch))
        
        # Key findings
        elements.append(Paragraph("KEY FINDINGS", self.styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.15*inch))
        
        findings = []
        
        if category_totals:
            # Find largest variances
            sorted_cats = sorted(category_totals.items(), key=lambda x: abs(x[1]['variance']), reverse=True)
            if sorted_cats and abs(sorted_cats[0][1]['variance']) > 100:
                cat_name = sorted_cats[0][0].replace('_', ' ').title()
                variance_amt = sorted_cats[0][1]['variance']
                findings.append(f"• <b>Largest variance</b> in {cat_name}: ${abs(variance_amt):,.2f}")
            
            # Count flagged items
            flagged_count = sum(1 for item in line_items if item.get('should_challenge', False))
            if flagged_count > 0:
                findings.append(f"• <b>{flagged_count} line items</b> flagged for review or challenge")
        
        # Check for excluded items
        excluded = cam_provisions.get('excluded_items', [])
        if excluded:
            excluded_str = ', '.join(excluded)
            findings.append(f"• Per lease terms, the following are <b>excluded from CAM</b>: {excluded_str}")
        
        # Check CAM cap
        if cam_provisions.get('has_cam_cap'):
            cap_pct = cam_provisions.get('cam_cap_percentage', 0)
            findings.append(f"• Lease includes <b>{cap_pct}% annual CAM cap</b> on increases")
        
        # Check audit rights
        if cam_provisions.get('tenant_audit_right'):
            findings.append(f"• Tenant has <b>audit rights</b> per lease agreement")
        
        if not findings:
            findings.append("• No significant issues or special provisions identified")
        
        for finding in findings:
            elements.append(Paragraph(finding, self.styles['CAMBodyText']))
            elements.append(Spacer(1, 0.08*inch))
        
        return elements
    
    def _create_line_item_table(self, line_items: List[Dict]) -> List:
        """Create detailed line item comparison table"""
        elements = []
        
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("DETAILED LINE ITEM BREAKDOWN", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
        if not line_items:
            # Create a nice info box instead of plain text
            no_data_message = [
                ['<b>NO LINE ITEM DATA AVAILABLE</b>'],
                [''],
                ['This reconciliation was performed without detailed line-item data from the landlord\'s CAM statement.'],
                [''],
                ['To perform a comprehensive line-by-line analysis, please:'],
                ['   1. Request a detailed CAM statement from your landlord'],
                ['   2. Upload the statement in the CAM Reconciliation module'],
                ['   3. Use the "Parse CAM Statement with AI" feature'],
                ['   4. Regenerate this report with line item details']
            ]
            
            no_data_table = Table(no_data_message, colWidths=[6*inch])
            no_data_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#90caf9')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, 0), 15),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ]))
            
            elements.append(no_data_table)
            return elements
        
        # Build table data with line items
        table_data = [['<b>#</b>', '<b>DESCRIPTION</b>', '<b>CATEGORY</b>', '<b>AMOUNT</b>', '<b>VARIANCE</b>', '<b>FLAG</b>']]
        
        for idx, item in enumerate(line_items, 1):
            desc = item.get('description', 'N/A')
            if len(desc) > 50:
                desc = desc[:47] + '...'
            
            cat = item.get('category', 'OTHER').replace('_', ' ')
            if len(cat) > 18:
                cat = cat[:15] + '...'
            
            amt = float(item.get('amount', 0))
            variance = float(item.get('variance', 0))
            
            # Status flag
            if abs(variance) < 50:
                flag = 'OK'
            elif abs(variance) < 200:
                flag = 'Review'
            else:
                flag = 'Challenge'
            
            table_data.append([
                str(idx),
                desc,
                cat,
                f"${amt:,.2f}",
                f"${variance:,.2f}" if variance != 0 else '-',
                flag
            ])
        
        line_table = Table(table_data, colWidths=[0.3*inch, 2.5*inch, 1.3*inch, 1*inch, 1*inch, 0.7*inch])
        line_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (5, 0), (5, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ]))
        
        elements.append(line_table)
        
        return elements
    
    def _create_lease_terms_section(self, cam_provisions: Dict) -> List:
        """Create lease terms reference section"""
        elements = []
        
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("LEASE TERMS REFERENCE", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.3*inch))
        
        # CAM Calculation Terms
        elements.append(Paragraph("<b>CAM CALCULATION TERMS</b>", self.styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        calc_terms = [
            ['CAM Base Year:', str(cam_provisions.get('cam_base_year', 'Not specified'))],
            ['CAM Stop Amount:', f"${cam_provisions.get('cam_stop_amount', 0):,.2f}" if cam_provisions.get('cam_stop_amount') else 'None'],
            ['CAM Base Amount:', f"${cam_provisions.get('cam_base_amount', 0):,.2f}" if cam_provisions.get('cam_base_amount') else 'Not specified'],
            ['', ''],
            ['Tenant Square Footage:', f"{cam_provisions.get('tenant_square_footage', 0):,} SF" if cam_provisions.get('tenant_square_footage') else 'Not specified'],
            ['Building Square Footage:', f"{cam_provisions.get('building_square_footage', 0):,} SF" if cam_provisions.get('building_square_footage') else 'Not specified'],
            ['Tenant Pro-Rata Share:', f"{cam_provisions.get('tenant_prorata_share', 0)*100:.2f}%" if cam_provisions.get('tenant_prorata_share') else 'Not specified'],
        ]
        
        calc_table = Table(calc_terms, colWidths=[2.5*inch, 4*inch])
        calc_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f4788')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(calc_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # CAM Caps & Limitations
        elements.append(Paragraph("<b>CAM CAPS & LIMITATIONS</b>", self.styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        if cam_provisions.get('has_cam_cap'):
            cap_pct = cam_provisions.get('cam_cap_percentage', 0)
            cap_text = f"Yes - {cap_pct}% maximum annual increase"
        else:
            cap_text = "No annual cap on CAM increases"
        
        cap_terms = [
            ['Annual CAM Cap:', cap_text],
        ]
        
        cap_table = Table(cap_terms, colWidths=[2.5*inch, 4*inch])
        cap_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f4788')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(cap_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Excluded Items
        excluded = cam_provisions.get('excluded_items', [])
        if excluded:
            elements.append(Paragraph("<b>EXCLUDED ITEMS (Per Lease)</b>", self.styles['SubsectionHeader']))
            elements.append(Spacer(1, 0.1*inch))
            
            excluded_text = "The following items are explicitly excluded from CAM charges per the lease agreement:\n\n"
            for item in excluded:
                excluded_text += f"  • {item}\n"
            
            elements.append(Paragraph(excluded_text, self.styles['CAMBodyText']))
            elements.append(Spacer(1, 0.3*inch))
        
        # Tenant Rights
        elements.append(Paragraph("<b>TENANT RIGHTS & OBLIGATIONS</b>", self.styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        rights_terms = [
            ['Payment Frequency:', cam_provisions.get('cam_payment_frequency', 'Not specified')],
            ['Reconciliation Deadline:', cam_provisions.get('reconciliation_deadline', 'Not specified')],
            ['Tenant Audit Rights:', 'Yes - Tenant may audit CAM charges' if cam_provisions.get('tenant_audit_right') else 'Not specified or not granted'],
            ['Audit Deadline:', cam_provisions.get('audit_deadline', 'N/A') if cam_provisions.get('tenant_audit_right') else 'N/A'],
        ]
        
        rights_table = Table(rights_terms, colWidths=[2.5*inch, 4*inch])
        rights_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f4788')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(rights_table)
        
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
