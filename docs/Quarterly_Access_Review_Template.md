# LeaseAI - Quarterly Access Review Template
**Review Quarter:** Q___ 20___  
**Review Date:** _______________  
**Conducted By:** _______________  
**Next Review:** _______________

---

## 1. OVERVIEW

### 1.1 Purpose
Quarterly access reviews ensure that users have appropriate access levels based on their current roles and responsibilities, following the principle of least privilege.

### 1.2 Scope
- All user accounts (active and inactive)
- All system access (Supabase, GitHub, OpenAI, etc.)
- All role assignments
- All service accounts and API keys

### 1.3 Review Frequency
- **Quarterly:** Full access review
- **Monthly:** High-privilege accounts (admin, developer)
- **Ad-hoc:** After role changes, terminations, or security incidents

---

## 2. PRE-REVIEW CHECKLIST

- [ ] Export current user list from Supabase
- [ ] Export GitHub repository collaborators
- [ ] List all API keys and service accounts
- [ ] Gather HR data (current employees, contractors, roles)
- [ ] Identify recent role changes or terminations
- [ ] Review audit logs for suspicious access patterns

---

## 3. USER ACCESS REVIEW

### 3.1 SQL Query: Export All Users

```sql
-- Export all users with access details
SELECT 
    id,
    email,
    role,
    created_at,
    last_sign_in_at,
    confirmed_at,
    (SELECT COUNT(*) 
     FROM auth.mfa_factors 
     WHERE user_id = users.id AND status = 'verified') as mfa_enabled
FROM auth.users
ORDER BY role DESC, last_sign_in_at DESC NULLS LAST;
```

### 3.2 User Access Audit Spreadsheet

| User Email | Current Role | Department | Manager | Last Login | MFA? | Access Justified? | Action Required | Notes |
|------------|--------------|------------|---------|------------|------|-------------------|-----------------|-------|
| founder@leaseai.com | Admin | Executive | N/A | 2026-10-20 | ✅ | ✅ Yes | None | CEO - appropriate access |
| dev1@leaseai.com | Developer | Engineering | CTO | 2026-10-19 | ✅ | ✅ Yes | None | Active developer |
| support@leaseai.com | Support | Customer Success | VP CS | 2026-10-15 | ❌ | ✅ Yes | **Enable MFA** | Read-only access |
| old_employee@leaseai.com | Admin | N/A | N/A | 2026-06-01 | ✅ | ❌ No | **REVOKE ACCESS** | Terminated 3 months ago |
| contractor@example.com | Developer | N/A | CTO | 2026-09-01 | ✅ | ⚠️  Review | **Downgrade to read-only** | Contract ended, but still has dev access |

### 3.3 Review Questions for Each User

For each user, answer:

1. **Is this person currently employed/contracted?**
   - If NO → Revoke access immediately

2. **Does their current role match their system role?**
   - If NO → Adjust access to match current role

3. **When did they last log in?**
   - If >90 days → Consider deactivating account

4. **Do they need admin access?**
   - Admin access should be minimal (principle of least privilege)

5. **Do they have MFA enabled?**
   - If NO and admin → Require MFA immediately
   - If NO and user → Recommend MFA

6. **Have they changed roles recently?**
   - If YES → Verify access matches new role

---

## 4. ROLE-BASED ACCESS REVIEW

### 4.1 Admin Users

**Current Admins:**

| User | Justification | MFA? | Last Review | Keep Admin? |
|------|---------------|------|-------------|-------------|
| founder@leaseai.com | CEO, owns company | ✅ | Q4 2026 | ✅ Yes |
| cto@leaseai.com | CTO, manages systems | ✅ | Q4 2026 | ✅ Yes |
|  |  |  |  |  |

**Admin access review:**
- [ ] All admins require business justification
- [ ] All admins have MFA enabled
- [ ] Admin count minimized (target: <5 users)

### 4.2 Developer Users

**Current Developers:**

| User | Active Projects | Last Commit | GitHub Access? | Keep Developer? |
|------|-----------------|-------------|----------------|-----------------|
| dev1@leaseai.com | Phase 5 | 2026-10-20 | ✅ Yes | ✅ Yes |
|  |  |  |  |  |

**Developer access review:**
- [ ] All developers actively contributing
- [ ] GitHub access matches Supabase access
- [ ] Read-only access for inactive developers

### 4.3 Support Users

**Current Support Staff:**

| User | Customer-Facing? | Data Access Level | Justified? |
|------|------------------|-------------------|------------|
| support@leaseai.com | Yes | Read-only | ✅ Yes |
|  |  |  |  |

**Support access review:**
- [ ] Support staff have minimum required access
- [ ] No write access unless absolutely necessary
- [ ] Audit logs reviewed for data export activity

### 4.4 Read-Only / Viewer Users

**Current Viewers:**

| User | Purpose | Still Needed? |
|------|---------|---------------|
| auditor@leaseai.com | SOC 2 audit | ⏸️ Temporary (remove after audit) |
|  |  |  |

---

## 5. SYSTEM ACCESS REVIEW

### 5.1 GitHub Repository Access

**Current Collaborators:**

| User | GitHub Username | Role | Last Activity | Keep Access? |
|------|-----------------|------|---------------|--------------|
| founder@leaseai.com | brodyleaseai | Owner | 2026-10-20 | ✅ Yes |
|  |  |  |  |  |

**Review GitHub:**
1. Go to: https://github.com/brodyleaseai/leaseai/settings/access
2. Review all collaborators
3. Remove inactive users
4. Verify branch protection rules
5. Check deploy keys and webhooks

### 5.2 API Keys & Service Accounts

**Current API Keys:**

| Key Name | Purpose | Created | Last Used | Rotate? | Owner |
|----------|---------|---------|-----------|---------|-------|
| Supabase Service Key | Backend operations | 2026-01 | 2026-10-20 | 🔄 Q1 2027 | CTO |
| OpenAI API Key | Lease extraction | 2026-03 | 2026-10-20 | ✅ OK | CTO |
| Stripe API Key | Billing (future) | TBD | N/A | N/A | CFO |

**API Key Review:**
- [ ] All keys documented with purpose
- [ ] Keys rotated quarterly (or annually minimum)
- [ ] Unused keys revoked
- [ ] Keys stored securely (not in code)

### 5.3 Third-Party Service Access

**Services with LeaseAI Access:**

| Service | Access Level | Purpose | Owner | Review Status |
|---------|--------------|---------|-------|---------------|
| Supabase | Full admin | Database hosting | CTO | ✅ Reviewed |
| OpenAI | API access | AI extraction | CTO | ✅ Reviewed |
| GitHub | Repository owner | Code hosting | CTO | ✅ Reviewed |
| Streamlit Cloud | Deployment | App hosting | CTO | ✅ Reviewed |

---

## 6. INACTIVE ACCOUNTS

### 6.1 Identify Inactive Accounts

**SQL Query:**

```sql
-- Users who haven't logged in for 90+ days
SELECT 
    email,
    role,
    last_sign_in_at,
    EXTRACT(DAY FROM (NOW() - last_sign_in_at)) as days_since_login
FROM auth.users
WHERE last_sign_in_at < NOW() - INTERVAL '90 days'
   OR last_sign_in_at IS NULL
ORDER BY last_sign_in_at ASC NULLS FIRST;
```

### 6.2 Inactive Account Actions

| User | Last Login | Days Inactive | Action | Reason |
|------|------------|---------------|--------|--------|
|  |  |  |  |  |

**Actions:**
- **<90 days:** No action
- **90-180 days:** Flag for review, contact user
- **>180 days:** Disable account
- **Terminated employee:** Delete immediately

---

## 7. FINDINGS & ACTIONS

### 7.1 Access Violations Found

| Issue | Severity | User | Action Taken | Completed? |
|-------|----------|------|--------------|------------|
| Admin without MFA | High | support@leaseai.com | Enable MFA required | [ ] |
| Terminated employee still has access | Critical | old_employee@leaseai.com | Access revoked | [ ] |
| Contractor with excessive permissions | Medium | contractor@example.com | Downgraded to read-only | [ ] |

### 7.2 Summary Statistics

**Before Review:**
- Total users: ___
- Admin users: ___
- Users with MFA: ___
- Inactive accounts (>90 days): ___

**After Review:**
- Total users: ___
- Admin users: ___
- Users with MFA: ___
- Inactive accounts (>90 days): ___

**Actions Taken:**
- Accounts disabled: ___
- Accounts deleted: ___
- Access downgraded: ___
- MFA required: ___
- API keys rotated: ___

---

## 8. REMEDIATION TRACKING

### 8.1 Action Items

| Action | Owner | Due Date | Status | Completion Date |
|--------|-------|----------|--------|-----------------|
| Revoke access for old_employee@leaseai.com | CTO | Immediately | ✅ Complete | 2026-10-21 |
| Require MFA for support@leaseai.com | IT Admin | Within 7 days | 🟡 In Progress | |
| Rotate Supabase service key | CTO | Q1 2027 | ⏸️ Scheduled | |

### 8.2 Follow-Up Required

**High Priority (complete within 24 hours):**
- 

**Medium Priority (complete within 7 days):**
- 

**Low Priority (complete within 30 days):**
- 

---

## 9. RECOMMENDATIONS

### 9.1 Process Improvements

**Identified gaps:**
1. 
2. 
3. 

**Recommendations:**
1. 
2. 
3. 

### 9.2 Policy Updates Needed

- [ ] Update Information Security Policy
- [ ] Update onboarding/offboarding procedures
- [ ] Update access request process
- [ ] Create automated alerts for inactive accounts

---

## 10. APPROVAL & SIGN-OFF

**Access Review Completed By:**

Name: _____________________________  
Title: _____________________________  
Signature: _________________________  
Date: ______________________________

**Reviewed and Approved By:**

Name: _____________________________  
Title: _____________________________  
Signature: _________________________  
Date: ______________________________

**Next Review:** _______________ (3 months from completion date)

---

## 11. DISTRIBUTION

**Report sent to:**
- [ ] CTO
- [ ] Founder/CEO
- [ ] HR (if applicable)
- [ ] SOC 2 auditor (when applicable)

**Stored in:** `docs/access_reviews/Q[X]_20[XX]_access_review.md`

---

## 12. APPENDIX: OFFBOARDING CHECKLIST

**When an employee/contractor leaves:**

Within 1 hour of termination:
- [ ] Disable Supabase account
- [ ] Remove GitHub collaborator access
- [ ] Revoke API keys user had access to
- [ ] Disable email forwarding
- [ ] Change shared passwords

Within 24 hours:
- [ ] Verify all access revoked (run audit query)
- [ ] Collect company equipment
- [ ] Exit interview (if applicable)
- [ ] Document in offboarding log

---

**Document Classification:** CONFIDENTIAL - Internal Use Only
