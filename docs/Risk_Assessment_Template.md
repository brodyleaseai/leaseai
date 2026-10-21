# LeaseAI - Risk Assessment Template
**Assessment Date:** _______________  
**Next Review Date:** _______________  
**Conducted By:** _______________  
**Reviewed By:** _______________  

---

## 1. OVERVIEW

### 1.1 Purpose
This risk assessment identifies, evaluates, and prioritizes information security risks to LeaseAI's systems, data, and operations.

### 1.2 Scope
- All information systems and applications
- All data (customer data, company data, backups)
- All personnel (employees, contractors, vendors)
- All physical and virtual infrastructure
- All third-party services and integrations

### 1.3 Assessment Methodology
- **Likelihood:** Rare (1), Unlikely (2), Possible (3), Likely (4), Almost Certain (5)
- **Impact:** Insignificant (1), Minor (2), Moderate (3), Major (4), Catastrophic (5)
- **Risk Score:** Likelihood × Impact (1-25)
- **Risk Level:** 
  - **Low (1-5):** Accept with monitoring
  - **Medium (6-12):** Mitigate with controls
  - **High (15-25):** Immediate action required

---

## 2. ASSET INVENTORY

### 2.1 Information Assets

| Asset | Classification | Location | Owner | Business Impact |
|-------|----------------|----------|-------|-----------------|
| Customer lease documents | Restricted | Supabase Storage | CTO | Critical |
| Extracted lease data | Restricted | Supabase DB | CTO | Critical |
| User credentials | Restricted | Supabase Auth | CTO | Critical |
| Source code | Confidential | GitHub | CTO | High |
| API keys / secrets | Restricted | Environment variables | CTO | Critical |
| Audit logs | Confidential | Supabase DB | CTO | High |
| Backup data | Restricted | Supabase / AWS S3 | CTO | Critical |
| Customer contact info | Restricted | Supabase DB | CTO | High |
| Financial data (billing) | Confidential | Stripe | CFO | High |
| Marketing materials | Public | Website | Marketing | Low |

### 2.2 System Assets

| System | Purpose | Hosting | Access Level | Criticality |
|--------|---------|---------|--------------|-------------|
| Streamlit application | Main application | Streamlit Cloud | Public (auth required) | Critical |
| Supabase database | Data storage | Supabase (AWS) | Service role only | Critical |
| GitHub repository | Source code | GitHub | Developers only | High |
| OpenAI API | AI extraction | OpenAI | API key auth | High |
| Email system (SMTP) | Notifications | TBD | Admin only | Medium |
| Domain / DNS | Website access | Domain registrar | Admin only | High |

### 2.3 Personnel

| Role | Access Level | Critical Systems Access |
|------|--------------|-------------------------|
| Founder/CEO | Admin | All systems |
| Developers | Developer | GitHub, Supabase, OpenAI |
| Support staff | Support | Supabase (read-only) |
| Contractors | Limited | Case-by-case |

---

## 3. THREAT IDENTIFICATION

### 3.1 External Threats

| Threat | Description | Threat Actor |
|--------|-------------|--------------|
| **Unauthorized access** | Attacker gains access to customer data | Cybercriminals, competitors |
| **Data breach** | Customer lease data exposed or stolen | Cybercriminals, nation-states |
| **Ransomware** | Files encrypted, ransom demanded | Organized crime |
| **DDoS attack** | Service unavailable due to traffic flood | Hacktivists, competitors |
| **Phishing** | Employees tricked into revealing credentials | Cybercriminals |
| **SQL injection** | Database compromised via application vulnerability | Cybercriminals |
| **API abuse** | OpenAI or other API keys stolen and misused | Script kiddies, competitors |
| **Supply chain attack** | Compromised dependency introduces malware | Nation-states, APT groups |
| **Social engineering** | Attacker impersonates employee to gain access | Cybercriminals |

### 3.2 Internal Threats

| Threat | Description | Threat Actor |
|--------|-------------|--------------|
| **Insider threat** | Malicious employee exfiltrates data | Disgruntled employee |
| **Accidental data loss** | Employee accidentally deletes data | Any employee |
| **Credential sharing** | Employees share passwords, weakening security | Any employee |
| **Unpatched systems** | Vulnerabilities not patched, exploited | N/A (negligence) |
| **Poor access controls** | Over-privileged users access sensitive data | N/A (misconfiguration) |

### 3.3 Environmental Threats

| Threat | Description |
|--------|-------------|
| **Natural disaster** | Fire, flood, earthquake affects data center |
| **Power outage** | Extended outage causes service disruption |
| **Internet outage** | ISP failure prevents access to cloud services |

---

## 4. VULNERABILITY ASSESSMENT

### 4.1 Technical Vulnerabilities

| Vulnerability | Affected System | Exploitability | Current Controls |
|---------------|-----------------|----------------|------------------|
| Weak passwords | User accounts | High | Password policy (12+ chars) |
| No MFA enforcement | Admin accounts | High | MFA available but not required |
| Outdated dependencies | Application code | Medium | Dependabot alerts enabled |
| Missing rate limiting | API endpoints | Medium | Basic rate limiting (Supabase) |
| No WAF (Web Application Firewall) | Web application | Medium | None (rely on Streamlit/Supabase) |
| Missing intrusion detection | All systems | Medium | Audit logging only |
| No data encryption at rest (old backups) | Backup storage | Low | New backups encrypted (AES-256) |
| Session timeout too long | Application | Low | 30-day "remember me" |

### 4.2 Process Vulnerabilities

| Vulnerability | Process | Impact | Current Controls |
|---------------|---------|--------|------------------|
| No formal change management | Code deployment | High | None (ad-hoc deploys) |
| No disaster recovery testing | Backup restore | High | None (no DR drills) |
| No vendor risk assessment | Third-party services | Medium | None (rely on SOC 2 certs) |
| No security awareness training | All staff | Medium | None |
| No incident response plan tested | Incident response | High | Plan documented but not tested |

### 4.3 Physical Vulnerabilities

| Vulnerability | Location | Impact | Current Controls |
|---------------|----------|--------|------------------|
| Home office security | Founder's home | Medium | Standard home security |
| Laptop theft/loss | Remote work | Medium | Full-disk encryption |
| Cloud data center access | Supabase/AWS | Low | Inherit from cloud provider (SOC 2) |

---

## 5. RISK REGISTER

### 5.1 Critical Risks (15-25)

| Risk ID | Risk Description | Likelihood | Impact | Risk Score | Mitigation Strategy | Owner | Status |
|---------|------------------|------------|--------|------------|---------------------|-------|--------|
| **R-001** | Customer data breach due to unauthorized access | 3 | 5 | **15** | Enforce MFA for all admins, quarterly access reviews, intrusion detection | CTO | In Progress |
| **R-002** | Ransomware attack encrypts customer data | 3 | 5 | **15** | Daily backups, backup testing, offline backup copies, security training | CTO | Partial |
| **R-003** | Data loss due to no disaster recovery testing | 3 | 5 | **15** | Monthly backup restore tests, documented DR plan, annual DR drill | CTO | Planned |
| **R-004** | Production outage due to uncontrolled code changes | 4 | 4 | **16** | Implement change management workflow, staging environment, rollback plan | CTO | Planned |

### 5.2 High Risks (10-14)

| Risk ID | Risk Description | Likelihood | Impact | Risk Score | Mitigation Strategy | Owner | Status |
|---------|------------------|------------|--------|------------|---------------------|-------|--------|
| **R-005** | API keys exposed in code or logs | 3 | 4 | **12** | Secrets scanning (GitHub), rotate keys quarterly, audit logging | CTO | In Progress |
| **R-006** | SQL injection compromises database | 2 | 5 | **10** | Parameterized queries, input validation, WAF, penetration testing | CTO | Partial |
| **R-007** | Insider threat: employee exfiltrates data | 2 | 5 | **10** | Audit logging, least privilege, background checks, exit interviews | HR/CTO | Partial |
| **R-008** | DDoS attack causes service outage | 3 | 3 | **9** | CDN, rate limiting, DDoS protection (Cloudflare if needed) | CTO | Accept |
| **R-009** | Phishing attack compromises employee account | 3 | 4 | **12** | Security awareness training, MFA, phishing simulations | CTO | Planned |
| **R-010** | Third-party vendor breach (Supabase, OpenAI) | 2 | 5 | **10** | Vendor risk assessment, monitor vendor security posture, contracts | CTO | Accept |

### 5.3 Medium Risks (6-9)

| Risk ID | Risk Description | Likelihood | Impact | Risk Score | Mitigation Strategy | Owner | Status |
|---------|------------------|------------|--------|------------|---------------------|-------|--------|
| **R-011** | Outdated dependencies introduce vulnerabilities | 3 | 3 | **9** | Dependabot, patch within 30 days (critical), 90 days (high) | CTO | Partial |
| **R-012** | No security training leads to policy violations | 3 | 2 | **6** | Annual security awareness training, policy acknowledgment | CTO | Planned |
| **R-013** | Session hijacking due to long session timeout | 2 | 3 | **6** | Reduce session timeout to 7 days, require re-auth for sensitive actions | CTO | Accept |
| **R-014** | Laptop theft exposes credentials or data | 2 | 3 | **6** | Full-disk encryption, password manager required, remote wipe capability | CTO | Partial |
| **R-015** | No WAF allows application-layer attacks | 2 | 3 | **6** | Consider Cloudflare or AWS WAF if attacks increase | CTO | Accept |

### 5.4 Low Risks (1-5)

| Risk ID | Risk Description | Likelihood | Impact | Risk Score | Mitigation Strategy | Owner | Status |
|---------|------------------|------------|--------|------------|---------------------|-------|--------|
| **R-016** | Natural disaster affects AWS data center | 1 | 4 | **4** | AWS multi-AZ, auto-failover (inherit from Supabase) | CTO | Accept |
| **R-017** | GitHub account compromise | 1 | 4 | **4** | MFA on GitHub, code review required | CTO | Complete |
| **R-018** | Public disclosure of non-sensitive data | 2 | 1 | **2** | Data classification policy, employee training | CTO | Accept |

---

## 6. RISK TREATMENT DECISIONS

### 6.1 Accept
- **R-008:** DDoS attack - Current rate limiting sufficient, upgrade to CDN if needed
- **R-010:** Third-party vendor breach - Vendors are SOC 2 certified, monitor status
- **R-013:** Session hijacking - Current timeout acceptable, no customer complaints
- **R-015:** No WAF - Rely on Supabase/Streamlit protections, reassess if attacks occur
- **R-016:** Natural disaster - AWS provides multi-AZ redundancy
- **R-018:** Public disclosure - Low impact, normal data classification controls

### 6.2 Mitigate
- **R-001:** Customer data breach → **Enforce MFA (Dec 1, 2026), quarterly access reviews**
- **R-002:** Ransomware → **Monthly backup tests, security training, offline backups**
- **R-003:** Data loss → **Monthly restore tests (starting Nov 2026), annual DR drill**
- **R-004:** Production outage → **Change management workflow (by Dec 31, 2026)**
- **R-005:** API key exposure → **Secrets scanning, quarterly rotation, audit logging**
- **R-006:** SQL injection → **Code review, input validation, annual penetration test**
- **R-007:** Insider threat → **Audit logging, least privilege, background checks**
- **R-009:** Phishing → **Security training (Q1 2027), quarterly phishing simulations**
- **R-011:** Outdated dependencies → **Patch SLA: 30 days (critical), 90 days (high)**
- **R-012:** No security training → **Annual training starting Q1 2027**
- **R-014:** Laptop theft → **Full-disk encryption required, password manager**

### 6.3 Transfer
- **Cyber liability insurance:** $1M-$5M coverage (purchase by Q1 2027)

### 6.4 Avoid
- None identified (no risks requiring complete activity cessation)

---

## 7. CONTROL EFFECTIVENESS

### 7.1 Existing Controls Assessment

| Control | Effectiveness | Evidence | Improvement Needed |
|---------|---------------|----------|---------------------|
| Encryption (TLS 1.3, AES-256) | Effective | Supabase config, SSL cert | None |
| Password policy (12+ chars) | Effective | Supabase Auth config | None |
| Audit logging | Effective | Phase 5 implementation | Integrate into all modules |
| MFA available | Partially Effective | Available but not enforced | **Enforce for admins by Dec 1** |
| Code review | Partially Effective | GitHub branch protection | Require approval before merge |
| Dependency scanning | Effective | Dependabot enabled | None |
| Static code analysis | Partially Effective | Bandit tool created | **Automate in CI/CD** |
| Backup & restore | Partially Effective | Daily backups | **Test restores monthly** |
| Incident response plan | Ineffective | Documented but not tested | **Conduct tabletop exercise** |
| Change management | Ineffective | None | **Implement workflow** |

---

## 8. RISK TREATMENT ROADMAP

### November 2026 (This Month)
- ✅ Enforce MFA for all admin users
- ✅ Automate SAST in CI/CD (Bandit)
- ✅ Conduct first backup restore test
- ✅ Implement secrets scanning (GitHub)

### December 2026
- ✅ Implement change management workflow
- ✅ Conduct quarterly access review (first one)
- ✅ Rotate all API keys
- ✅ Test incident response plan (tabletop)

### Q1 2027
- ✅ Security awareness training (all staff)
- ✅ Purchase cyber liability insurance
- ✅ Phishing simulation (first one)
- ✅ Vendor risk assessment (Supabase, OpenAI)

### Q2 2027
- ✅ Annual penetration test
- ✅ Disaster recovery drill (full test)
- ✅ SOC 2 Type I audit

---

## 9. RESIDUAL RISK ASSESSMENT

After implementing all mitigations:

| Risk Level | Count | Acceptable? |
|------------|-------|-------------|
| Critical (15-25) | 0 | N/A |
| High (10-14) | 2 | Yes (third-party risk, accept with monitoring) |
| Medium (6-9) | 5 | Yes |
| Low (1-5) | 11 | Yes |

**Overall Risk Posture:** ACCEPTABLE after mitigation implementation

---

## 10. APPROVAL

**Risk Assessment Completed By:**

Name: _____________________________  
Title: _____________________________  
Signature: _________________________  
Date: ______________________________

**Reviewed and Approved By:**

Name: _____________________________  
Title: _____________________________  
Signature: _________________________  
Date: ______________________________

---

## 11. NEXT REVIEW

- **Next Risk Assessment:** October 2027 (annual)
- **Interim Reviews:** After any significant change (new system, new vendor, security incident)
- **Quarterly Reviews:** Risk register status update (check mitigation progress)

---

**Document Classification:** CONFIDENTIAL - Internal Use Only
