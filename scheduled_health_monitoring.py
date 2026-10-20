"""
LeaseAI - Scheduled Portfolio Health Monitoring
Phase 6: Agentic AI Layer - Session 2

Background job runner for automated portfolio monitoring:
- Weekly health report generation
- Daily anomaly scanning
- Critical alert notifications
- Deadline reminders

Run this script via cron or scheduler:
- Daily: python scheduled_health_monitoring.py --task daily_scan
- Weekly: python scheduled_health_monitoring.py --task weekly_report
"""

import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, List
import os

# Supabase and OpenAI imports
from supabase import create_client

# LeaseAI module imports
from anomaly_detection_engine import scan_portfolio_for_anomalies, get_active_anomalies
from health_report_generator import generate_health_report
from health_report_emailer import HealthReportEmailer, send_critical_alert, send_deadline_reminder
from health_report_pdf import generate_health_report_pdf


class ScheduledHealthMonitor:
    """
    Manages scheduled portfolio health monitoring tasks
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, openai_key: str, smtp_config: Dict):
        """
        Initialize scheduler
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key
            openai_key: OpenAI API key
            smtp_config: SMTP configuration dictionary
        """
        self.sb = create_client(supabase_url, supabase_key)
        self.openai_key = openai_key
        self.smtp_config = smtp_config
        self.emailer = HealthReportEmailer(self.sb, smtp_config)
    
    def run_daily_scan(self):
        """
        Daily anomaly scan and critical alert notification
        Run this task once per day (recommended: early morning)
        """
        
        print("=" * 60)
        print(f"🔍 DAILY PORTFOLIO SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Get all active clients
        clients_response = self.sb.table("leases").select("uploaded_by").execute()
        
        if not clients_response.data:
            print("ℹ️ No clients found")
            return
        
        # Get unique client IDs
        client_ids = list(set([lease['uploaded_by'] for lease in clients_response.data]))
        
        print(f"📊 Scanning {len(client_ids)} client portfolios...\n")
        
        for client_id in client_ids:
            print(f"📂 Client: {client_id}")
            
            try:
                # Scan for anomalies
                scan_results = scan_portfolio_for_anomalies(self.sb, client_id)
                
                print(f"   ✓ Anomalies detected: {scan_results['anomalies_detected']}")
                print(f"   ✓ Critical/High: {scan_results['by_severity']['CRITICAL']} / {scan_results['by_severity']['HIGH']}")
                
                # Send alerts for new critical/high anomalies
                self._send_critical_alerts(client_id, scan_results)
                
                # Check for upcoming deadlines and send reminders
                self._send_deadline_reminders(client_id)
                
                print(f"   ✅ Scan complete for client {client_id}\n")
            
            except Exception as e:
                print(f"   ❌ Error scanning client {client_id}: {str(e)}\n")
        
        print("=" * 60)
        print(f"✅ Daily scan complete - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def run_weekly_report(self):
        """
        Weekly health report generation and email delivery
        Run this task once per week (recommended: Monday morning)
        """
        
        print("=" * 60)
        print(f"📊 WEEKLY HEALTH REPORT GENERATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Get all active clients
        clients_response = self.sb.table("leases").select("uploaded_by").execute()
        
        if not clients_response.data:
            print("ℹ️ No clients found")
            return
        
        # Get unique client IDs
        client_ids = list(set([lease['uploaded_by'] for lease in clients_response.data]))
        
        print(f"📊 Generating reports for {len(client_ids)} clients...\n")
        
        for client_id in client_ids:
            print(f"📂 Client: {client_id}")
            
            try:
                # First, run anomaly scan to ensure fresh data
                print("   Step 1/4: Scanning for anomalies...")
                scan_results = scan_portfolio_for_anomalies(self.sb, client_id)
                
                # Generate health report
                print("   Step 2/4: Generating health report...")
                report_result = generate_health_report(self.sb, self.openai_key, client_id)
                report_id = report_result['report_id']
                report_data = report_result['report_data']
                actions = report_result['actions']
                
                print(f"   ✓ Report generated: {report_id}")
                print(f"   ✓ Health Score: {report_data['health_score']}/100 ({report_data['health_status']})")
                
                # Generate PDF
                print("   Step 3/4: Generating PDF report...")
                pdf_path = f"/tmp/health_report_{client_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                generate_health_report_pdf(report_data, actions, pdf_path)
                print(f"   ✓ PDF generated: {pdf_path}")
                
                # Send email
                print("   Step 4/4: Sending email notification...")
                recipient_email, recipient_name = self._get_client_email(client_id)
                
                if recipient_email:
                    success = self.emailer.send_weekly_health_report(
                        report_id=report_id,
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        pdf_path=pdf_path
                    )
                    
                    if success:
                        print(f"   ✓ Email sent to {recipient_email}")
                    else:
                        print(f"   ⚠️ Failed to send email to {recipient_email}")
                else:
                    print("   ⚠️ No email configured for client, skipping notification")
                
                # Clean up temp PDF
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                
                print(f"   ✅ Weekly report complete for client {client_id}\n")
            
            except Exception as e:
                print(f"   ❌ Error generating report for client {client_id}: {str(e)}\n")
        
        print("=" * 60)
        print(f"✅ Weekly reports complete - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def run_monthly_cleanup(self):
        """
        Monthly cleanup and archiving
        Run this task once per month (recommended: first day of month)
        """
        
        print("=" * 60)
        print(f"🗄️ MONTHLY CLEANUP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Archive old resolved anomalies (older than 90 days)
        cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()
        
        try:
            # Update old resolved anomalies to ARCHIVED status
            result = self.sb.table("lease_anomalies").update({
                'status': 'ARCHIVED'
            }).eq('status', 'RESOLVED').lt('resolved_at', cutoff_date).execute()
            
            archived_count = len(result.data) if result.data else 0
            print(f"✓ Archived {archived_count} old resolved anomalies")
        
        except Exception as e:
            print(f"❌ Error archiving anomalies: {str(e)}")
        
        # Archive old dismissed anomalies
        try:
            result = self.sb.table("lease_anomalies").update({
                'status': 'ARCHIVED'
            }).eq('status', 'DISMISSED').lt('detected_at', cutoff_date).execute()
            
            archived_count = len(result.data) if result.data else 0
            print(f"✓ Archived {archived_count} old dismissed anomalies")
        
        except Exception as e:
            print(f"❌ Error archiving dismissed anomalies: {str(e)}")
        
        # Clean up old notification logs (older than 6 months)
        log_cutoff = (datetime.now() - timedelta(days=180)).isoformat()
        
        try:
            result = self.sb.table("notification_log").delete().lt('sent_at', log_cutoff).execute()
            print(f"✓ Cleaned up old notification logs")
        
        except Exception as e:
            print(f"❌ Error cleaning notification logs: {str(e)}")
        
        print("=" * 60)
        print(f"✅ Monthly cleanup complete - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def _send_critical_alerts(self, client_id: str, scan_results: Dict):
        """Send email alerts for newly detected critical/high anomalies"""
        
        # Get critical/high anomalies that haven't been alerted yet
        anomalies_response = self.sb.table("lease_anomalies").select("*, leases(uploaded_by)").eq("leases.uploaded_by", client_id).in_("severity", ["CRITICAL", "HIGH"]).eq("alert_sent", False).execute()
        
        new_anomalies = anomalies_response.data if anomalies_response.data else []
        
        if not new_anomalies:
            print("   ℹ️ No new critical alerts to send")
            return
        
        print(f"   📧 Sending {len(new_anomalies)} critical alerts...")
        
        # Get client email
        recipient_email, recipient_name = self._get_client_email(client_id)
        
        if not recipient_email:
            print("   ⚠️ No email configured, skipping alerts")
            return
        
        # Send alert for each critical anomaly
        for anomaly in new_anomalies:
            try:
                self.emailer.send_critical_anomaly_alert(
                    anomaly_id=anomaly['id'],
                    recipient_email=recipient_email,
                    recipient_name=recipient_name
                )
            except Exception as e:
                print(f"   ⚠️ Failed to send alert for anomaly {anomaly['id']}: {str(e)}")
    
    def _send_deadline_reminders(self, client_id: str):
        """Send reminders for approaching deadlines (7, 14, 30 days out)"""
        
        # Get leases for this client
        leases_response = self.sb.table("leases").select("id").eq("uploaded_by", client_id).neq("status", "DELETED").execute()
        lease_ids = [l['id'] for l in (leases_response.data or [])]
        
        if not lease_ids:
            return
        
        # Critical date fields
        critical_fields = ['Lease Expiration Date', 'Renewal Option Deadline', 'Renewal Notice Deadline', 'Termination Notice Deadline']
        
        today = datetime.now().date()
        reminder_days = [7, 14, 30]  # Send reminders at these thresholds
        
        recipient_email, recipient_name = self._get_client_email(client_id)
        
        if not recipient_email:
            return
        
        reminders_sent = 0
        
        for lease_id in lease_ids:
            fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease_id).in_("field_name", critical_fields).execute()
            
            for field in (fields_response.data or []):
                date_str = field.get('reviewed_value') or field.get('raw_value')
                
                if date_str and date_str != 'NOT FOUND':
                    try:
                        from anomaly_detection_engine import AnomalyDetectionEngine
                        engine = AnomalyDetectionEngine(self.sb)
                        deadline_date = engine._parse_date(date_str)
                        
                        if deadline_date:
                            days_until = (deadline_date - today).days
                            
                            # Send reminder if we're at a threshold (7, 14, or 30 days)
                            if days_until in reminder_days:
                                try:
                                    self.emailer.send_deadline_reminder(
                                        lease_id=lease_id,
                                        field_name=field['field_name'],
                                        deadline_date=deadline_date,
                                        days_until=days_until,
                                        recipient_email=recipient_email,
                                        recipient_name=recipient_name
                                    )
                                    reminders_sent += 1
                                except Exception as e:
                                    pass  # Continue with other reminders
                    except:
                        pass
        
        if reminders_sent > 0:
            print(f"   ✓ Sent {reminders_sent} deadline reminders")
    
    def _get_client_email(self, client_id: str) -> tuple:
        """
        Get client email and name from database
        
        Returns:
            Tuple of (email, name) or (None, None) if not found
        """
        
        try:
            # In a real system, you'd have a clients/users table
            # For now, we'll try to get from Supabase auth or use a placeholder
            # This is a stub - implement based on your auth system
            
            # Placeholder: return None to skip email sending in development
            # In production, implement proper client email lookup:
            # client_response = self.sb.table("clients").select("email, name").eq("id", client_id).execute()
            # if client_response.data:
            #     client = client_response.data[0]
            #     return (client['email'], client.get('name'))
            
            return (None, None)
        
        except Exception as e:
            print(f"   ⚠️ Error getting client email: {str(e)}")
            return (None, None)


def main():
    """Main entry point for scheduled tasks"""
    
    parser = argparse.ArgumentParser(description="LeaseAI Scheduled Portfolio Health Monitoring")
    parser.add_argument('--task', type=str, required=True, 
                       choices=['daily_scan', 'weekly_report', 'monthly_cleanup'],
                       help='Task to run')
    
    args = parser.parse_args()
    
    # Load configuration from environment variables
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
    
    # SMTP configuration
    smtp_config = {
        'host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
        'port': int(os.environ.get('SMTP_PORT', 587)),
        'username': os.environ.get('SMTP_USERNAME'),
        'password': os.environ.get('SMTP_PASSWORD'),
        'from_email': os.environ.get('SMTP_FROM_EMAIL'),
        'from_name': os.environ.get('SMTP_FROM_NAME', 'LeaseAI Portfolio Monitor')
    }
    
    # Validate configuration
    if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_KEY]):
        print("❌ Error: Missing required environment variables")
        print("   Required: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY")
        sys.exit(1)
    
    if not all([smtp_config['username'], smtp_config['password'], smtp_config['from_email']]):
        print("⚠️ Warning: SMTP not fully configured, email notifications will be skipped")
    
    # Initialize monitor
    monitor = ScheduledHealthMonitor(SUPABASE_URL, SUPABASE_KEY, OPENAI_KEY, smtp_config)
    
    # Run requested task
    if args.task == 'daily_scan':
        monitor.run_daily_scan()
    elif args.task == 'weekly_report':
        monitor.run_weekly_report()
    elif args.task == 'monthly_cleanup':
        monitor.run_monthly_cleanup()


if __name__ == "__main__":
    main()
