# LeaseAI - Information Security Policy
**Version:** 1.0  
**Effective Date:** October 2026  
**Review Date:** Annually (October each year)  
**Owner:** Chief Information Security Officer / Founder

---

## 1. PURPOSE & SCOPE

### 1.1 Purpose
This Information Security Policy establishes LeaseAI's commitment to protecting information assets and defines security standards for all systems, data, and personnel.

### 1.2 Scope
This policy applies to:
- All LeaseAI employees, contractors, and third-party service providers
- All information systems, applications, and data (including customer data)
- All network infrastructure, cloud services, and physical facilities
- All devices used to access LeaseAI systems (company-issued and BYOD)

---

## 2. DATA CLASSIFICATION

LeaseAI classifies data into four categories:

### 2.1 Public
- **Definition:** Information approved for public disclosure
- **Examples:** Marketing materials, public website content, press releases
- **Controls:** No special protection required
- **Retention:** Indefinite

### 2.2 Internal
- **Definition:** Information for internal use only, minimal risk if disclosed
- **Examples:** Internal memos, company policies, non-sensitive product documentation
- **Controls:** Access limited to employees and authorized contractors
- **Retention:** 3 years minimum

### 2.3 Confidential
- **Definition:** Sensitive business information that could harm the company if disclosed
- **Examples:** Customer lists, financial data, product roadmaps, source code
- **Controls:** Access on need-to-know basis, encryption in transit and at rest
- **Retention:** 7 years

### 2.4 Restricted
- **Definition:** Highly sensitive information subject to legal/regulatory protection
- **Examples:** Customer lease documents, passwords, API keys, PHI, PII
- **Controls:** Strict access controls, encrypted storage, audit logging, MFA required
- **Retention:** 7 years (or per customer contract), secure deletion afterward

---

## 3. ACCESS CONTROL

### 3.1 User Access Management
- **Principle of Least Privilege:** Users granted minimum access required for job function
- **Access Reviews:** Quarterly review of all user access rights
- **Termination:** Access revoked within 24 hours of employment termination

### 3.2 Authentication Requirements
- **Passwords:**
  - Minimum 12 characters
  - Must include uppercase, lowercase, number, and special character
  - Changed every 90 days
  - No password reuse (last 5 passwords)
  - Stored using bcrypt or argon2

- **Multi-Factor Authentication (MFA):**
  - Required for all admin users
  - Required for all production system access
  - Recommended for all users

### 3.3 Role-Based Access Control (RBAC)
- **Admin:** Full system access, user management, settings
- **Manager:** Lease management, reporting, team oversight
- **Auditor:** Read-only access, commenting, audit trail review
- **Viewer:** Read-only access to assigned leases only
- **Broker:** Limited access, no financial data visibility

---

## 4. DATA SECURITY

### 4.1 Encryption Standards
- **In Transit:** TLS 1.3 minimum for all network communications
- **At Rest:** AES-256 encryption for all databases and file storage
- **Key Management:** Keys stored in AWS KMS or Supabase Vault, rotated annually

### 4.2 Data Handling
- **Storage:** All customer data stored in SOC 2 Type II compliant data centers (Supabase/AWS)
- **Backups:** Daily automated backups, 30-day retention, encrypted, tested monthly
- **Deletion:** Secure deletion within 30 days of customer termination request

### 4.3 Data Loss Prevention (DLP)
- No download of Restricted data to unencrypted devices
- Email security: SPF, DKIM, DMARC configured
- No storage of Restricted data in public cloud storage (Dropbox, Google Drive)

---

## 5. NETWORK & INFRASTRUCTURE SECURITY

### 5.1 Network Controls
- Firewall enabled on all systems
- VPN required for remote access to internal systems
- Network segmentation: production, development, and admin networks separated

### 5.2 Cloud Security
- Infrastructure-as-Code (IaC) for all cloud resources
- Least privilege IAM policies
- Regular security group audits
- Automated vulnerability scanning

### 5.3 Endpoint Security
- Antivirus/EDR required on all devices
- Full-disk encryption required
- Automatic security updates enabled
- Screen lock after 5 minutes idle

---

## 6. APPLICATION SECURITY

### 6.1 Secure Development Lifecycle (SDLC)
- Security requirements defined during design phase
- Code review required before merge to production
- Static application security testing (SAST) via Bandit
- Dependency vulnerability scanning (Dependabot/Snyk)

### 6.2 Vulnerability Management
- Security patches applied within 30 days (critical), 90 days (high)
- Annual penetration testing by third-party firm
- Bug bounty program (post-SOC 2 certification)

### 6.3 API Security
- OAuth 2.0 for authentication
- Rate limiting: 1000 requests/hour per user
- Input validation and sanitization
- OWASP Top 10 mitigation

---

## 7. AUDIT LOGGING & MONITORING

### 7.1 Audit Requirements
All Restricted data access and modifications are logged with:
- User ID and email
- Timestamp (UTC)
- Action performed
- Resource accessed
- IP address and user agent
- Before and after states (for updates/deletes)

### 7.2 Log Retention
- Audit logs: 1 year active, 7 years archive
- Security events: 1 year
- Application logs: 90 days

### 7.3 Monitoring
- Real-time alerts for: failed logins (>3 in 5 min), privilege escalation, bulk data export
- Daily review of security events
- Quarterly audit log review

---

## 8. INCIDENT RESPONSE

### 8.1 Security Incident Definition
- Unauthorized access to Restricted data
- Data breach or leak
- Malware/ransomware infection
- DDoS attack
- Insider threat

### 8.2 Incident Response Process
1. **Detect & Report:** Anyone can report via security@leaseai.com
2. **Assess:** Security team assesses severity within 1 hour
3. **Contain:** Isolate affected systems within 4 hours
4. **Investigate:** Root cause analysis within 24 hours
5. **Remediate:** Fix vulnerability within 7 days
6. **Notify:** Customers notified within 72 hours if their data affected
7. **Document:** Incident report completed within 14 days

### 8.3 Incident Severity Levels
- **Critical:** Data breach, ransomware, customer data exposed
- **High:** Unauthorized admin access, production system compromise
- **Medium:** Failed security control, suspicious activity
- **Low:** Policy violation, phishing attempt (unsuccessful)

---

## 9. THIRD-PARTY & VENDOR MANAGEMENT

### 9.1 Vendor Risk Assessment
All vendors with access to Restricted data must:
- Complete security questionnaire
- Provide SOC 2 Type II report (or equivalent)
- Sign Data Processing Agreement (DPA)
- Undergo annual security review

### 9.2 Current Approved Vendors
- **Supabase:** Database and authentication (SOC 2 Type II)
- **OpenAI:** AI model inference (data not stored beyond processing)
- **Streamlit Cloud:** Application hosting (SOC 2 Type II)
- **AWS:** Cloud infrastructure (if applicable, SOC 2 Type II)

---

## 10. BUSINESS CONTINUITY & DISASTER RECOVERY

### 10.1 Backup Policy
- **Frequency:** Daily full backups, hourly incremental
- **Retention:** 30 days point-in-time recovery
- **Testing:** Monthly restore test (random sample)
- **Offsite:** Backups stored in separate geographic region

### 10.2 Recovery Objectives
- **RTO (Recovery Time Objective):** 4 hours
- **RPO (Recovery Point Objective):** 1 hour (max data loss)

### 10.3 Disaster Recovery Plan
- Documented DR runbook
- Annual DR drill
- Failover to backup data center (if multi-region deployment)

---

## 11. COMPLIANCE & LEGAL

### 11.1 Regulatory Compliance
LeaseAI complies with:
- **GDPR:** For EU customers (data processing, right to deletion, etc.)
- **CCPA:** For California residents
- **SOC 2 Type II:** In progress, target certification Q2 2027
- **PIPEDA:** For Canadian customers (if applicable)

### 11.2 Data Privacy
- Privacy Policy published and linked in application
- Customer consent obtained before data collection
- Data Subject Access Requests (DSAR) fulfilled within 30 days

---

## 12. EMPLOYEE RESPONSIBILITIES

### 12.1 Security Awareness Training
- All employees complete security training within 30 days of hire
- Annual refresher training
- Phishing simulation quarterly

### 12.2 Acceptable Use Policy
- Company devices for business use only
- No sharing of credentials
- No installation of unauthorized software
- Report security incidents immediately

### 12.3 Bring Your Own Device (BYOD)
- MDM (Mobile Device Management) enrollment required
- Passcode/biometric lock required
- Company data wiped upon termination

---

## 13. POLICY ENFORCEMENT

### 13.1 Violations
Policy violations result in:
- First offense: Written warning
- Second offense: Suspension
- Third offense or critical violation: Termination

### 13.2 Exceptions
- All policy exceptions require written approval from CISO/Founder
- Exceptions documented and reviewed quarterly

---

## 14. POLICY REVIEW & UPDATES

This policy is reviewed and updated:
- Annually (October)
- After any security incident
- When regulatory requirements change
- When business operations significantly change

---

## 15. APPROVAL & ACKNOWLEDGMENT

**Policy Owner:** [Founder Name], Chief Executive Officer

**Approval Date:** October 21, 2026

**Next Review Date:** October 21, 2027

---

### Employee Acknowledgment
I acknowledge that I have read, understood, and agree to comply with this Information Security Policy.

Employee Name: ____________________________

Employee Signature: ________________________

Date: _____________________________________

---

**For questions or to report a security concern:**  
Email: security@leaseai.com  
Phone: [Security Hotline]

---

*This document is marked CONFIDENTIAL and is for internal use only.*
