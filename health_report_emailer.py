"""
LeaseAI - Portfolio Health Report Email Notification System
Phase 6: Agentic AI Layer - Session 2

Sends automated email notifications:
- Weekly portfolio health reports
- Critical anomaly alerts
- Upcoming deadline reminders
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os


class HealthReportEmailer:
    """
    Sends email notifications for portfolio health reports and alerts
    """
    
    def __init__(self, supabase_client, smtp_config: Dict):
        """
        Initialize emailer
        
        Args:
            supabase_client: Supabase client instance
            smtp_config: Dictionary with SMTP settings:
                - host: SMTP server hostname
                - port: SMTP server port
                - username: SMTP auth username
                - password: SMTP auth password
                - from_email: Sender email address
                - from_name: Sender display name
        """
        self.sb = supabase_client
        self.smtp_host = smtp_config.get('host', 'smtp.gmail.com')
        self.smtp_port = smtp_config.get('port', 587)
        self.smtp_user = smtp_config.get('username')
        self.smtp_password = smtp_config.get('password')
        self.from_email = smtp_config.get('from_email')
        self.from_name = smtp_config.get('from_name', 'LeaseAI Portfolio Monitor')
    
    def send_weekly_health_report(self, report_id: str, recipient_email: str, recipient_name: str = None, pdf_path: str = None) -> bool:
        """
        Send weekly health report email
        
        Args:
            report_id: UUID of the health report
            recipient_email: Email address to send to
            recipient_name: Recipient name (optional)
            pdf_path: Path to PDF report attachment (optional)
            
        Returns:
            True if sent successfully
        """
        
        print(f"📧 Preparing weekly health report email for {recipient_email}...")
        
        # Get report data
        report_response = self.sb.table("portfolio_health_reports").select("*").eq("id", report_id).execute()
        
        if not report_response.data:
            print(f"❌ Report {report_id} not found")
            return False
        
        report = report_response.data[0]
        
        # Get action items
        actions_response = self.sb.table("health_report_actions").select("*").eq("health_report_id", report_id).order("priority").execute()
        actions = actions_response.data if actions_response.data else []
        
        # Build email
        subject = f"📊 Portfolio Health Report - Week of {report['report_date']} (Score: {report['health_score']}/100)"
        
        html_body = self._generate_weekly_report_html(report, actions, recipient_name)
        
        # Send email
        success = self._send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            html_body=html_body,
            pdf_attachment=pdf_path
        )
        
        if success:
            # Log notification
            self._log_notification(
                client_id=report['client_id'],
                notification_type='WEEKLY_REPORT',
                recipient_email=recipient_email,
                subject=subject,
                related_id=report_id
            )
            print(f"✅ Weekly report email sent to {recipient_email}")
        
        return success
    
    def send_critical_anomaly_alert(self, anomaly_id: str, recipient_email: str, recipient_name: str = None) -> bool:
        """
        Send immediate alert for critical anomaly
        
        Args:
            anomaly_id: UUID of the anomaly
            recipient_email: Email address
            recipient_name: Recipient name (optional)
            
        Returns:
            True if sent successfully
        """
        
        print(f"🚨 Sending critical anomaly alert to {recipient_email}...")
        
        # Get anomaly data
        anomaly_response = self.sb.table("lease_anomalies").select("*, leases(property_address, tenant_name)").eq("id", anomaly_id).execute()
        
        if not anomaly_response.data:
            print(f"❌ Anomaly {anomaly_id} not found")
            return False
        
        anomaly = anomaly_response.data[0]
        lease_info = anomaly.get('leases', {})
        
        # Build email
        subject = f"🚨 CRITICAL ALERT: {anomaly['title']}"
        
        html_body = self._generate_anomaly_alert_html(anomaly, lease_info, recipient_name)
        
        # Send email
        success = self._send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            html_body=html_body
        )
        
        if success:
            # Log notification
            self._log_notification(
                client_id=None,  # Will need to fetch from lease
                notification_type='CRITICAL_ALERT',
                recipient_email=recipient_email,
                subject=subject,
                related_id=anomaly_id
            )
            
            # Mark anomaly as alerted
            self.sb.table("lease_anomalies").update({
                'alert_sent': True,
                'alert_sent_at': datetime.now().isoformat()
            }).eq("id", anomaly_id).execute()
            
            print(f"✅ Critical alert sent to {recipient_email}")
        
        return success
    
    def send_deadline_reminder(self, lease_id: str, field_name: str, deadline_date: datetime, days_until: int, recipient_email: str, recipient_name: str = None) -> bool:
        """
        Send reminder for upcoming critical date
        
        Args:
            lease_id: UUID of the lease
            field_name: Name of the critical date field
            deadline_date: The deadline date
            days_until: Days until deadline
            recipient_email: Email address
            recipient_name: Recipient name (optional)
            
        Returns:
            True if sent successfully
        """
        
        print(f"📅 Sending deadline reminder to {recipient_email}...")
        
        # Get lease data
        lease_response = self.sb.table("leases").select("*").eq("id", lease_id).execute()
        
        if not lease_response.data:
            print(f"❌ Lease {lease_id} not found")
            return False
        
        lease = lease_response.data[0]
        
        # Build email
        urgency = "URGENT" if days_until <= 7 else "IMPORTANT" if days_until <= 30 else "REMINDER"
        subject = f"⏰ {urgency}: {field_name} in {days_until} days"
        
        html_body = self._generate_deadline_reminder_html(lease, field_name, deadline_date, days_until, recipient_name)
        
        # Send email
        success = self._send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=subject,
            html_body=html_body
        )
        
        if success:
            # Log notification
            self._log_notification(
                client_id=lease['uploaded_by'],
                notification_type='DEADLINE_REMINDER',
                recipient_email=recipient_email,
                subject=subject,
                related_id=lease_id
            )
            print(f"✅ Deadline reminder sent to {recipient_email}")
        
        return success
    
    def _send_email(self, to_email: str, subject: str, html_body: str, to_name: str = None, pdf_attachment: str = None) -> bool:
        """
        Send email via SMTP
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML email body
            to_name: Recipient name (optional)
            pdf_attachment: Path to PDF file to attach (optional)
            
        Returns:
            True if sent successfully
        """
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Attach PDF if provided
            if pdf_attachment and os.path.exists(pdf_attachment):
                with open(pdf_attachment, 'rb') as f:
                    pdf_part = MIMEApplication(f.read(), _subtype='pdf')
                    pdf_part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_attachment))
                    msg.attach(pdf_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            return False
    
    def _generate_weekly_report_html(self, report: Dict, actions: List[Dict], recipient_name: str = None) -> str:
        """Generate HTML email body for weekly report"""
        
        greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
        
        # Health status styling
        health_status_colors = {
            'EXCELLENT': '#2e7d32',
            'GOOD': '#7cb342',
            'NEEDS_ATTENTION': '#f57c00',
            'CRITICAL': '#c62828'
        }
        health_color = health_status_colors.get(report['health_status'], '#757575')
        
        # Build actions list
        actions_html = ""
        priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
        
        for action in actions[:5]:  # Top 5 actions
            icon = priority_icons.get(action['priority'], "⚪")
            actions_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px;">
                <strong>{icon} {action['title']}</strong><br/>
                <span style="color: #666;">{action['description']}</span>
            </div>
            """
        
        if not actions_html:
            actions_html = "<p style='color: #666;'>No specific actions required at this time.</p>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
                .score-box {{ text-align: center; margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 8px; }}
                .score {{ font-size: 48px; font-weight: bold; color: {health_color}; }}
                .status {{ font-size: 20px; font-weight: 600; color: {health_color}; }}
                .metrics {{ display: table; width: 100%; margin: 20px 0; }}
                .metric {{ display: table-cell; text-align: center; padding: 15px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .section {{ margin: 25px 0; }}
                .section-title {{ font-size: 18px; font-weight: 600; margin-bottom: 10px; color: #333; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
                a {{ color: #667eea; text-decoration: none; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🏥 Portfolio Health Report</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Week of {report['report_date']}</p>
                </div>
                
                <div class="content">
                    <p>{greeting}</p>
                    
                    <p>Here's your weekly portfolio health report:</p>
                    
                    <div class="score-box">
                        <div class="score">{report['health_score']}/100</div>
                        <div class="status">{report['health_status']}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">📊 Executive Summary</div>
                        <p style="color: #555;">{report['executive_summary']}</p>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">📈 Key Metrics</div>
                        <div class="metrics">
                            <div class="metric">
                                <div class="metric-value">{report['active_leases']}</div>
                                <div class="metric-label">Active Leases</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${float(report['total_monthly_rent']):,.0f}</div>
                                <div class="metric-label">Monthly Rent</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">{report['anomalies_detected']}</div>
                                <div class="metric-label">Anomalies</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">📅 Critical Dates</div>
                        <p>
                            <strong>{report['critical_dates_30_days']}</strong> deadlines in next 30 days<br/>
                            <strong>{report['critical_dates_60_days']}</strong> deadlines in next 60 days<br/>
                            <strong>{report['critical_dates_90_days']}</strong> deadlines in next 90 days
                        </p>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">✅ Recommended Actions</div>
                        {actions_html}
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://leaseai.app/portfolio-health" class="button">View Full Report</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated report from LeaseAI Portfolio Monitor</p>
                    <p><a href="#">Unsubscribe</a> | <a href="#">Manage Preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_anomaly_alert_html(self, anomaly: Dict, lease_info: Dict, recipient_name: str = None) -> str:
        """Generate HTML email body for critical anomaly alert"""
        
        greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
        
        # Severity styling
        severity_colors = {
            'CRITICAL': '#c62828',
            'HIGH': '#f57c00',
            'MEDIUM': '#fbc02d',
            'LOW': '#7cb342'
        }
        severity_color = severity_colors.get(anomaly['severity'], '#757575')
        
        property_address = lease_info.get('property_address', 'Unknown Property')
        tenant_name = lease_info.get('tenant_name', 'Unknown Tenant')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {severity_color}; color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
                .alert-box {{ background: #fff3cd; border: 2px solid #ffc107; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .detail-row {{ margin: 10px 0; }}
                .label {{ font-weight: 600; color: #555; }}
                .value {{ color: #333; }}
                .button {{ display: inline-block; padding: 12px 24px; background: {severity_color}; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🚨 CRITICAL ALERT</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Immediate Attention Required</p>
                </div>
                
                <div class="content">
                    <p>{greeting}</p>
                    
                    <div class="alert-box">
                        <h2 style="margin-top: 0; color: {severity_color};">{anomaly['title']}</h2>
                        <p style="margin: 0;"><strong>Severity:</strong> {anomaly['severity']}</p>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Property:</span>
                        <span class="value">{property_address}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Tenant:</span>
                        <span class="value">{tenant_name}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Issue Type:</span>
                        <span class="value">{anomaly['anomaly_type'].replace('_', ' ').title()}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="label">Detected:</span>
                        <span class="value">{datetime.fromisoformat(anomaly['detected_at']).strftime('%B %d, %Y at %I:%M %p')}</span>
                    </div>
                    
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
                    
                    <h3>Details</h3>
                    <p>{anomaly['description']}</p>
                    
                    {f'<p><strong>Field:</strong> {anomaly["field_name"]}</p>' if anomaly.get('field_name') else ''}
                    
                    {f'<p><strong>Expected:</strong> {anomaly["expected_value"]}<br/><strong>Actual:</strong> {anomaly["actual_value"]}</p>' if anomaly.get('expected_value') and anomaly.get('actual_value') else ''}
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://leaseai.app/lease-review?id={anomaly['lease_id']}" class="button">Review Lease Now</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from LeaseAI Portfolio Monitor</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_deadline_reminder_html(self, lease: Dict, field_name: str, deadline_date: datetime, days_until: int, recipient_name: str = None) -> str:
        """Generate HTML email body for deadline reminder"""
        
        greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
        
        urgency_color = '#c62828' if days_until <= 7 else '#f57c00' if days_until <= 30 else '#fbc02d'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {urgency_color}; color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
                .countdown {{ text-align: center; margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 8px; }}
                .days {{ font-size: 48px; font-weight: bold; color: {urgency_color}; }}
                .button {{ display: inline-block; padding: 12px 24px; background: {urgency_color}; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">⏰ Deadline Reminder</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">{field_name}</p>
                </div>
                
                <div class="content">
                    <p>{greeting}</p>
                    
                    <p>This is a reminder that an important deadline is approaching for one of your leases:</p>
                    
                    <div class="countdown">
                        <div class="days">{days_until}</div>
                        <div>Days Until Deadline</div>
                    </div>
                    
                    <p>
                        <strong>Property:</strong> {lease.get('property_address', 'N/A')}<br/>
                        <strong>Tenant:</strong> {lease.get('tenant_name', 'N/A')}<br/>
                        <strong>Deadline Type:</strong> {field_name}<br/>
                        <strong>Deadline Date:</strong> {deadline_date.strftime('%B %d, %Y')}
                    </p>
                    
                    <p style="background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107;">
                        <strong>⚠️ Action Required:</strong> Please review this lease and take appropriate action before the deadline.
                    </p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://leaseai.app/lease-review?id={lease['id']}" class="button">Review Lease</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated reminder from LeaseAI Portfolio Monitor</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _log_notification(self, client_id: str, notification_type: str, recipient_email: str, subject: str, related_id: str = None):
        """Log sent notification to database"""
        
        try:
            notification_data = {
                'client_id': client_id,
                'notification_type': notification_type,
                'recipient_email': recipient_email,
                'subject': subject,
                'related_id': related_id,
                'sent_at': datetime.now().isoformat(),
                'status': 'SENT'
            }
            
            self.sb.table("notification_log").insert(notification_data).execute()
        
        except Exception as e:
            print(f"⚠️ Error logging notification: {str(e)}")


# Convenience functions
def send_weekly_report(supabase_client, smtp_config: Dict, report_id: str, recipient_email: str, recipient_name: str = None, pdf_path: str = None) -> bool:
    """Send weekly health report email"""
    emailer = HealthReportEmailer(supabase_client, smtp_config)
    return emailer.send_weekly_health_report(report_id, recipient_email, recipient_name, pdf_path)


def send_critical_alert(supabase_client, smtp_config: Dict, anomaly_id: str, recipient_email: str, recipient_name: str = None) -> bool:
    """Send critical anomaly alert email"""
    emailer = HealthReportEmailer(supabase_client, smtp_config)
    return emailer.send_critical_anomaly_alert(anomaly_id, recipient_email, recipient_name)


def send_deadline_reminder(supabase_client, smtp_config: Dict, lease_id: str, field_name: str, deadline_date: datetime, days_until: int, recipient_email: str, recipient_name: str = None) -> bool:
    """Send deadline reminder email"""
    emailer = HealthReportEmailer(supabase_client, smtp_config)
    return emailer.send_deadline_reminder(lease_id, field_name, deadline_date, days_until, recipient_email, recipient_name)
