# LeaseAI - MFA Enforcement Checklist
**Target Completion:** December 1, 2026  
**Owner:** CTO / IT Admin  
**Status:** 🟡 In Progress

---

## 1. OVERVIEW

### 1.1 Objective
Enforce Multi-Factor Authentication (MFA) for all admin users by December 1, 2026 to comply with SOC 2 requirements and protect against credential compromise.

### 1.2 Scope
- **Phase 1 (Nov 2026):** All admin users
- **Phase 2 (Jan 2027):** All users (recommended)

### 1.3 Success Criteria
- 100% of admin users have MFA enabled
- Zero admin accounts without MFA by Dec 1, 2026
- Documentation updated

---

## 2. PRE-ENFORCEMENT CHECKLIST

### 2.1 Preparation (Complete by Nov 15, 2026)

- [ ] **Verify MFA is available** in Supabase Auth
  - Login to Supabase Dashboard
  - Navigate to Authentication → Providers
  - Confirm TOTP (Authenticator App) is enabled

- [ ] **Create user documentation**
  - ✅ 2FA Setup Guide already created (`docs/2FA_Setup_Guide.md`)
  - [ ] Test setup guide with a test user
  - [ ] Create quick-start video (optional)

- [ ] **Identify all admin users**
  - Run audit query (see Section 3)
  - Create list of admin users who need MFA
  - Document exemptions (if any - should be ZERO)

- [ ] **Communicate to admins**
  - [ ] Email #1: Nov 1 - "MFA Required by Dec 1"
  - [ ] Email #2: Nov 15 - "Reminder: MFA Required in 2 weeks"
  - [ ] Email #3: Nov 27 - "Final Reminder: MFA Required in 3 days"

- [ ] **Set up support process**
  - [ ] Designate MFA support contact (CTO or IT admin)
  - [ ] Create FAQ document
  - [ ] Prepare for common issues (lost phone, etc.)

---

## 3. IDENTIFY ADMIN USERS

### 3.1 SQL Query to List All Admin Users

Run this query in Supabase SQL Editor:

```sql
-- List all users with admin role
SELECT 
    id,
    email,
    role,
    created_at,
    last_sign_in_at,
    phone, -- If using SMS MFA
    -- Check if MFA is enabled (method depends on Supabase Auth version)
    (SELECT COUNT(*) 
     FROM auth.mfa_factors 
     WHERE user_id = users.id AND status = 'verified') as mfa_factors_count
FROM auth.users
WHERE role = 'admin' -- Adjust based on your role field
   OR email IN ('founder@leaseai.com', 'admin@leaseai.com') -- Add known admins
ORDER BY last_sign_in_at DESC NULLS LAST;
```

### 3.2 Export Results

Export the query results and create a tracking spreadsheet:

| User Email | User ID | MFA Enabled? | Date Enabled | Notes |
|------------|---------|--------------|--------------|-------|
| founder@leaseai.com | uuid-123 | ❌ No | | Pending |
| admin@leaseai.com | uuid-456 | ✅ Yes | 2026-10-15 | Complete |

---

## 4. COMMUNICATION PLAN

### 4.1 Email Template #1 (Nov 1, 2026)

**Subject:** [ACTION REQUIRED] Enable 2FA on Your LeaseAI Account by Dec 1

**Body:**
```
Hi [Name],

As part of our ongoing security improvements and SOC 2 compliance efforts, 
we are requiring all admin users to enable Two-Factor Authentication (2FA) 
by December 1, 2026.

**What is 2FA?**
Two-Factor Authentication adds an extra layer of security by requiring both 
your password and a code from your phone when you log in.

**What do you need to do?**
1. Follow the step-by-step guide: [Link to 2FA_Setup_Guide.md]
2. Enable 2FA using an authenticator app (Google Authenticator, Authy, etc.)
3. Save your backup codes in a safe place

**Deadline:** December 1, 2026

**Need help?**
Contact [CTO/IT Admin] at [email] or [phone]

**What happens if I don't enable 2FA by Dec 1?**
Your admin access will be suspended until 2FA is enabled.

Thank you for helping us keep LeaseAI secure!

[CTO Name]
Chief Technology Officer
```

### 4.2 Email Template #2 (Nov 15, 2026)

**Subject:** [REMINDER] Enable 2FA - 2 Weeks Remaining

**Body:**
```
Hi [Name],

This is a friendly reminder that you need to enable Two-Factor Authentication 
on your LeaseAI admin account by December 1, 2026 (2 weeks from today).

**Status:** Our records show you have NOT yet enabled 2FA.

**How to enable 2FA:**
[Link to 2FA_Setup_Guide.md]

**Need help?**
Contact [CTO/IT Admin] - we're happy to help you set it up!

Thank you,
[CTO Name]
```

### 4.3 Email Template #3 (Nov 27, 2026)

**Subject:** [FINAL REMINDER] Enable 2FA by Dec 1 - 3 Days Remaining

**Body:**
```
Hi [Name],

FINAL REMINDER: You have 3 days remaining to enable Two-Factor Authentication 
on your LeaseAI admin account.

**Deadline:** December 1, 2026

**Current Status:** NOT ENABLED

After December 1, your admin access will be suspended until you enable 2FA.

**Enable 2FA now:** [Link to 2FA_Setup_Guide.md]

**Need urgent help?**
Contact [CTO/IT Admin] immediately.

[CTO Name]
```

---

## 5. ENFORCEMENT PROCEDURE

### 5.1 December 1, 2026 - Enforcement Day

**Morning (9:00 AM):**
1. [ ] Run admin user audit query again
2. [ ] Identify users who still don't have MFA enabled
3. [ ] Send final warning email (see template below)

**Afternoon (5:00 PM):**
1. [ ] Disable admin access for non-compliant users
2. [ ] Send access suspended notification
3. [ ] Offer to help them enable MFA immediately

### 5.2 Access Suspension Procedure

**Option A: Manual Suspension (Supabase Dashboard)**
1. Go to Supabase Dashboard → Authentication → Users
2. Find non-compliant user
3. Change role from `admin` to `user` (or custom role with limited permissions)
4. Add note: "Admin access suspended - MFA not enabled"

**Option B: Automated Suspension (SQL)**
```sql
-- Temporarily demote admins without MFA to regular users
UPDATE auth.users
SET role = 'user_suspended_no_mfa'
WHERE role = 'admin'
  AND id NOT IN (
    SELECT user_id 
    FROM auth.mfa_factors 
    WHERE status = 'verified'
  );
```

### 5.3 Suspension Notification Email

**Subject:** Your LeaseAI Admin Access Has Been Suspended

**Body:**
```
Hi [Name],

Your LeaseAI admin access has been suspended because Two-Factor Authentication 
(2FA) has not been enabled on your account.

**To restore your admin access:**
1. Enable 2FA following this guide: [Link]
2. Contact [CTO/IT Admin] to verify and restore your access

This is a required security measure for SOC 2 compliance.

**Need help?**
We're here to assist! Contact [email] or [phone] and we'll help you 
enable 2FA immediately.

[CTO Name]
```

---

## 6. RE-ENABLING ADMIN ACCESS

### 6.1 Verification Process

When a suspended user enables MFA:

1. [ ] User contacts IT admin: "I've enabled 2FA"
2. [ ] Admin verifies MFA is enabled:
   ```sql
   SELECT email, 
          (SELECT COUNT(*) 
           FROM auth.mfa_factors 
           WHERE user_id = users.id AND status = 'verified') as mfa_count
   FROM auth.users
   WHERE email = '[user email]';
   ```
3. [ ] If verified, restore admin role:
   ```sql
   UPDATE auth.users
   SET role = 'admin'
   WHERE email = '[user email]';
   ```
4. [ ] Send confirmation email

### 6.2 Confirmation Email

**Subject:** Your LeaseAI Admin Access Has Been Restored

**Body:**
```
Hi [Name],

Great news! Your LeaseAI admin access has been restored.

**What changed:**
- ✅ Two-Factor Authentication is now enabled on your account
- ✅ Your admin role has been restored
- ✅ You're now compliant with our security policy

**Next time you log in:**
- Enter your email and password
- Enter the 6-digit code from your authenticator app

**Don't forget to save your backup codes!**

Thank you for helping us keep LeaseAI secure.

[CTO Name]
```

---

## 7. ONGOING MONITORING

### 7.1 Monthly Audit (Starting Dec 2026)

Run this query monthly to ensure compliance:

```sql
-- Verify all admins have MFA enabled
SELECT 
    email,
    role,
    CASE 
        WHEN (SELECT COUNT(*) FROM auth.mfa_factors WHERE user_id = users.id AND status = 'verified') > 0 
        THEN '✅ Compliant'
        ELSE '❌ NON-COMPLIANT'
    END as mfa_status,
    last_sign_in_at
FROM auth.users
WHERE role = 'admin'
ORDER BY email;
```

**Expected result:** All admins show "✅ Compliant"

### 7.2 New Admin User Process

When creating new admin users:

1. [ ] Create user account
2. [ ] Send welcome email with 2FA setup instructions
3. [ ] **Do NOT grant admin role until 2FA is verified**
4. [ ] Verify MFA enabled (run audit query)
5. [ ] Grant admin role
6. [ ] Document in access log

---

## 8. PHASE 2: ALL USERS (January 2027)

### 8.1 Timeline

- **Dec 1, 2026:** Announce to all users: "MFA required for all accounts starting Jan 1, 2027"
- **Dec 15, 2026:** Reminder email #1
- **Dec 27, 2026:** Final reminder
- **Jan 1, 2027:** Enforce MFA for all users

### 8.2 All-User Enforcement

**Less strict than admin enforcement:**
- Grace period: 7 days (Jan 1-7)
- After grace period: Users cannot log in without enabling MFA
- Support available to help users set up MFA

---

## 9. EXCEPTION PROCESS

### 9.1 Valid Exceptions (RARE)

**Acceptable reasons:**
- User is traveling and lost phone (temporary exception, max 7 days)
- Technical issue prevents MFA setup (work with IT to resolve)

**Unacceptable reasons:**
- "I don't want to use MFA"
- "It's too inconvenient"
- "I forgot"

### 9.2 Exception Request Form

**To request an exception:**
1. Email CTO with:
   - Reason for exception
   - How long exception is needed
   - Alternative security measures (if any)
2. CTO reviews and approves/denies
3. If approved: Document in exception log, set expiration date
4. Monitor exception users closely

### 9.3 Exception Log

| User | Reason | Approved By | Start Date | End Date | Status |
|------|--------|-------------|------------|----------|--------|
|  |  |  |  |  |  |

---

## 10. SUCCESS METRICS

### 10.1 KPIs

- **Admin MFA Adoption Rate:** 100% by Dec 1, 2026
- **All-User MFA Adoption Rate:** 90%+ by Feb 1, 2027
- **Failed Login Attempts:** Monitor for decrease after MFA
- **MFA Support Tickets:** Track and address common issues

### 10.2 Weekly Tracking (Nov 2026)

| Week | Admins with MFA | Percentage | Notes |
|------|-----------------|------------|-------|
| Nov 1 | 2 / 5 | 40% | Initial baseline |
| Nov 8 | 3 / 5 | 60% | 1 more user enabled |
| Nov 15 | 4 / 5 | 80% | Reminder email sent |
| Nov 22 | 4 / 5 | 80% | 1 user needs follow-up |
| Nov 29 | 5 / 5 | **100%** | ✅ Target achieved! |

---

## 11. TROUBLESHOOTING

### Common Issues:

**Issue:** User lost phone / can't access authenticator app  
**Solution:** Use backup recovery codes (from setup)

**Issue:** User doesn't have backup codes  
**Solution:** Admin temporarily disables MFA, user sets up again

**Issue:** User's phone clock is off (codes don't work)  
**Solution:** Enable "Automatic time" in phone settings

**Issue:** User wants to use SMS instead of authenticator app  
**Solution:** Authenticator app is required for admins (more secure)

---

## 12. COMPLETION SIGN-OFF

**MFA enforcement complete when:**

- [ ] 100% of admin users have MFA enabled
- [ ] Monthly audit process established
- [ ] New admin onboarding includes MFA verification
- [ ] Support process documented and tested
- [ ] Phase 2 (all users) plan communicated

**Completed by:** _____________  
**Date:** _____________  
**Verified by:** _____________  

---

**Document Classification:** INTERNAL USE ONLY
