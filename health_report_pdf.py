"""
LeaseAI - Portfolio Health Report PDF Generator
Phase 6: Agentic AI Layer - Session 2

Generates professional PDF export of portfolio health reports
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from typing import Dict, List
import io


class PortfolioHealthPDFReport:
    """
    Generates professional PDF reports for portfolio health
    """
    
    def __init__(self):
        """Initialize PDF report generator"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles"""
        
        # Custom styles for health report
        if 'HealthTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='HealthTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#667eea'),
                spaceAfter=12,
                alignment=TA_CENTER
            ))
        
        if 'HealthSubtitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='HealthSubtitle',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=colors.grey,
                spaceAfter=20,
                alignment=TA_CENTER
            ))
        
        if 'SectionHeader' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#667eea'),
                spaceAfter=10,
                spaceBefore=15
            ))
        
        if 'HealthTableCell' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='HealthTableCell',
                parent=self.styles['Normal'],
                fontSize=10,
                leading=12
            ))
        
        if 'SmallText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SmallText',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=colors.grey
            ))
    
    def generate_report(self, report_data: Dict, actions: List[Dict], output_path: str) -> str:
        """
        Generate complete health report PDF
        
        Args:
            report_data: Dictionary with health report data
            actions: List of action items
            output_path: File path to save PDF
            
        Returns:
            Path to generated PDF
        """
        
        print(f"📄 Generating health report PDF: {output_path}")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        story = []
        
        # Page 1: Cover & Summary
        story.extend(self._create_cover_page(report_data))
        
        # Page 2: Detailed Metrics
        story.append(PageBreak())
        story.extend(self._create_metrics_page(report_data))
        
        # Page 3: Anomalies & Actions
        story.append(PageBreak())
        story.extend(self._create_actions_page(report_data, actions))
        
        # Page 4: Footer
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        
        print(f"✅ PDF generated successfully: {output_path}")
        
        return output_path
    
    def _create_cover_page(self, report: Dict) -> List:
        """Create cover page with health score and executive summary"""
        
        elements = []
        
        # Title
        title = Paragraph("Portfolio Health Report", self.styles['HealthTitle'])
        elements.append(title)
        
        # Date
        subtitle = Paragraph(f"Week of {report['report_date']}", self.styles['HealthSubtitle'])
        elements.append(subtitle)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Health Score Box
        health_status_colors = {
            'EXCELLENT': colors.HexColor('#2e7d32'),
            'GOOD': colors.HexColor('#7cb342'),
            'NEEDS_ATTENTION': colors.HexColor('#f57c00'),
            'CRITICAL': colors.HexColor('#c62828')
        }
        health_color = health_status_colors.get(report['health_status'], colors.grey)
        
        score_data = [
            [Paragraph(f"<font size='48' color='{health_color.hexval()}'><b>{report['health_score']}/100</b></font>", self.styles['HealthTableCell'])],
            [Paragraph(f"<font size='16' color='{health_color.hexval()}'><b>{report['health_status']}</b></font>", self.styles['HealthTableCell'])]
        ]
        
        score_table = Table(score_data, colWidths=[6*inch])
        score_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 2, health_color),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        elements.append(score_table)
        elements.append(Spacer(1, 0.4*inch))
        
        # Executive Summary
        section_header = Paragraph("Executive Summary", self.styles['SectionHeader'])
        elements.append(section_header)
        
        summary = Paragraph(report['executive_summary'], self.styles['Normal'])
        elements.append(summary)
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Key Highlights
        highlights_header = Paragraph("Key Highlights", self.styles['SectionHeader'])
        elements.append(highlights_header)
        
        highlights_data = [
            [
                Paragraph("<b>Active Leases</b>", self.styles['HealthTableCell']),
                Paragraph(str(report['active_leases']), self.styles['HealthTableCell']),
                Paragraph("<b>Monthly Rent</b>", self.styles['HealthTableCell']),
                Paragraph(f"${float(report['total_monthly_rent']):,.2f}", self.styles['HealthTableCell'])
            ],
            [
                Paragraph("<b>Anomalies Detected</b>", self.styles['HealthTableCell']),
                Paragraph(str(report['anomalies_detected']), self.styles['HealthTableCell']),
                Paragraph("<b>High Priority Issues</b>", self.styles['HealthTableCell']),
                Paragraph(str(report['high_severity_anomalies']), self.styles['HealthTableCell'])
            ],
            [
                Paragraph("<b>Deadlines (30 days)</b>", self.styles['HealthTableCell']),
                Paragraph(str(report['critical_dates_30_days']), self.styles['HealthTableCell']),
                Paragraph("<b>Requires Attention</b>", self.styles['HealthTableCell']),
                Paragraph(str(report['requires_attention']), self.styles['HealthTableCell'])
            ]
        ]
        
        highlights_table = Table(highlights_data, colWidths=[2*inch, 1.2*inch, 2*inch, 1.3*inch])
        highlights_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(highlights_table)
        
        return elements
    
    def _create_metrics_page(self, report: Dict) -> List:
        """Create detailed metrics page"""
        
        elements = []
        
        # Page title
        title = Paragraph("Portfolio Metrics", self.styles['SectionHeader'])
        elements.append(title)
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Portfolio Overview
        overview_data = [
            [Paragraph("<b>Metric</b>", self.styles['HealthTableCell']), Paragraph("<b>Value</b>", self.styles['HealthTableCell'])],
            [Paragraph("Total Leases", self.styles['HealthTableCell']), Paragraph(str(report['total_leases']), self.styles['HealthTableCell'])],
            [Paragraph("Active Leases", self.styles['HealthTableCell']), Paragraph(str(report['active_leases']), self.styles['HealthTableCell'])],
            [Paragraph("Leases Expiring Soon (90 days)", self.styles['HealthTableCell']), Paragraph(str(report['expiring_soon']), self.styles['HealthTableCell'])],
            [Paragraph("Leases Requiring Attention", self.styles['HealthTableCell']), Paragraph(str(report['requires_attention']), self.styles['HealthTableCell'])],
        ]
        
        overview_table = Table(overview_data, colWidths=[4*inch, 2.5*inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(overview_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Financial Metrics
        financial_header = Paragraph("Financial Metrics", self.styles['SectionHeader'])
        elements.append(financial_header)
        
        financial_data = [
            [Paragraph("<b>Metric</b>", self.styles['HealthTableCell']), Paragraph("<b>Value</b>", self.styles['HealthTableCell'])],
            [Paragraph("Total Monthly Rent", self.styles['HealthTableCell']), Paragraph(f"${float(report['total_monthly_rent']):,.2f}", self.styles['HealthTableCell'])],
            [Paragraph("Average Rent per SF", self.styles['HealthTableCell']), Paragraph(f"${float(report['avg_rent_per_sqft']):,.2f}", self.styles['HealthTableCell'])],
            [Paragraph("Total Portfolio SF", self.styles['HealthTableCell']), Paragraph(f"{report['total_portfolio_sqft']:,}", self.styles['HealthTableCell'])],
        ]
        
        financial_table = Table(financial_data, colWidths=[4*inch, 2.5*inch])
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(financial_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Critical Dates Summary
        dates_header = Paragraph("Critical Dates Summary", self.styles['SectionHeader'])
        elements.append(dates_header)
        
        dates_data = [
            [Paragraph("<b>Timeframe</b>", self.styles['HealthTableCell']), Paragraph("<b>Count</b>", self.styles['HealthTableCell'])],
            [Paragraph("Next 30 Days", self.styles['HealthTableCell']), Paragraph(str(report['critical_dates_30_days']), self.styles['HealthTableCell'])],
            [Paragraph("Next 60 Days", self.styles['HealthTableCell']), Paragraph(str(report['critical_dates_60_days']), self.styles['HealthTableCell'])],
            [Paragraph("Next 90 Days", self.styles['HealthTableCell']), Paragraph(str(report['critical_dates_90_days']), self.styles['HealthTableCell'])],
        ]
        
        dates_table = Table(dates_data, colWidths=[4*inch, 2.5*inch])
        dates_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(dates_table)
        
        return elements
    
    def _create_actions_page(self, report: Dict, actions: List[Dict]) -> List:
        """Create recommended actions and anomalies page"""
        
        elements = []
        
        # Anomalies Summary
        anomalies_header = Paragraph("Detected Anomalies", self.styles['SectionHeader'])
        elements.append(anomalies_header)
        
        anomalies_data = [
            [Paragraph("<b>Severity</b>", self.styles['HealthTableCell']), Paragraph("<b>Count</b>", self.styles['HealthTableCell'])],
            [Paragraph("Total Anomalies", self.styles['HealthTableCell']), Paragraph(str(report['anomalies_detected']), self.styles['HealthTableCell'])],
            [Paragraph("High/Critical Priority", self.styles['HealthTableCell']), Paragraph(str(report['high_severity_anomalies']), self.styles['HealthTableCell'])],
        ]
        
        anomalies_table = Table(anomalies_data, colWidths=[4*inch, 2.5*inch])
        anomalies_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(anomalies_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Recommended Actions
        actions_header = Paragraph("Recommended Actions", self.styles['SectionHeader'])
        elements.append(actions_header)
        
        if actions:
            # Build actions table
            actions_data = [
                [
                    Paragraph("<b>Priority</b>", self.styles['HealthTableCell']),
                    Paragraph("<b>Action</b>", self.styles['HealthTableCell']),
                    Paragraph("<b>Description</b>", self.styles['HealthTableCell'])
                ]
            ]
            
            priority_icons = {1: "🔴 HIGH", 2: "🟡 MEDIUM", 3: "🟢 LOW"}
            
            for action in actions[:10]:  # Top 10 actions
                priority_text = priority_icons.get(action['priority'], "⚪ NORMAL")
                
                actions_data.append([
                    Paragraph(priority_text, self.styles['HealthTableCell']),
                    Paragraph(action['title'], self.styles['HealthTableCell']),
                    Paragraph(action['description'], self.styles['SmallText'])
                ])
            
            actions_table = Table(actions_data, colWidths=[1*inch, 2.3*inch, 3.2*inch])
            actions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(actions_table)
        else:
            no_actions = Paragraph("✅ No specific actions required at this time. Your portfolio is well-maintained.", self.styles['Normal'])
            elements.append(no_actions)
        
        return elements
    
    def _create_footer(self) -> List:
        """Create report footer"""
        
        elements = []
        
        elements.append(Spacer(1, 0.5*inch))
        
        footer_text = f"""
        <para align='center'>
        <font size='9' color='grey'>
        Generated by LeaseAI Portfolio Health Monitor<br/>
        Report Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>
        © {datetime.now().year} LeaseAI - Automated Portfolio Intelligence
        </font>
        </para>
        """
        
        footer = Paragraph(footer_text, self.styles['SmallText'])
        elements.append(footer)
        
        return elements


# Convenience function
def generate_health_report_pdf(report_data: Dict, actions: List[Dict], output_path: str) -> str:
    """Generate portfolio health report PDF"""
    generator = PortfolioHealthPDFReport()
    return generator.generate_report(report_data, actions, output_path)
