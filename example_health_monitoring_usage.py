"""
LeaseAI - Portfolio Health Monitoring Example Script
Phase 6: Agentic AI Layer - Session 2

This script demonstrates how to use the automated monitoring system components.
"""

import os
from datetime import datetime
from supabase import create_client

# Import LeaseAI modules
from anomaly_detection_engine import scan_portfolio_for_anomalies
from health_report_generator import generate_health_report
from health_report_pdf import generate_health_report_pdf
from health_report_emailer import HealthReportEmailer


def example_full_workflow():
    """
    Complete workflow example:
    1. Scan portfolio for anomalies
    2. Generate health report
    3. Generate PDF
    4. Send email notification
    """
    
    print("=" * 60)
    print("LeaseAI Portfolio Health Monitoring - Full Workflow Example")
    print("=" * 60)
    
    # Initialize Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
    
    if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_KEY]):
        print("❌ Missing environment variables")
        print("   Required: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY")
        return
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Example client ID (replace with actual client UUID)
    client_id = "your-client-uuid-here"
    
    print(f"\n📂 Processing client: {client_id}\n")
    
    # Step 1: Scan for anomalies
    print("Step 1/4: Scanning portfolio for anomalies...")
    scan_results = scan_portfolio_for_anomalies(sb, client_id)
    
    print(f"✓ Scan complete!")
    print(f"  - Leases scanned: {scan_results['leases_scanned']}")
    print(f"  - Anomalies detected: {scan_results['anomalies_detected']}")
    print(f"  - Critical: {scan_results['by_severity']['CRITICAL']}")
    print(f"  - High: {scan_results['by_severity']['HIGH']}\n")
    
    # Step 2: Generate health report
    print("Step 2/4: Generating AI health report...")
    report_result = generate_health_report(sb, OPENAI_KEY, client_id)
    
    report_id = report_result['report_id']
    report_data = report_result['report_data']
    actions = report_result['actions']
    
    print(f"✓ Health report generated: {report_id}")
    print(f"  - Health Score: {report_data['health_score']}/100")
    print(f"  - Status: {report_data['health_status']}")
    print(f"  - Recommended Actions: {len(actions)}\n")
    
    # Step 3: Generate PDF
    print("Step 3/4: Generating PDF report...")
    pdf_filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    generate_health_report_pdf(report_data, actions, pdf_filename)
    
    print(f"✓ PDF generated: {pdf_filename}\n")
    
    # Step 4: Send email (optional - requires SMTP config)
    smtp_config = {
        'host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
        'port': int(os.environ.get('SMTP_PORT', 587)),
        'username': os.environ.get('SMTP_USERNAME'),
        'password': os.environ.get('SMTP_PASSWORD'),
        'from_email': os.environ.get('SMTP_FROM_EMAIL'),
        'from_name': 'LeaseAI Portfolio Monitor'
    }
    
    if all([smtp_config['username'], smtp_config['password'], smtp_config['from_email']]):
        print("Step 4/4: Sending email notification...")
        
        emailer = HealthReportEmailer(sb, smtp_config)
        
        # Replace with actual recipient
        recipient_email = "client@example.com"
        recipient_name = "John Doe"
        
        success = emailer.send_weekly_health_report(
            report_id=report_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            pdf_path=pdf_filename
        )
        
        if success:
            print(f"✓ Email sent to {recipient_email}\n")
        else:
            print(f"❌ Failed to send email to {recipient_email}\n")
    else:
        print("Step 4/4: Email notification skipped (SMTP not configured)\n")
    
    print("=" * 60)
    print("✅ Workflow complete!")
    print("=" * 60)


def example_anomaly_scan_only():
    """Example: Scan portfolio for anomalies only"""
    
    print("\n📊 Example: Anomaly Scan Only\n")
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    client_id = "your-client-uuid-here"
    
    # Run scan
    results = scan_portfolio_for_anomalies(sb, client_id)
    
    print(f"Anomalies by type:")
    for anom_type, count in results['by_type'].items():
        print(f"  - {anom_type.replace('_', ' ').title()}: {count}")


def example_send_critical_alert():
    """Example: Send critical anomaly alert email"""
    
    print("\n🚨 Example: Send Critical Alert\n")
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    smtp_config = {
        'host': os.environ.get('SMTP_HOST'),
        'port': int(os.environ.get('SMTP_PORT', 587)),
        'username': os.environ.get('SMTP_USERNAME'),
        'password': os.environ.get('SMTP_PASSWORD'),
        'from_email': os.environ.get('SMTP_FROM_EMAIL'),
        'from_name': 'LeaseAI Alerts'
    }
    
    emailer = HealthReportEmailer(sb, smtp_config)
    
    # Get first critical anomaly
    anomalies = sb.table("lease_anomalies").select("*").eq("severity", "CRITICAL").eq("status", "OPEN").limit(1).execute()
    
    if anomalies.data:
        anomaly = anomalies.data[0]
        
        success = emailer.send_critical_anomaly_alert(
            anomaly_id=anomaly['id'],
            recipient_email="admin@example.com",
            recipient_name="Portfolio Manager"
        )
        
        if success:
            print(f"✓ Critical alert sent for: {anomaly['title']}")
        else:
            print("❌ Failed to send alert")
    else:
        print("ℹ️ No critical anomalies found")


def example_pdf_generation_only():
    """Example: Generate PDF from existing health report"""
    
    print("\n📄 Example: PDF Generation Only\n")
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get most recent health report
    report_response = sb.table("portfolio_health_reports").select("*").order("report_date", desc=True).limit(1).execute()
    
    if not report_response.data:
        print("❌ No health reports found")
        return
    
    report = report_response.data[0]
    
    # Get actions
    actions_response = sb.table("health_report_actions").select("*").eq("health_report_id", report['id']).execute()
    actions = actions_response.data if actions_response.data else []
    
    # Generate PDF
    pdf_filename = f"health_report_{report['report_date']}.pdf"
    generate_health_report_pdf(report, actions, pdf_filename)
    
    print(f"✓ PDF generated: {pdf_filename}")
    print(f"  - Health Score: {report['health_score']}/100")
    print(f"  - Report Date: {report['report_date']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LeaseAI Portfolio Health Monitoring Examples")
    parser.add_argument('--example', type=str, choices=['full', 'scan', 'alert', 'pdf'], 
                       default='full',
                       help='Which example to run')
    
    args = parser.parse_args()
    
    if args.example == 'full':
        example_full_workflow()
    elif args.example == 'scan':
        example_anomaly_scan_only()
    elif args.example == 'alert':
        example_send_critical_alert()
    elif args.example == 'pdf':
        example_pdf_generation_only()
