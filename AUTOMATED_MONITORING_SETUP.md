# LeaseAI - Automated Portfolio Health Monitoring Setup Guide
## Phase 6: Agentic AI Layer - Session 2

This guide explains how to set up and configure the automated portfolio health monitoring system with email notifications, scheduled scans, and PDF report generation.

---

## 🎯 Overview

The automated monitoring system provides:

- **Daily Anomaly Scanning** - Detects critical issues across your portfolio
- **Weekly Health Reports** - AI-powered executive summaries with actionable insights
- **Email Notifications** - Automated delivery of reports and critical alerts
- **PDF Export** - Professional reports for stakeholders
- **Deadline Reminders** - Never miss a renewal or termination deadline
- **CAM Charge Monitoring** - Year-over-year trend analysis
- **ASC 842 Compliance Checks** - GAAP compliance validation

---

## 📋 Prerequisites

### 1. Database Setup

Run the SQL migration scripts to set up required tables:

```bash
# Core AI layer schema (if not already done)
psql -d your_database < database_schema_ai_layer.sql

# Notification system schema
psql -d your_database < database_schema_notification_system.sql
```

### 2. Environment Variables

Create a `.env` file or set the following environment variables:

```bash
# Supabase Configuration
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-role-key"

# OpenAI Configuration
export OPENAI_API_KEY="sk-your-openai-api-key"

# SMTP Email Configuration
export SMTP_HOST="smtp.gmail.com"  # or your SMTP server
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM_EMAIL="noreply@leaseai.app"
export SMTP_FROM_NAME="LeaseAI Portfolio Monitor"
```

#### Gmail SMTP Setup

If using Gmail:
1. Enable 2-factor authentication on your Google account
2. Generate an **App Password**: https://myaccount.google.com/apppasswords
3. Use the app password as `SMTP_PASSWORD`

#### Alternative SMTP Providers

- **SendGrid**: `smtp.sendgrid.net:587` (recommended for production)
- **AWS SES**: `email-smtp.us-east-1.amazonaws.com:587`
- **Mailgun**: `smtp.mailgun.org:587`
- **Office 365**: `smtp.office365.com:587`

### 3. Python Dependencies

Install required packages:

```bash
pip install supabase openai reportlab python-dotenv smtplib-ssl
```

---

## 🚀 Quick Start

### Manual Execution

Test the system by running tasks manually:

```bash
# Run daily anomaly scan
python scheduled_health_monitoring.py --task daily_scan

# Generate weekly health report
python scheduled_health_monitoring.py --task weekly_report

# Run monthly cleanup
python scheduled_health_monitoring.py --task monthly_cleanup
```

### Generate PDF Report (Standalone)

```python
from health_report_pdf import generate_health_report_pdf
from supabase import create_client

# Initialize Supabase
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Get most recent health report
report_response = sb.table("portfolio_health_reports").select("*").order("report_date", desc=True).limit(1).execute()
report = report_response.data[0]

# Get actions
actions_response = sb.table("health_report_actions").select("*").eq("health_report_id", report['id']).execute()
actions = actions_response.data

# Generate PDF
pdf_path = generate_health_report_pdf(report, actions, "health_report.pdf")
print(f"PDF saved to: {pdf_path}")
```

### Send Email Notification (Standalone)

```python
from health_report_emailer import send_weekly_report
from supabase import create_client

# SMTP config
smtp_config = {
    'host': 'smtp.gmail.com',
    'port': 587,
    'username': 'your-email@gmail.com',
    'password': 'your-app-password',
    'from_email': 'noreply@leaseai.app',
    'from_name': 'LeaseAI'
}

# Send report
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
send_weekly_report(
    supabase_client=sb,
    smtp_config=smtp_config,
    report_id="uuid-of-report",
    recipient_email="client@example.com",
    recipient_name="John Doe",
    pdf_path="health_report.pdf"
)
```

---

## ⏰ Automated Scheduling

### Option 1: Linux/macOS Cron

Edit your crontab:

```bash
crontab -e
```

Add the following entries:

```cron
# Daily anomaly scan at 6:00 AM
0 6 * * * cd /path/to/leaseai && /usr/bin/python3 scheduled_health_monitoring.py --task daily_scan >> /var/log/leaseai_daily.log 2>&1

# Weekly health report every Monday at 8:00 AM
0 8 * * 1 cd /path/to/leaseai && /usr/bin/python3 scheduled_health_monitoring.py --task weekly_report >> /var/log/leaseai_weekly.log 2>&1

# Monthly cleanup on the 1st of each month at 2:00 AM
0 2 1 * * cd /path/to/leaseai && /usr/bin/python3 scheduled_health_monitoring.py --task monthly_cleanup >> /var/log/leaseai_cleanup.log 2>&1
```

**Cron Time Format:**
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-6, Sunday=0)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Option 2: Windows Task Scheduler

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task**
3. Name: "LeaseAI Daily Scan"
4. Trigger: Daily at 6:00 AM
5. Action: Start a program
   - Program: `python.exe`
   - Arguments: `scheduled_health_monitoring.py --task daily_scan`
   - Start in: `C:\path\to\leaseai`

Repeat for weekly and monthly tasks.

### Option 3: Python `schedule` Library (Simple Development)

Create a `scheduler_daemon.py`:

```python
import schedule
import time
import subprocess

def run_daily_scan():
    subprocess.run(["python", "scheduled_health_monitoring.py", "--task", "daily_scan"])

def run_weekly_report():
    subprocess.run(["python", "scheduled_health_monitoring.py", "--task", "weekly_report"])

def run_monthly_cleanup():
    subprocess.run(["python", "scheduled_health_monitoring.py", "--task", "monthly_cleanup"])

# Schedule jobs
schedule.every().day.at("06:00").do(run_daily_scan)
schedule.every().monday.at("08:00").do(run_weekly_report)
schedule.every().month.at("02:00").do(run_monthly_cleanup)

print("📅 LeaseAI Scheduler started...")

while True:
    schedule.run_pending()
    time.sleep(60)
```

Run as a background service:

```bash
nohup python scheduler_daemon.py &
```

### Option 4: Cloud Functions (Production)

For production deployments, use serverless functions:

#### AWS Lambda

1. Package code: `zip -r leaseai_monitor.zip *.py`
2. Create Lambda function with Python 3.9+ runtime
3. Set environment variables in Lambda console
4. Create EventBridge rules for scheduled execution:
   - Daily: `cron(0 6 * * ? *)`
   - Weekly: `cron(0 8 ? * MON *)`

#### Google Cloud Functions

```bash
gcloud functions deploy portfolio_health_monitor \
  --runtime python39 \
  --trigger-topic daily-scan \
  --entry-point run_daily_scan \
  --set-env-vars SUPABASE_URL=xxx,OPENAI_API_KEY=yyy
```

#### Azure Functions

Use `TimerTrigger` binding in `function.json`:

```json
{
  "bindings": [{
    "type": "timerTrigger",
    "schedule": "0 0 6 * * *",
    "name": "timer"
  }]
}
```

---

## 📧 Email Notification Customization

### HTML Email Templates

Email templates are defined in `health_report_emailer.py`:

- **Weekly Report**: `_generate_weekly_report_html()`
- **Critical Alert**: `_generate_anomaly_alert_html()`
- **Deadline Reminder**: `_generate_deadline_reminder_html()`

Customize these methods to match your branding.

### Client Email Preferences

Store client notification preferences in the `client_notification_preferences` table:

```sql
INSERT INTO client_notification_preferences (
    client_id,
    email_address,
    display_name,
    weekly_health_reports,
    critical_anomaly_alerts,
    deadline_reminders,
    deadline_reminder_days
) VALUES (
    'uuid-of-client',
    'client@example.com',
    'John Doe',
    true,
    true,
    true,
    ARRAY[7, 14, 30]
);
```

### Notification Settings UI

Add to Streamlit settings page (`pages/11_🏥_Portfolio_Health.py` Tab 4):

```python
# In Tab 4: Settings
st.markdown("### Email Preferences")

# Get current preferences
prefs_response = sb.table("client_notification_preferences").select("*").eq("client_id", client_id).execute()
prefs = prefs_response.data[0] if prefs_response.data else {}

# Email input
email = st.text_input("Email Address", value=prefs.get('email_address', ''))

# Toggles
weekly_reports = st.checkbox("Weekly Health Reports", value=prefs.get('weekly_health_reports', True))
critical_alerts = st.checkbox("Critical Anomaly Alerts", value=prefs.get('critical_anomaly_alerts', True))
deadline_reminders = st.checkbox("Deadline Reminders", value=prefs.get('deadline_reminders', True))

# Save
if st.button("Save Preferences"):
    sb.table("client_notification_preferences").upsert({
        'client_id': client_id,
        'email_address': email,
        'weekly_health_reports': weekly_reports,
        'critical_anomaly_alerts': critical_alerts,
        'deadline_reminders': deadline_reminders
    }).execute()
    st.success("Preferences saved!")
```

---

## 🔍 Anomaly Detection Rules

### Built-in Detectors

1. **Critical Date Approaching** - 7/30/60/90 day thresholds
2. **Expired Lease Active** - Lease past expiration but still marked active
3. **Low Confidence Fields** - Fields requiring manual review
4. **Missing Critical Data** - Required fields not extracted
5. **Rent Escalation Mismatch** - Escalations >10%
6. **CAM Charge Spike** - YoY increase >15%
7. **ASC 842 Compliance Gap** - Missing required accounting fields

### Custom Detectors

Add custom anomaly checks by extending `AnomalyDetectionEngine` class:

```python
def _check_custom_rule(self, lease: Dict) -> List[Dict]:
    """Your custom anomaly detector"""
    anomalies = []
    
    # Your detection logic here
    if some_condition:
        anomalies.append({
            'anomaly_type': 'CUSTOM_RULE',
            'severity': 'HIGH',
            'title': 'Issue detected',
            'description': 'Detailed description',
            'field_name': 'Field Name',
            'expected_value': 'Expected',
            'actual_value': 'Actual'
        })
    
    return anomalies
```

Add to scan in `scan_portfolio()`:

```python
anomalies.extend(self._check_custom_rule(lease))
```

---

## 📊 Monitoring & Logs

### View Notification History

```sql
-- Recent notifications sent
SELECT 
    notification_type,
    recipient_email,
    subject,
    sent_at,
    status
FROM notification_log
ORDER BY sent_at DESC
LIMIT 50;

-- Notification stats by type
SELECT 
    notification_type,
    COUNT(*) as total_sent,
    COUNT(CASE WHEN status = 'SENT' THEN 1 END) as successful,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
FROM notification_log
WHERE sent_at >= NOW() - INTERVAL '30 days'
GROUP BY notification_type;
```

### View Active Anomalies

```sql
-- All open anomalies by severity
SELECT 
    severity,
    anomaly_type,
    COUNT(*) as count
FROM lease_anomalies
WHERE status = 'OPEN'
GROUP BY severity, anomaly_type
ORDER BY severity, count DESC;
```

### Check Scheduled Job Logs

```bash
# View daily scan log
tail -f /var/log/leaseai_daily.log

# View weekly report log
tail -f /var/log/leaseai_weekly.log
```

---

## 🧪 Testing

### Test Email Configuration

```python
python -c "
from health_report_emailer import HealthReportEmailer
from supabase import create_client
import os

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
smtp = {
    'host': os.getenv('SMTP_HOST'),
    'port': int(os.getenv('SMTP_PORT')),
    'username': os.getenv('SMTP_USERNAME'),
    'password': os.getenv('SMTP_PASSWORD'),
    'from_email': os.getenv('SMTP_FROM_EMAIL'),
    'from_name': 'LeaseAI Test'
}

emailer = HealthReportEmailer(sb, smtp)
# Test by sending yourself an email using send_weekly_health_report()
"
```

### Test Anomaly Scanning

```python
from anomaly_detection_engine import scan_portfolio_for_anomalies
from supabase import create_client

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
results = scan_portfolio_for_anomalies(sb, client_id="your-client-uuid")

print(f"Anomalies detected: {results['anomalies_detected']}")
print(f"By severity: {results['by_severity']}")
```

---

## 🔒 Security Best Practices

1. **Never commit secrets** to version control - use `.env` files with `.gitignore`
2. **Use service role key** only on backend/scheduled jobs, never in frontend
3. **Enable RLS policies** on all Supabase tables
4. **Rotate SMTP credentials** quarterly
5. **Monitor failed emails** for potential security issues (bounces, blocks)
6. **Limit notification frequency** to prevent spam complaints

---

## 🐛 Troubleshooting

### Email Not Sending

```bash
# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-password')
print('✅ SMTP connection successful')
server.quit()
"
```

**Common Issues:**
- Gmail: Enable "Less secure app access" or use App Password
- Firewall: Ensure port 587 (or 465 for SSL) is open
- Rate limits: Gmail limits to 500 emails/day for free accounts

### Scheduled Job Not Running

```bash
# Check cron service status (Linux)
sudo service cron status

# View cron logs
grep CRON /var/log/syslog

# Test cron job manually
cd /path/to/leaseai && python scheduled_health_monitoring.py --task daily_scan
```

### PDF Generation Fails

**Error: "No module named 'reportlab'"**
```bash
pip install reportlab
```

**Error: Font issues on Linux**
```bash
sudo apt-get install -y fonts-dejavu-core
```

---

## 📈 Performance Optimization

### For Large Portfolios (10,000+ leases)

1. **Batch Processing**: Scan clients in batches
   ```python
   for i in range(0, len(client_ids), 100):
       batch = client_ids[i:i+100]
       # Process batch
   ```

2. **Database Indexes**: Ensure indexes on frequently queried fields
   ```sql
   CREATE INDEX idx_leases_uploaded_by ON leases(uploaded_by);
   CREATE INDEX idx_anomalies_lease_severity ON lease_anomalies(lease_id, severity);
   ```

3. **Parallel Execution**: Use multiprocessing for independent scans
   ```python
   from multiprocessing import Pool
   with Pool(4) as p:
       p.map(scan_client_portfolio, client_ids)
   ```

---

## 📚 Additional Resources

- **ReportLab Documentation**: https://www.reportlab.com/docs/reportlab-userguide.pdf
- **Python Email (smtplib)**: https://docs.python.org/3/library/smtplib.html
- **Supabase RLS Guide**: https://supabase.com/docs/guides/auth/row-level-security
- **Cron Syntax**: https://crontab.guru/

---

## 🎉 Next Steps

After setting up automated monitoring:

1. **Test end-to-end** with a small client portfolio
2. **Configure client email preferences** in database
3. **Monitor logs** for first week to catch any issues
4. **Set up alerts** for scheduler failures (e.g., via monitoring tools like Sentry, Datadog)
5. **Scale gradually** - start with daily scans, add weekly reports after validation

---

**Version:** Phase 6 Session 2  
**Last Updated:** October 2026  
**Maintainer:** LeaseAI Engineering Team
