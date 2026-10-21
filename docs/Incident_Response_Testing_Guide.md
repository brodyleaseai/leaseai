# LeaseAI - Incident Response Testing Guide
**Version:** 1.0  
**Last Updated:** October 2026  
**Owner:** CTO / Security Team

---

## 1. OVERVIEW

### 1.1 Purpose
This guide provides procedures for testing LeaseAI's Incident Response Plan through tabletop exercises and simulations.

### 1.2 Testing Frequency
- **Tabletop Exercise:** Quarterly (minimum annually)
- **Full Simulation:** Annually
- **After Major Changes:** When IR plan is updated

### 1.3 Success Criteria
- All participants understand their roles
- IR plan is followed correctly
- Issues identified and documented
- Plan updated based on lessons learned

---

## 2. INCIDENT RESPONSE PLAN QUICK REFERENCE

### IR Phases (from Information_Security_Policy.md Section 8)

1. **Detect & Report** → Report via security@leaseai.com
2. **Assess** → Security team assesses severity within 1 hour
3. **Contain** → Isolate affected systems within 4 hours
4. **Investigate** → Root cause analysis within 24 hours
5. **Remediate** → Fix vulnerability within 7 days
6. **Notify** → Customers notified within 72 hours if data affected
7. **Document** → Incident report completed within 14 days

### Severity Levels
- **Critical:** Data breach, ransomware, customer data exposed
- **High:** Unauthorized admin access, production system compromise
- **Medium:** Failed security control, suspicious activity
- **Low:** Policy violation, phishing attempt (unsuccessful)

---

## 3. TABLETOP EXERCISE FORMAT

### 3.1 Preparation (1 week before)

**Facilitator:**
1. Select scenario (from Section 4 below)
2. Customize details to match current environment
3. Prepare scenario packet
4. Schedule 90-minute session
5. Invite participants:
   - CTO (Incident Commander)
   - Developers (Technical Response)
   - Support Staff (Customer Communication)
   - Founder/CEO (Executive Decision-Making)

**Participants:**
1. Review Incident Response Plan (Information_Security_Policy.md Section 8)
2. Review roles and responsibilities
3. Prepare questions

### 3.2 Exercise Structure (90 minutes)

**Introduction (10 minutes)**
- Welcome and objectives
- Ground rules (no wrong answers, safe space)
- Scenario overview

**Scenario Walkthrough (50 minutes)**
- Facilitator presents initial scenario
- Participants discuss response
- Facilitator injects additional information
- Participants adapt response
- Continue through all IR phases

**Debrief (30 minutes)**
- What went well?
- What gaps were identified?
- What needs to be improved?
- Action items

### 3.3 Documentation

**During exercise:**
- Scribe documents all decisions and discussions
- Note gaps, questions, and issues

**After exercise:**
- Complete Exercise Report (template in Section 5)
- Create action items in GitHub Issues
- Update IR plan if needed
- Schedule next exercise

---

## 4. TABLETOP SCENARIOS

### Scenario 1: Customer Data Breach (Critical)

**Initial Notification:**

> **From:** alerts@supabase.com  
> **Subject:** Unusual Database Activity Detected  
> **Date:** Today, 2:15 AM  
> 
> Unusual activity detected on your LeaseAI production database:
> - 500+ SELECT queries from unknown IP address: 203.0.113.47 (Russia)
> - Queries accessing `leases` table and extracting customer data
> - Activity lasted 15 minutes (1:45 AM - 2:00 AM)
> - Estimated 5,000 lease records accessed
> 
> This IP is not associated with any known LeaseAI systems.

**Discussion Questions:**
1. Who discovers this alert? What time of day is it?
2. Who do you notify first?
3. How quickly can you assemble the incident response team?
4. What immediate containment actions do you take?
5. How do you determine which customers are affected?
6. Do you need to notify customers within 72 hours (GDPR)?
7. What evidence do you preserve for investigation?
8. How do you investigate the root cause?
9. What systems do you check for compromise?
10. How do you prevent this from happening again?

**Injects (Facilitator adds these during discussion):**

**Inject 1 (after 10 minutes):**
> Investigation reveals that the Supabase service role key was leaked in a GitHub commit 3 months ago. The key is still active.

**Discussion:** How does this change your response? What do you do now?

**Inject 2 (after 20 minutes):**
> You receive an email from a customer: "I just got a call from someone claiming to be from LeaseAI asking for my password. Is this legitimate?"

**Discussion:** Is this related? How do you respond to the customer?

**Inject 3 (after 30 minutes):**
> You find that the attacker also accessed the `users` table, potentially exposing email addresses and hashed passwords for 200 users.

**Discussion:** Does this change your notification strategy? Who else needs to know?

---

### Scenario 2: Ransomware Attack (Critical)

**Initial Discovery:**

> **Developer** logs in Monday morning (9:00 AM) and notices:
> - Streamlit application shows error: "Database connection failed"
> - Supabase dashboard shows all tables renamed to `[table_name]_LOCKED`
> - Email in inbox with subject: "Your data has been encrypted - Pay 5 BTC to decrypt"

**Ransom Note:**
```
Your LeaseAI database has been encrypted.

To decrypt your data, send 5 Bitcoin (approximately $200,000 USD) to:
[Bitcoin address]

You have 48 hours before the decryption key is deleted.
We have also exfiltrated 50GB of customer data. If you do not pay, 
we will publish this data on the dark web.

Do not contact police or FBI - we are monitoring.
```

**Discussion Questions:**
1. What is your immediate first action?
2. Do you pay the ransom? Why or why not?
3. How do you verify backups are not also encrypted?
4. Who do you notify? (Police? FBI? Customers? Insurance?)
5. How quickly can you restore from backup?
6. How do you verify the restored data is clean (no malware)?
7. What do you tell customers during downtime?
8. What legal obligations do you have (notification, reporting)?
9. How do you prevent this in the future?
10. Do you go public with this incident?

**Injects:**

**Inject 1 (after 10 minutes):**
> You check backups and find that last night's backup is also encrypted. The most recent clean backup is 7 days old.

**Discussion:** Do you accept 7 days of data loss? What are the alternatives?

**Inject 2 (after 25 minutes):**
> Your cyber liability insurance company calls and asks: "Did you have MFA enforced for all admin accounts?" You realize you didn't.

**Discussion:** How does this affect your insurance claim?

**Inject 3 (after 40 minutes):**
> A news reporter emails: "We heard LeaseAI was hacked. Can you confirm?"

**Discussion:** How do you handle public communication?

---

### Scenario 3: Insider Threat (High)

**Initial Discovery:**

> **Friday, 4:45 PM:** A developer (Bob) resigns abruptly, citing "personal reasons." He refuses to work the standard 2-week notice period and says his last day is today.
> 
> **Monday, 9:00 AM:** You receive an alert from the audit log system:
> - Bob accessed the production database on Friday at 4:55 PM (10 minutes after resignation)
> - Exported 10,000 lease records to CSV
> - Deleted his user account at 5:00 PM
> - Audit log shows he accessed admin panel and downloaded customer list

**Discussion Questions:**
1. What is your immediate concern?
2. What data did Bob potentially steal?
3. Is this a security incident or just an employee leaving?
4. Who do you notify? (Police? Customers? Legal?)
5. What evidence do you need to preserve?
6. Can you prove Bob's intent (malicious vs. backing up work)?
7. How do you prevent this in the future?
8. Do you have any legal recourse?
9. What do you tell customers (if anything)?
10. How do you audit what else Bob might have done?

**Injects:**

**Inject 1 (after 15 minutes):**
> You find Bob's LinkedIn profile has been updated: "Just joined [Competitor Company] as Senior Developer!"

**Discussion:** Does this change your assessment of his intent?

**Inject 2 (after 25 minutes):**
> A customer forwards you an email from Bob's personal email address offering "lease abstraction consulting services" at a discount.

**Discussion:** What do you do now?

---

### Scenario 4: Phishing Attack (Medium)

**Initial Discovery:**

> **Wednesday, 10:30 AM:** Support staff member (Alice) reports:
> "I just clicked on a link in an email that looked like it was from our CEO. It asked me to reset my Supabase password. After I entered my password, it said 'error' and now I can't log in. Was that legitimate?"
> 
> The email:
> ```
> From: founder@leaseai-secure.com (note the typo)
> Subject: URGENT: Reset your Supabase password immediately
> 
> Alice,
> 
> We detected suspicious activity on your account. Please reset your 
> Supabase password immediately by clicking here:
> [Fake Link]
> 
> - CEO Name
> ```

**Discussion Questions:**
1. What is your immediate response?
2. Was Alice's account compromised?
3. What access does Alice have? (Read-only? Admin?)
4. What can an attacker do with Alice's credentials?
5. How do you investigate if data was accessed?
6. How do you prevent this from happening again?
7. Do you need to notify anyone?
8. How do you educate staff to avoid phishing?

**Injects:**

**Inject 1 (after 10 minutes):**
> Audit logs show that Alice's account accessed 50 customer leases in the 10 minutes after she clicked the link.

**Discussion:** Does this change the severity? What now?

**Inject 2 (after 20 minutes):**
> You receive the same phishing email yourself, and notice 3 other employees also received it.

**Discussion:** Is this a targeted attack on LeaseAI?

---

### Scenario 5: Third-Party Vendor Breach (High)

**Initial Discovery:**

> **News Alert:** Supabase announces data breach affecting 1% of customers
> 
> "Supabase has identified unauthorized access to a subset of customer project metadata including project names, database connection strings, and API keys. Customer data within databases was NOT accessed. All affected customers are being notified."
> 
> You receive an email from Supabase: "Your project may have been affected..."

**Discussion Questions:**
1. What is your immediate concern?
2. What data is at risk? (Database itself? Connection strings? API keys?)
3. Do you need to rotate all API keys immediately?
4. How do you verify if customer data was accessed?
5. Do you notify customers? (It was Supabase's breach, not yours)
6. How does this affect your SOC 2 compliance?
7. What do you tell customers who ask about this?
8. Do you consider switching vendors?
9. How do you audit for unauthorized access to your systems?

**Injects:**

**Inject 1 (after 15 minutes):**
> A customer emails: "I saw Supabase had a breach. Was my lease data exposed?"

**Discussion:** How do you respond?

**Inject 2 (after 30 minutes):**
> Your cyber liability insurance asks: "Did you have a Data Processing Agreement with Supabase?"

**Discussion:** Do you? Does it matter?

---

## 5. EXERCISE REPORT TEMPLATE

```markdown
# Incident Response Tabletop Exercise Report

**Date:** ___________  
**Facilitator:** ___________  
**Scenario:** ___________  

## Participants
- 
- 
- 

## Scenario Summary


## Exercise Objectives
1. 
2. 
3. 

## Key Decisions Made
| Decision | Time | Rationale |
|----------|------|-----------|
|  |  |  |

## Strengths Identified
- 
- 
- 

## Gaps Identified
| Gap | Impact | Priority |
|-----|--------|----------|
|  |  |  |

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
|  |  |  |  |

## IR Plan Updates Needed
- 
- 

## Lessons Learned
1. 
2. 
3. 

## Next Exercise
**Date:** ___________  
**Scenario:** ___________  

---

**Prepared by:** ___________  
**Reviewed by:** ___________  
**Date:** ___________
```

---

## 6. POST-EXERCISE ACTIONS

### Within 1 Week:
1. ✅ Complete exercise report
2. ✅ Create GitHub issues for action items
3. ✅ Update IR plan (if needed)
4. ✅ Share report with leadership

### Within 1 Month:
1. ✅ Complete all high-priority action items
2. ✅ Provide additional training (if gaps found)
3. ✅ Update runbooks or playbooks

### Quarterly:
1. ✅ Schedule next tabletop exercise
2. ✅ Review progress on action items

---

## 7. FULL SIMULATION (Annual)

### Difference from Tabletop:
- **Tabletop:** Discussion-based (what would you do?)
- **Simulation:** Hands-on (actually do it in test environment)

### Simulation Requirements:
1. Test environment that mirrors production
2. Ability to simulate attack (e.g., fake ransomware on test DB)
3. All teams participate (not just discussion)
4. Actually perform IR steps (containment, investigation, recovery)
5. Measure response times

### Simulation Scenarios:
- Restore from backup (actual restore, measure time)
- Failover to backup region (if multi-region)
- Communication drill (send fake notifications, measure speed)

---

## 8. CHECKLIST: IR PLAN READINESS

Before any exercise, verify:
- [ ] IR plan is up to date
- [ ] Contact list is current
- [ ] Backup restore has been tested (last 30 days)
- [ ] Escalation process is documented
- [ ] Communication templates are ready
- [ ] Legal counsel contact info is available
- [ ] Cyber insurance policy is active
- [ ] Forensics tools/vendors are identified

---

**Document Classification:** CONFIDENTIAL - Internal Use Only
