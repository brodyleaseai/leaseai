# Supabase Automated Backup Configuration Guide

**Phase 5B: Enterprise Readiness**  
**Last Updated:** October 21, 2026  
**Owner:** DevOps / Platform Team

---

## 📋 Overview

This guide provides step-by-step instructions for configuring automated backups for your LeaseAI Supabase database, including Point-in-Time Recovery (PITR), scheduled backups, monitoring, and restoration procedures.

---

## 🎯 Backup Requirements (SOC 2 Compliance)

| Requirement | Target | Status |
|-------------|--------|--------|
| Backup Frequency | Daily | ✅ |
| Backup Retention | 30 days minimum | ✅ |
| PITR Window | 7 days | ✅ |
| Recovery Time Objective (RTO) | < 4 hours | ✅ |
| Recovery Point Objective (RPO) | < 24 hours | ✅ |
| Backup Testing | Monthly | 🔄 Configure |
| Offsite Storage | Multi-region | ✅ |
| Encryption | AES-256 at rest | ✅ |

---

## 🔧 Part 1: Enable Point-in-Time Recovery (PITR)

### What is PITR?

Point-in-Time Recovery allows you to restore your database to any point within the last 7 days, down to the second. This protects against:
- Accidental data deletion
- Corrupted data
- Bad migrations
- Application bugs

### Enable PITR (Supabase Dashboard)

1. **Log into Supabase Dashboard**: https://app.supabase.com

2. **Navigate to your LeaseAI project**

3. **Go to Database → Backups**

4. **Enable Point-in-Time Recovery**:
   - Click **"Enable PITR"**
   - Confirm the action
   - Wait 2-5 minutes for activation

5. **Verify PITR is Active**:
   - Status should show: **"PITR Enabled"**
   - Recovery window: **7 days**

**Cost:** PITR is included in Pro plan ($25/month) and above. Free tier does not include PITR.

---

## 📅 Part 2: Configure Daily Automated Backups

Supabase automatically performs daily backups on Pro plan and above. Here's how to configure them:

### Step 1: Verify Daily Backups are Enabled

1. **Go to Database → Backups**

2. **Check "Scheduled Backups" section**:
   - Should show: **"Daily backups enabled"**
   - Backup time: **02:00 UTC** (default)
   - Retention: **7 days** (Free/Pro), **30 days** (Team/Enterprise)

### Step 2: Adjust Backup Retention (Optional)

**For Team/Enterprise Plans:**
1. Go to **Settings → Billing**
2. Under **Add-ons**, select **Extended Backup Retention**
3. Options:
   - 30 days (included in Team plan)
   - 90 days (+$100/month)
   - 180 days (+$200/month)

**Recommendation for SOC 2:** Minimum 30 days retention.

### Step 3: Configure Backup Window (Enterprise Only)

Enterprise customers can customize backup timing:
1. Contact Supabase support: support@supabase.io
2. Request custom backup window (e.g., 02:00 AM PST)
3. Supabase will configure backend scheduling

---

## 🔔 Part 3: Set Up Backup Monitoring & Alerts

### Monitor Backup Status via Dashboard

1. **Go to Database → Backups**

2. **Check "Backup History" table**:
   - Date/time of each backup
   - Backup size
   - Status: Success/Failed
   - Duration

3. **Investigate failures immediately**:
   - Click on failed backup for details
   - Contact Supabase support if recurring

### Configure Email Alerts (Recommended)

**Option A: Supabase Built-in Alerts (Enterprise)**
- Enterprise plans include backup failure alerts
- Contact support to enable: support@supabase.io

**Option B: Custom Monitoring Script**

Create a daily cron job to check backup status:

```python
# check_backups.py
import os
import requests
from datetime import datetime, timedelta

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ALERT_EMAIL = "devops@leaseai.com"

def check_backup_status():
    """Check if backup ran successfully in last 24 hours"""
    
    # Query backup_verifications table
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/backup_verifications"
    params = {
        "order": "verified_at.desc",
        "limit": 1
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        if data:
            last_backup = data[0]
            backup_time = datetime.fromisoformat(last_backup['verified_at'])
            
            # Check if backup is within 24 hours
            if datetime.utcnow() - backup_time < timedelta(hours=24):
                print(f"✅ Backup healthy: {backup_time}")
                return True
            else:
                send_alert(f"⚠️ Last backup is {datetime.utcnow() - backup_time} old")
                return False
        else:
            send_alert("❌ No backup records found")
            return False
    else:
        send_alert(f"❌ Failed to check backup status: {response.status_code}")
        return False

def send_alert(message):
    """Send alert via email/Slack/PagerDuty"""
    print(message)
    # Integrate with your alerting system
    # Example: SendGrid, Slack webhook, PagerDuty

if __name__ == "__main__":
    check_backup_status()
```

**Schedule via cron:**
```bash
# Run daily at 9am UTC (after 2am backup completes)
0 9 * * * python /path/to/check_backups.py
```

---

## 🔄 Part 4: Test Backup Restoration (Monthly)

**Critical:** You must test backup restoration monthly to verify recoverability.

### Test Restoration Procedure

#### Method 1: PITR Restoration (Recommended for Testing)

1. **Go to Database → Backups**

2. **Click "Point-in-Time Recovery"**

3. **Select a restore point**:
   - Date: Yesterday
   - Time: 14:00 UTC
   - Click **"Preview Restore"**

4. **Create a new project from backup**:
   - Project name: `leaseai-restore-test-2026-10-21`
   - Region: Same as production
   - Click **"Restore to New Project"**

5. **Wait 5-15 minutes** for restoration

6. **Verify data integrity**:
   - Check row counts: `SELECT COUNT(*) FROM leases;`
   - Check latest entries exist
   - Run test queries

7. **Calculate RTO/RPO**:
   - RTO: Time from restore start to database accessible
   - RPO: Difference between restore point and latest data

8. **Document results** in `backup_verifications` table:
   ```sql
   INSERT INTO backup_verifications (
       backup_date,
       restore_tested_at,
       test_status,
       rto_minutes,
       rpo_minutes,
       verified_by
   ) VALUES (
       '2026-10-21',
       NOW(),
       'SUCCESS',
       12,  -- RTO in minutes
       0,   -- RPO in minutes
       'devops@leaseai.com'
   );
   ```

9. **Delete test project** after verification

#### Method 2: Full Backup Download (Alternative)

1. **Go to Database → Backups**

2. **Click "Download" on latest backup**

3. **Extract backup file** (`.tar.gz`)

4. **Restore locally with `pg_restore`**:
   ```bash
   # Extract backup
   tar -xzf backup-2026-10-21.tar.gz
   
   # Restore to local PostgreSQL
   pg_restore -d leaseai_test -v backup.dump
   
   # Verify
   psql leaseai_test -c "SELECT COUNT(*) FROM leases;"
   ```

5. **Document test results**

---

## 📊 Part 5: Backup Verification Automation

Use the included test script to automate monthly backup testing:

```bash
# Run backup restore test
python test_backup_restore.py
```

**Expected Output:**
```
========================================
LeaseAI Backup & Restore Test
========================================

✅ Connected to Supabase successfully
✅ Latest backup found: 2026-10-21 02:15:33 UTC
✅ Backup age: 7 hours (within 24-hour threshold)

Testing Backup Restoration...
✅ Restored database accessible
✅ Row count verification:
   - Leases: 127 (expected: 127)
   - Clients: 8 (expected: 8)
   - Extracted Fields: 10,668 (expected: 10,668)

✅ Data integrity confirmed
✅ RTO: 8 minutes (target: <240 minutes)
✅ RPO: 0 minutes (target: <1440 minutes)

========================================
Status: SUCCESS
All backup tests passed!
========================================
```

**Schedule Monthly:**
```bash
# Run first Saturday of each month at 10am
0 10 1-7 * 6 python /path/to/test_backup_restore.py
```

---

## 🚨 Part 6: Disaster Recovery Procedure

### When to Trigger DR

- Database corruption detected
- Accidental mass deletion
- Failed migration
- Security breach requiring rollback

### DR Steps

**1. Assess the Situation**
- What happened?
- When did it happen?
- What data is affected?
- What is the restore point target?

**2. Notify Stakeholders**
- Email: devops@leaseai.com, founder@leaseai.com
- Slack: #incidents channel
- Status page: Update with "Database Maintenance"

**3. Execute Point-in-Time Recovery**

```sql
-- Example: Restore to 10 minutes before incident
-- This is done via Supabase Dashboard, not SQL

1. Database → Backups → PITR
2. Select restore point: [Date] [Time]
3. Choose:
   - Restore over current database (DESTRUCTIVE)
   - OR Create new project (SAFER)
4. Confirm and execute
5. Wait for completion (10-30 minutes)
```

**4. Verify Restoration**
- Check row counts
- Verify critical data exists
- Run application smoke tests
- Check audit logs for consistency

**5. Resume Operations**
- Update DNS (if restored to new project)
- Notify users
- Update status page
- Document incident

**6. Post-Incident Review**
- Root cause analysis
- Update runbooks
- Improve monitoring
- Test recovery time

---

## 📈 Part 7: Backup Metrics & Reporting

### Key Metrics to Track

| Metric | Target | Measurement |
|--------|--------|-------------|
| Backup Success Rate | 100% | Daily |
| Average Backup Duration | <5 min | Daily |
| Backup Size Growth | <10%/month | Monthly |
| RTO (Recovery Time) | <4 hours | Monthly test |
| RPO (Recovery Point) | <24 hours | Monthly test |
| Restore Success Rate | 100% | Monthly test |

### Monthly Backup Report Template

```markdown
# LeaseAI Backup Report - [Month Year]

## Summary
- Total Backups: [X]
- Successful Backups: [X] (100%)
- Failed Backups: 0
- Average Backup Size: [X] GB
- Restore Tests Conducted: 1
- Restore Test Success: ✅

## Backup Growth
- Start of month: [X] GB
- End of month: [X] GB
- Growth: [X]% ([X] GB)

## Restore Test Results
- Test Date: [Date]
- Restore Point: [Date/Time]
- RTO: [X] minutes (Target: <240)
- RPO: [X] minutes (Target: <1440)
- Data Integrity: ✅ Verified

## Issues & Resolutions
- None

## Action Items
- None

**Next Review:** [Date]
```

---

## 🔐 Part 8: Security & Compliance

### Backup Encryption

- **At Rest:** AES-256 encryption (Supabase default)
- **In Transit:** TLS 1.3 encryption
- **Key Management:** Managed by Supabase (SOC 2 Type II certified)

### Access Controls

**Who can access backups?**
- Organization Owner (you)
- Organization Admins
- Supabase Support (emergency only, with permission)

**Recommendation:** Use Supabase's RBAC to limit backup access to 2-3 trusted admins.

### Audit Logging

All backup operations are logged:
- Backup creation
- Backup downloads
- PITR restorations
- Backup deletions

**View logs:** Database → Backups → Activity Log

---

## 📚 Part 9: Additional Resources

### Supabase Backup Documentation
- Official Docs: https://supabase.com/docs/guides/platform/backups
- PITR Guide: https://supabase.com/docs/guides/platform/pitr
- Migration Guide: https://supabase.com/docs/guides/platform/migrating-and-upgrading

### Support Channels
- Supabase Support: support@supabase.io
- Supabase Discord: https://discord.supabase.com
- LeaseAI DevOps: devops@leaseai.com

### SOC 2 Requirements
- Backup retention: 30 days minimum
- Monthly restore testing: Required
- Documented DR procedure: Required
- Backup encryption: Required

---

## ✅ Implementation Checklist

Use this checklist to verify your backup configuration:

**Initial Setup:**
- [ ] Enable PITR in Supabase Dashboard
- [ ] Verify daily backups are running
- [ ] Configure backup retention (30+ days)
- [ ] Set up backup monitoring script
- [ ] Schedule daily backup health checks
- [ ] Document backup procedures in runbook

**Monthly Tasks:**
- [ ] Run backup restore test (first Saturday)
- [ ] Review backup size growth
- [ ] Check for backup failures
- [ ] Update backup metrics dashboard
- [ ] Generate monthly backup report

**Quarterly Tasks:**
- [ ] Review DR procedure with team
- [ ] Conduct DR drill (full restoration)
- [ ] Update backup documentation
- [ ] Review backup retention policy

**Annual Tasks:**
- [ ] Full disaster recovery simulation
- [ ] Review backup costs vs. retention
- [ ] Audit backup access controls
- [ ] Update SOC 2 backup documentation

---

## 🚀 Quick Start Commands

```bash
# Install test dependencies
pip install python-dateutil requests

# Run backup verification test
python test_backup_restore.py

# Check last backup status
python -c "
from supabase import create_client
import config
sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
backups = sb.table('backup_verifications').select('*').order('verified_at', desc=True).limit(1).execute()
print(f'Last backup: {backups.data[0] if backups.data else \"None\"}')
"

# Schedule monthly backup test (crontab)
0 10 1-7 * 6 cd /path/to/leaseai && python test_backup_restore.py >> /var/log/backup_tests.log 2>&1
```

---

## 📞 Emergency Contacts

| Role | Contact | Availability |
|------|---------|-------------|
| Primary DBA | devops@leaseai.com | 24/7 |
| Founder/CTO | founder@leaseai.com | 24/7 |
| Supabase Support | support@supabase.io | 24/7 (Enterprise) |
| On-Call Engineer | [Phone] | 24/7 |

---

**Document Version:** 1.0  
**Last Updated:** October 21, 2026  
**Next Review:** November 21, 2026  
**Owner:** DevOps Team
