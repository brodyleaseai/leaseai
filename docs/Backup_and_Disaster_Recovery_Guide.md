# LeaseAI - Backup & Disaster Recovery Guide
**Version:** 1.0  
**Last Updated:** October 2026  
**Owner:** DevOps / Infrastructure Team

---

## 1. OVERVIEW

This document describes LeaseAI's backup strategy, disaster recovery procedures, and business continuity plans.

### 1.1 Objectives
- **RTO (Recovery Time Objective):** 4 hours - Maximum acceptable downtime
- **RPO (Recovery Point Objective):** 1 hour - Maximum acceptable data loss
- **Backup Retention:** 30 days point-in-time recovery

### 1.2 Scope
This guide covers:
- Database backups (Supabase PostgreSQL)
- File storage backups (lease documents, generated reports)
- Application code and configuration
- Disaster recovery procedures

---

## 2. BACKUP STRATEGY

### 2.1 Database Backups (Supabase)

#### Automated Backups
Supabase provides automatic backups for all projects:

| Backup Type | Frequency | Retention | Storage Location |
|-------------|-----------|-----------|------------------|
| **Full Backup** | Daily at 2:00 AM UTC | 30 days | AWS S3 (multi-region) |
| **Incremental Backup** | Every hour | 24 hours | Supabase infrastructure |
| **Point-in-Time Recovery (PITR)** | Continuous (WAL archiving) | 7 days | AWS S3 |

#### Enabling Point-in-Time Recovery

1. Log in to Supabase Dashboard
2. Navigate to: **Project Settings → Database → Backups**
3. Enable **Point-in-Time Recovery (PITR)**
4. Set retention period: **7 days** (or longer for Pro plan)

**Note:** PITR allows recovery to any point in the last 7 days with 1-second granularity.

### 2.2 File Storage Backups

Lease documents and generated reports are stored in **Supabase Storage** (backed by AWS S3).

#### Backup Configuration
- **Versioning:** Enabled (keeps previous versions of files)
- **Cross-Region Replication:** Enabled (replicates to secondary AWS region)
- **Lifecycle Policy:** Delete old file versions after 90 days

#### Verification
To verify file storage backups:
```bash
# List buckets
supabase storage ls

# Check versioning status
supabase storage info leases
```

### 2.3 Application Code Backups

Application code is version-controlled in **GitHub**.

- **Repository:** https://github.com/brodyleaseai/leaseai
- **Branches:** 
  - `main` - Production code
  - `develop` - Development code
  - Feature branches for active work
- **Backup Strategy:** 
  - GitHub maintains redundant copies across data centers
  - Git history provides version recovery
  - Tagged releases for production deployments

#### Best Practices
- Tag all production releases: `git tag -a v1.2.3 -m "Production release v1.2.3"`
- Push tags to GitHub: `git push origin --tags`
- Never force-push to `main` branch

---

## 3. BACKUP TESTING & VERIFICATION

### 3.1 Monthly Backup Restore Test

**Schedule:** First Monday of each month  
**Responsibility:** DevOps team

#### Test Procedure

1. **Select Random Backup**
   - Choose a backup from 1-7 days ago

2. **Create Test Environment**
   ```bash
   # Create a new Supabase project for testing
   # Or use dedicated staging project
   ```

3. **Restore Database Backup**
   - Via Supabase Dashboard:
     - Go to **Database → Backups**
     - Click **Restore** on selected backup
     - Choose destination (test project)
   
   - Or via CLI:
     ```bash
     supabase db restore --project-ref TEST_PROJECT --backup-id BACKUP_ID
     ```

4. **Verify Data Integrity**
   ```sql
   -- Check row counts match expected values
   SELECT 'leases' as table_name, COUNT(*) as row_count FROM leases
   UNION ALL
   SELECT 'extracted_fields', COUNT(*) FROM extracted_fields
   UNION ALL
   SELECT 'cam_reconciliations', COUNT(*) FROM cam_reconciliations;
   
   -- Verify recent data exists
   SELECT MAX(uploaded_at) as latest_lease FROM leases;
   SELECT MAX(created_at) as latest_reconciliation FROM cam_reconciliations;
   ```

5. **Test Application Functionality**
   - Point application to test database
   - Log in and verify user authentication works
   - Navigate to Lease Review page
   - Generate a CAM reconciliation report
   - Generate a portfolio health report

6. **Measure Restore Time**
   - Record time from backup selection to full application functionality
   - Target: < 4 hours (RTO)

7. **Document Results**
   - Log results in `backup_verifications` table:
     ```sql
     INSERT INTO backup_verifications (
       backup_date, verification_date, backup_type, status, 
       records_restored, restore_time_seconds, verified_by, notes
     ) VALUES (
       '2026-10-15', NOW(), 'FULL', 'SUCCESS',
       1523, 1800, 'auth_user_uuid', 'Test successful, 30 min restore time'
     );
     ```

8. **Clean Up**
   - Delete test environment
   - Document any issues found

---

## 4. DISASTER RECOVERY PROCEDURES

### 4.1 Disaster Scenarios

#### Scenario 1: Database Corruption or Data Loss

**Symptoms:**
- Application errors accessing database
- Missing or corrupted data
- Unexpected data deletion

**Recovery Steps:**

1. **Assess Damage**
   - Identify affected tables and time range
   - Determine if PITR is sufficient or full restore needed

2. **Stop Application (if necessary)**
   ```bash
   # Put application in maintenance mode
   # Update environment variable: MAINTENANCE_MODE=true
   ```

3. **Restore Database**
   
   **Option A: Point-in-Time Recovery (for recent issues, < 7 days)**
   ```bash
   # Via Supabase Dashboard:
   # Database → Backups → Point-in-Time Recovery
   # Select date/time before corruption occurred
   
   # Via CLI:
   supabase db restore --project-ref PROJECT_REF --pitr-timestamp "2026-10-20T14:30:00Z"
   ```
   
   **Option B: Full Backup Restore (for older issues)**
   ```bash
   supabase db restore --project-ref PROJECT_REF --backup-id BACKUP_ID
   ```

4. **Verify Data**
   - Run integrity checks (see Section 3.1 step 4)
   - Compare row counts before/after

5. **Resume Application**
   - Remove maintenance mode
   - Monitor error logs for 24 hours

6. **Post-Mortem**
   - Document root cause
   - Implement preventive measures
   - Update runbooks if needed

**Estimated Time:** 2-4 hours

---

#### Scenario 2: Complete Infrastructure Failure (AWS Region Outage)

**Symptoms:**
- Application completely unavailable
- Database inaccessible
- Supabase dashboard unreachable

**Recovery Steps:**

1. **Assess Outage Scope**
   - Check AWS status page: https://status.aws.amazon.com/
   - Check Supabase status: https://status.supabase.com/
   - Determine if single region or multi-region

2. **Activate DR Plan**
   - If outage > 1 hour, begin failover

3. **Deploy to Backup Region**
   
   **Option A: Supabase Automatic Failover (if configured)**
   - Supabase Pro/Enterprise plans include auto-failover
   - Verify new connection string
   - Update application environment variables

   **Option B: Manual Failover**
   ```bash
   # 1. Create new Supabase project in different region
   # 2. Restore latest backup to new project
   # 3. Update DNS to point to new region
   # 4. Update application environment variables:
   export SUPABASE_URL="https://NEW_PROJECT_REF.supabase.co"
   export SUPABASE_SERVICE_KEY="NEW_KEY"
   
   # 5. Redeploy application
   git push origin main  # Triggers CI/CD
   ```

4. **Verify Application**
   - Test login
   - Test key workflows (upload, extract, export)
   - Monitor error rates

5. **Communicate with Users**
   - Email: "Service restored after infrastructure outage"
   - Provide incident report within 72 hours

6. **After Primary Region Recovers**
   - Optionally fail back to primary region
   - Or continue on backup region permanently

**Estimated Time:** 4-6 hours (within RTO)

---

#### Scenario 3: Ransomware or Security Breach

**Symptoms:**
- Files encrypted
- Unauthorized data access
- Data exfiltration detected

**Recovery Steps:**

1. **Incident Response (Priority 1)**
   - Isolate affected systems immediately
   - Revoke all API keys and access tokens
   - Force password reset for all users
   - Engage security consultant/IR firm if needed

2. **Assess Damage**
   - Identify compromised data
   - Determine breach timeline
   - Check audit logs for unauthorized activity

3. **Restore from Clean Backup**
   - Restore from backup **before** breach occurred
   - Verify backup is not infected

4. **Rebuild Infrastructure**
   - Provision new Supabase project (if compromised)
   - Rotate all secrets (database passwords, API keys, etc.)
   - Update firewall rules

5. **Re-deploy Application**
   - Scan code for malware/backdoors
   - Deploy to new infrastructure

6. **Legal & Compliance**
   - Notify affected customers within 72 hours (GDPR)
   - File breach report with authorities (if required)
   - Engage legal counsel

**Estimated Time:** 24-48 hours (extended RTO acceptable for security)

---

## 5. BACKUP RETENTION & LIFECYCLE

| Data Type | Retention Period | Deletion Method |
|-----------|------------------|-----------------|
| Database backups | 30 days | Automatic (Supabase) |
| PITR logs | 7 days | Automatic (Supabase) |
| File storage versions | 90 days | Lifecycle policy |
| Audit logs (active) | 1 year | SQL DELETE after 1 year |
| Audit logs (archive) | 7 years | Move to cold storage (Glacier) |
| Customer data (after termination) | 30 days | Secure deletion (overwrite + verify) |

---

## 6. BACKUP SECURITY

### 6.1 Encryption
- **In Transit:** TLS 1.3 for all backup transfers
- **At Rest:** AES-256 encryption for all backups
- **Key Management:** AWS KMS (automatic key rotation)

### 6.2 Access Control
- Backup restoration requires admin role + MFA
- Supabase service role key stored in secure secrets manager
- Audit all backup access in `audit_log` table

### 6.3 Compliance
- Backups stored in SOC 2 Type II certified data centers
- GDPR-compliant (data can be deleted upon request)
- Backups excluded from public access (private S3 buckets)

---

## 7. MONITORING & ALERTS

### 7.1 Backup Success Monitoring

Set up alerts for:
- Backup failure (daily backup did not complete)
- Backup size anomaly (backup < 50% of previous day = data loss risk)
- Restore test failure (monthly test did not pass)

### 7.2 Alerting Channels
- **Email:** devops@leaseai.com
- **Slack:** #ops-alerts channel
- **PagerDuty:** For critical failures (24/7)

### 7.3 Monitoring Dashboard

Create a Supabase function to check backup status:

```sql
-- Query backup status (example using Supabase backup metadata)
SELECT 
  inserted_at as backup_time,
  status,
  size_mb,
  duration_seconds
FROM backups
ORDER BY inserted_at DESC
LIMIT 7;
```

---

## 8. BUSINESS CONTINUITY PLAN

### 8.1 Critical Business Functions

| Function | Max Tolerable Downtime | Priority |
|----------|------------------------|----------|
| User authentication | 1 hour | P0 |
| Lease upload & extraction | 4 hours | P1 |
| Lease review & export | 8 hours | P2 |
| CAM reconciliation | 24 hours | P3 |
| Portfolio health reports | 48 hours | P4 |

### 8.2 Recovery Prioritization

In a disaster scenario, recover in this order:
1. Database (all business functions depend on this)
2. Authentication & user access
3. Lease upload & extraction (revenue-critical)
4. Reporting & analytics (can tolerate longer downtime)

---

## 9. CONTACTS & ESCALATION

| Role | Name | Email | Phone | Escalation Level |
|------|------|-------|-------|------------------|
| Primary On-Call | [DevOps Lead] | devops@leaseai.com | [Phone] | L1 |
| Backup On-Call | [Engineer 2] | engineer2@leaseai.com | [Phone] | L2 |
| Founder/CEO | [Founder] | founder@leaseai.com | [Phone] | L3 (Critical) |
| Supabase Support | - | support@supabase.com | - | Vendor |
| AWS Support | - | [AWS Account ID] | - | Vendor |

---

## 10. ANNUAL REVIEW

This backup and DR plan must be reviewed and updated:
- **Annually** (October)
- After any disaster recovery event
- When infrastructure significantly changes
- After SOC 2 audit findings

**Next Review Date:** October 2027

---

**Plan Owner:** DevOps Lead  
**Approved By:** Founder/CEO  
**Approval Date:** October 2026

---

For questions or to report a disaster:  
Email: devops@leaseai.com  
Emergency Hotline: [Emergency Phone]
