# LeaseAI - Change Management Policy
**Version:** 1.0  
**Effective Date:** October 2026  
**Owner:** CTO / Development Lead

---

## 1. PURPOSE

This Change Management Policy establishes a formal process for requesting, approving, testing, and implementing changes to LeaseAI's production systems to minimize risk and ensure stability.

---

## 2. SCOPE

This policy applies to all changes affecting:
- Production application code
- Database schema changes
- Infrastructure configuration
- Third-party integrations
- Security controls
- User-facing features

---

## 3. CHANGE CATEGORIES

### 3.1 Standard Changes (Pre-Approved)
**Definition:** Low-risk, routine changes with documented procedures

**Examples:**
- Dependency updates (patch versions)
- Documentation updates
- UI text/copy changes
- Non-breaking bug fixes

**Approval:** Automatic (follows standard procedure)  
**Testing:** Unit tests must pass  
**Notification:** None required

### 3.2 Normal Changes (Approval Required)
**Definition:** Medium-risk changes requiring review and approval

**Examples:**
- New features
- Database migrations
- API changes (backwards compatible)
- Configuration changes
- Dependency updates (minor/major versions)

**Approval:** 1 reviewer (CTO or senior developer)  
**Testing:** Unit + integration tests, staging deployment  
**Notification:** Team notification before deployment

### 3.3 Emergency Changes (Post-Approval)
**Definition:** Urgent changes to resolve critical production issues

**Examples:**
- Security vulnerability patches
- Critical bug fixes causing outages
- Data loss prevention

**Approval:** Verbal/Slack approval from CTO, formal approval within 24 hours  
**Testing:** Minimum viable testing  
**Notification:** All stakeholders immediately

### 3.4 Major Changes (Full Review)
**Definition:** High-risk changes with significant impact

**Examples:**
- Architecture changes
- Breaking API changes
- Data model changes (breaking)
- Third-party vendor changes
- Infrastructure migrations

**Approval:** CTO + Founder approval, full team review  
**Testing:** Full test suite + manual QA + staging soak test (48 hours)  
**Notification:** All stakeholders 1 week in advance

---

## 4. CHANGE WORKFLOW

### Step 1: Request Change (Change Requester)

**Create GitHub Issue or Pull Request:**

1. Use change request template (`.github/ISSUE_TEMPLATE/change_request.md`)
2. Provide:
   - Change description
   - Business justification
   - Risk assessment
   - Rollback plan
   - Testing plan
3. Label appropriately: `change:standard`, `change:normal`, `change:emergency`, `change:major`
4. Assign to appropriate reviewer

### Step 2: Risk Assessment (Change Requester)

**Complete risk evaluation:**

| Risk Factor | Low (1) | Medium (2) | High (3) |
|-------------|---------|------------|----------|
| **Impact on users** | No user impact | Minor UX change | Major functionality change |
| **Data risk** | No data touched | Data read/display | Data write/migration |
| **System complexity** | Single file change | Multiple files | Architecture change |
| **Rollback difficulty** | Easy (code revert) | Medium (DB migration) | Difficult (data migration) |
| **Dependencies** | None | Internal dependencies | External dependencies |

**Risk Score = Sum of all factors**
- **1-5:** Standard change
- **6-10:** Normal change
- **11-15:** Major change

### Step 3: Review & Approval (Reviewer)

**Reviewer checklist:**

- [ ] Change description is clear and complete
- [ ] Business justification is valid
- [ ] Risk assessment is accurate
- [ ] Testing plan is adequate
- [ ] Rollback plan is documented
- [ ] Code quality meets standards
- [ ] Security implications considered
- [ ] No secrets or sensitive data in code
- [ ] Documentation updated (if needed)
- [ ] Database migrations are reversible (if applicable)

**Approval:**
- **Standard:** Auto-approved (CI checks pass)
- **Normal:** 1 approval required
- **Emergency:** Verbal approval, formal within 24 hours
- **Major:** 2 approvals + team review

### Step 4: Testing (Developer + QA)

**Required tests by change type:**

| Change Type | Unit Tests | Integration Tests | Staging Deployment | Manual QA | Production Smoke Test |
|-------------|------------|-------------------|--------------------|-----------|-----------------------|
| Standard | ✅ Required | Optional | Optional | No | No |
| Normal | ✅ Required | ✅ Required | ✅ Required | Recommended | ✅ Required |
| Emergency | Best effort | Best effort | If time permits | No | ✅ Required |
| Major | ✅ Required | ✅ Required | ✅ Required (48h soak) | ✅ Required | ✅ Required |

**Staging environment:**
- All normal and major changes MUST be tested in staging
- Staging environment must mirror production configuration
- Soak test: Run in staging for 48 hours (major changes only)

### Step 5: Schedule Deployment (Change Manager / CTO)

**Deployment windows:**

| Change Type | Preferred Window | Blackout Periods |
|-------------|------------------|------------------|
| Standard | Anytime | None |
| Normal | Monday-Thursday, 9 AM - 3 PM PT | Fridays, weekends, holidays |
| Emergency | Immediate | None |
| Major | Tuesday-Wednesday, 9 AM - 12 PM PT | Fridays, weekends, holidays, month-end |

**Notification requirements:**
- **Standard:** No notification
- **Normal:** Team notification 24 hours in advance
- **Emergency:** Stakeholders notified immediately
- **Major:** All stakeholders 1 week in advance, customer notification if user-facing

### Step 6: Deploy Change (Developer)

**Deployment checklist:**

- [ ] All approvals obtained
- [ ] All tests passed
- [ ] Staging deployment successful
- [ ] Rollback plan ready
- [ ] Monitoring dashboard open
- [ ] Team available for support (normal hours)
- [ ] Database backup verified (if DB changes)
- [ ] Feature flags configured (if applicable)

**Deployment steps:**

1. **Pre-deployment:**
   - Announce in Slack: `#deployments` channel
   - Verify production backup is recent (<24 hours)
   - Tag release in Git: `git tag v1.2.3`

2. **Deployment:**
   - Push to production branch
   - Monitor deployment logs
   - Run automated smoke tests
   - Verify key functionality manually

3. **Post-deployment:**
   - Monitor error logs for 30 minutes
   - Check user impact metrics (if applicable)
   - Announce completion in Slack
   - Update change ticket status

### Step 7: Verify & Monitor (Developer + Operations)

**Verification checklist:**

- [ ] Application is running (uptime check)
- [ ] No error spikes in logs
- [ ] Key user flows working (smoke test)
- [ ] Database queries performing normally
- [ ] API response times normal
- [ ] No customer complaints (first 24 hours)

**Monitoring period:**
- **Standard:** 30 minutes
- **Normal:** 2 hours
- **Emergency:** 4 hours
- **Major:** 48 hours (intensive), 1 week (monitoring)

### Step 8: Close Change (Change Requester)

**Completion steps:**

1. Verify change is working as expected
2. Document any issues encountered
3. Update change log
4. Close change ticket
5. Post-implementation review (major changes only)

---

## 5. ROLLBACK PROCEDURES

### 5.1 When to Rollback

**Mandatory rollback triggers:**
- Application is down or inaccessible
- Critical functionality is broken
- Data loss or corruption detected
- Security vulnerability introduced
- >10% error rate spike

**Optional rollback triggers:**
- Minor UX issues (can be fixed forward)
- Performance degradation <20%
- Non-critical bugs (can be fixed in next deploy)

### 5.2 Rollback Process

**Code rollback (most common):**

```bash
# 1. Revert Git commit
git revert <commit-hash>
git push origin main

# Or roll back to previous tag
git reset --hard v1.2.2
git push origin main --force

# 2. Redeploy previous version
# (triggers CI/CD automatically)

# 3. Verify rollback successful
# Run smoke tests
```

**Database rollback (if migration applied):**

```bash
# 1. Run down migration (if available)
# Via Supabase dashboard or migration tool

# 2. Restore from backup (if no down migration)
# See Backup_and_Disaster_Recovery_Guide.md

# 3. Verify data integrity
```

**Emergency rollback (critical outage):**

1. **Immediate action:** Revert code or disable feature flag
2. **Communicate:** Alert all stakeholders
3. **Document:** Log everything for post-mortem
4. **Fix forward:** Plan permanent fix after stabilization

---

## 6. CHANGE CALENDAR

### Blackout Periods (No deployments except emergencies)

- **Fridays after 12 PM PT**
- **Weekends**
- **US Federal Holidays**
- **Month-end / quarter-end (last 2 business days)**
- **Black Friday / Cyber Monday week** (if applicable)

### Preferred Deployment Windows

- **Tuesday 10 AM - 2 PM PT** (best for major changes)
- **Wednesday 10 AM - 2 PM PT**
- **Monday-Thursday 9 AM - 5 PM PT** (normal changes)

---

## 7. CHANGE LOG

All changes must be logged in `CHANGELOG.md`:

```markdown
## [1.2.3] - 2026-10-21

### Added
- New Security Dashboard with audit logs and security events

### Changed
- Updated password policy to require 12+ characters

### Fixed
- Bug where CAM reconciliation PDF failed to generate

### Security
- Enforced MFA for all admin users
```

**Format:** Follow [Keep a Changelog](https://keepachangelog.com/) standard

---

## 8. POST-IMPLEMENTATION REVIEW

### Required for Major Changes

**Within 1 week of deployment:**

1. **What went well?**
   - Successes, smooth processes

2. **What went wrong?**
   - Issues, unexpected problems

3. **What could be improved?**
   - Process improvements, lessons learned

4. **Action items:**
   - Concrete steps to improve future changes

**Document in:** `.github/post_mortems/YYYY-MM-DD-change-name.md`

---

## 9. METRICS & REPORTING

### Change Metrics (tracked monthly)

- Total changes deployed
- Changes by type (standard, normal, emergency, major)
- Changes requiring rollback (target: <5%)
- Average time from request to deployment
- Changes deployed outside blackout periods (target: 0)

### Success Criteria

- **Change success rate:** >95% (no rollback required)
- **Emergency changes:** <10% of total changes
- **Approval SLA:** <24 hours (normal), <1 hour (emergency)
- **Deployment SLA:** <48 hours after approval (normal)

---

## 10. ROLES & RESPONSIBILITIES

| Role | Responsibilities |
|------|------------------|
| **Change Requester** | Create change request, implement change, test, deploy |
| **Change Reviewer** | Review and approve changes, ensure quality standards |
| **Change Manager (CTO)** | Oversee change process, approve major changes, manage calendar |
| **Operations** | Monitor production, assist with rollbacks |
| **QA (if applicable)** | Test major changes in staging |

---

## 11. EXCEPTIONS

**Exception process:**

1. Request exception from CTO
2. Document business justification
3. Accept additional risk
4. Add extra monitoring/controls

**Valid exception reasons:**
- Customer-facing critical bug
- Security vulnerability
- Legal/compliance requirement
- Executive directive

**Invalid exception reasons:**
- "We're behind schedule"
- "Customer is impatient"
- "I don't want to wait for approval"

---

## 12. POLICY REVIEW

- **Review frequency:** Annually (October)
- **Owner:** CTO
- **Next review:** October 2027

---

## 13. RELATED DOCUMENTS

- Information Security Policy (Section 6: Application Security)
- Incident Response Plan
- Backup and Disaster Recovery Guide
- SOC 2 Gap Analysis (CC8: Change Management)

---

**Document Classification:** CONFIDENTIAL - Internal Use Only
