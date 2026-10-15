# LeaseAI — Prioritized Task Roadmap to MVP Completion
**Prepared:** October 15, 2026  
**Based On:** Founder's Brief & Business Plan (September 2026)  
**Current Status:** ~65-70% complete (Phase 2 equivalent)  
**Target:** Production-ready MVP with Growth tier sellable

---

## Roadmap Overview

This roadmap organizes remaining work into **6 phases** based on:
1. **Revenue Impact** — features that unlock higher ACV contracts
2. **Competitive Moats** — defensible IP and differentiation
3. **Dependencies** — technical blockers for other features
4. **Go-to-Market Readiness** — sales enablement and operational requirements

**Estimated Total Timeline:** 10-14 weeks (2.5-3.5 months)  
**Critical Path:** Amendment Pipeline → Yardi/MRI Integration → CAM Reconciliation → SOC 2 Prep

---

## Phase 1: Core Revenue Enablers (Weeks 1-4) 🔥 CRITICAL

**Goal:** Unlock Growth tier ($72K ACV) and make Amendment Resolution Graph™ operational

### Priority 1A: Complete Amendment Resolution Graph™ Pipeline
**Impact:** Activates $5.6M IP asset; enables competitive differentiation  
**Effort:** 2-3 weeks  
**Owner:** Backend engineer + AI specialist

**Tasks:**
- [ ] **1.1** Build amendment document processor (`amendment_processor.py` enhancement)
  - Parse amendment PDFs using existing OCR pipeline
  - Extract amendment metadata (number, date, effective date)
  - Identify which base lease it amends
  
- [ ] **1.2** Create amendment clause extraction pipeline
  - Prompt engineering for GPT-4o to identify modified clauses
  - Extract: clause type, section, modification type (MODIFIES/SUPERSEDES/ADDS/DELETES)
  - Extract original value vs. new value
  - Confidence scoring for each clause change
  
- [ ] **1.3** Wire amendment upload UI to processing pipeline
  - Connect `pages/3_🔗_Amendment_Graph.py` upload tab to backend
  - Store amendment PDF in Supabase storage
  - Trigger automated extraction on upload
  - Populate `amendments` and `amendment_clauses` tables
  
- [ ] **1.4** Build clause history materialization
  - On amendment approval, update `lease_clause_history` table
  - Calculate `effective_from` and `effective_to` dates
  - Mark previous version as `is_current = FALSE`
  - Mark new version as `is_current = TRUE`
  
- [ ] **1.5** Test amendment chain queries
  - Create 2-3 test leases with 3-5 amendments each
  - Verify `get_controlling_clause()` returns correct value at any date
  - Verify visual timeline renders correctly
  - Verify before/after comparisons work

**Success Criteria:**
- ✅ Can upload amendment PDF and link to base lease
- ✅ GPT-4o extracts at least 5 modified clauses per amendment
- ✅ Clause history table correctly tracks version evolution
- ✅ Query engine returns controlling value as of any date
- ✅ Visual timeline displays amendment chain
- ✅ Demo-ready: can show a lease with 3 amendments and query it

**Revenue Impact:** Unlocks $5.6M IP valuation; becomes primary sales differentiator

---

### Priority 1B: Yardi & MRI Export Integration (Phase 1)
**Impact:** Unlocks Growth tier ($72K ACV); table stakes for mid-market  
**Effort:** 2-3 weeks  
**Owner:** Backend engineer

**Tasks:**
- [ ] **1.6** Research Yardi Voyager and MRI Software data import formats
  - Obtain CSV/XML templates for lease data import
  - Identify required field mappings (LeaseAI → Yardi/MRI)
  - Document authentication requirements (if API vs. file-based)
  
- [ ] **1.7** Build Yardi CSV export module
  - Map 84 LeaseAI fields to Yardi standard fields
  - Generate properly formatted CSV per Yardi spec
  - Include validation checks for required fields
  - Add export button to Lease Review page
  
- [ ] **1.8** Build MRI CSV export module
  - Map 84 LeaseAI fields to MRI standard fields
  - Generate properly formatted CSV per MRI spec
  - Include validation checks for required fields
  - Add export button to Lease Review page
  
- [ ] **1.9** Create unified export UI
  - Single "Export Lease Data" dropdown on Lease Review page
  - Options: Yardi CSV, MRI CSV, Generic CSV, PDF (already exists)
  - Download file or email to user
  - Log all exports for audit trail
  
- [ ] **1.10** Document integration setup process
  - Write user guide: "How to Import LeaseAI Data into Yardi"
  - Write user guide: "How to Import LeaseAI Data into MRI"
  - Create video walkthrough (5-10 min screencast)
  - Add to sales collateral library

**Success Criteria:**
- ✅ Can export lease data as Yardi-formatted CSV
- ✅ Can export lease data as MRI-formatted CSV
- ✅ Exported CSV successfully imports into Yardi demo environment
- ✅ Exported CSV successfully imports into MRI demo environment
- ✅ User documentation complete and tested
- ✅ Sales can demo Yardi/MRI export in 60-second pitch

**Revenue Impact:** Unlocks Growth tier ($72K ACV); estimated 60-70% of target customers require Yardi/MRI compatibility

---

### Priority 1C: CSV & Excel Exports (Generic)
**Impact:** Completes Starter tier feature set; sales table stakes  
**Effort:** 1 week  
**Owner:** Backend engineer

**Tasks:**
- [ ] **1.11** Build generic CSV export
  - Export all 84 fields as flat CSV
  - Include confidence scores in adjacent column
  - Add metadata row (property address, tenant, lease ID)
  - Download as `LeaseAbstract_[LeaseID]_[Date].csv`
  
- [ ] **1.12** Build Excel (.xlsx) export
  - Use `openpyxl` or `xlsxwriter` library
  - Create formatted workbook with:
    - Sheet 1: Lease Summary (property, tenant, dates)
    - Sheet 2: Extracted Fields (all 84 fields)
    - Sheet 3: ASC 842 Calculations (if run)
    - Sheet 4: Critical Dates
  - Apply formatting: headers, colors, confidence indicators
  - Download as `LeaseAbstract_[LeaseID]_[Date].xlsx`
  
- [ ] **1.13** Add bulk export capability
  - Admin dashboard: "Export All Leases" button
  - Generate ZIP file with all lease CSVs or single consolidated Excel
  - Useful for portfolio-level analysis

**Success Criteria:**
- ✅ Can export single lease as CSV
- ✅ Can export single lease as formatted Excel
- ✅ Can bulk export all leases as ZIP
- ✅ Exports open correctly in Excel, Google Sheets, Numbers

**Revenue Impact:** Required for Starter tier completeness; removes sales objection

---

## Phase 2: CAM Reconciliation Module (Weeks 5-7) 💰 HIGH VALUE

**Goal:** Build the $500/month add-on that recovers overbilled CAM charges  
**Effort:** 3 weeks  
**Owner:** Backend engineer + product manager (for workflow design)

### Priority 2A: CAM Data Model & Extraction
**Tasks:**
- [ ] **2.1** Design CAM reconciliation database schema
  - New table: `cam_reconciliations` (lease_id, year, landlord_charges, calculated_charges, variance, status)
  - New table: `cam_line_items` (reconciliation_id, category, landlord_amount, calculated_amount, variance)
  - Link to `leases` table
  
- [ ] **2.2** Extract CAM provisions from leases
  - Enhance extraction prompt to capture:
    - CAM base year
    - CAM stop amount
    - CAM exclusions (specific items landlord cannot charge)
    - CAM caps (max annual increase %)
    - Pro-rata share (if not 100%)
  - Store in `extracted_fields` or new `cam_provisions` table
  
- [ ] **2.3** Build CAM upload interface
  - New page: `pages/8_💵_CAM_Reconciliation.py`
  - Upload landlord CAM statement (PDF or CSV)
  - Parse line items using GPT-4o
  - Categorize charges: utilities, maintenance, insurance, property tax, admin, etc.

**Success Criteria:**
- ✅ CAM provisions correctly extracted from lease
- ✅ Can upload landlord CAM statement (PDF)
- ✅ GPT-4o categorizes CAM line items with >85% accuracy

---

### Priority 2B: CAM Calculation & Dispute Detection
**Tasks:**
- [ ] **2.4** Build CAM calculation engine
  - Calculate tenant's pro-rata share
  - Apply CAM cap (if any)
  - Apply CAM exclusions (remove excluded items)
  - Compare landlord charges vs. calculated charges
  - Flag variances > $500 or >5%
  
- [ ] **2.5** Create CAM reconciliation report
  - PDF output: "CAM Reconciliation Report - [Property] - [Year]"
  - Summary: Total landlord charge vs. calculated charge
  - Line-by-line comparison table
  - Highlighted discrepancies
  - Recommended actions (e.g., "Challenge $2,450 janitorial overcharge")
  
- [ ] **2.6** Build dispute workflow UI
  - Mark discrepancies as: Accept / Challenge / Under Review
  - Draft dispute letter to landlord (GPT-4o generated)
  - Track dispute status and resolution
  - Calculate total savings recovered

**Success Criteria:**
- ✅ Calculates correct tenant CAM obligation per lease terms
- ✅ Identifies overbilled charges with 90%+ accuracy
- ✅ Generates professional dispute-ready PDF report
- ✅ Drafts landlord challenge letter in <30 seconds
- ✅ Demo shows $5,000+ in recovered overbilling for a mid-size property

**Revenue Impact:** $500/month add-on (per Growth tier pricing); ROI story of "$6,000/year subscription recovers $20,000 in CAM overcharges" is highly compelling

---

## Phase 3: Sales Enablement & Design Partner Prep (Weeks 5-8) 📈 MARKET READINESS

**Goal:** Create collateral to close first 5 design partners / paying customers  
**Effort:** Parallel to Phases 1-2 (non-engineering work)  
**Owner:** Founder + marketing/sales hire (if available)

### Priority 3A: Sales Collateral
**Tasks:**
- [ ] **3.1** Create Product Demo Script (60 min)
  - Act 1: The Problem (manual abstraction pain)
  - Act 2: The Solution (LeaseAI extraction demo)
  - Act 3: The Differentiation (Amendment Graph™ + ASC 842)
  - Act 4: The ROI (CAM reconciliation + time savings)
  - Include tailored versions for: CRE firms, REITs, CPA firms
  
- [ ] **3.2** Build ROI Calculator (interactive web tool)
  - Input: # of leases, manual abstraction cost, hours/lease
  - Output: Annual savings with LeaseAI
  - Embed on website or share as Excel
  - Example: "200 leases × $250/lease × 2 abstractions/year = $100K saved"
  
- [ ] **3.3** Create One-Pager (PDF sales sheet)
  - Front: Product overview, key features, pricing
  - Back: Case study (even if anonymized/hypothetical), ROI example
  - Professional design (Canva or Figma)
  
- [ ] **3.4** Create Founder Video (3-5 min)
  - Personal story: why you built LeaseAI
  - Problem statement
  - Product walkthrough (screen recording)
  - Call to action: "Book a demo"
  - Upload to YouTube/Vimeo, embed on landing page
  
- [ ] **3.5** Write LinkedIn Content Series (10 posts)
  - Post 1: "Why lease abstraction costs $250/lease"
  - Post 2: "How AI reduces lease review from 5 days to 2 hours"
  - Post 3: "What is ASC 842 and why CFOs care"
  - Post 4: "The $2B CAM reconciliation problem"
  - Post 5: "Case study: [Hypothetical] client saves $50K/year"
  - Post 6-10: Feature spotlights, behind-the-scenes, testimonials

**Success Criteria:**
- ✅ 60-min demo script tested with 3 pilot prospects
- ✅ ROI calculator shows clear savings for 50-500 lease portfolios
- ✅ One-pager is print-ready and design-approved
- ✅ Founder video uploaded and shared
- ✅ 10 LinkedIn posts scheduled (2/week for 5 weeks)

---

### Priority 3B: Design Partner Program
**Tasks:**
- [ ] **3.6** Define Design Partner Offer
  - Free access for 6 months (Starter or Growth tier)
  - 2 hours/week of product feedback sessions
  - Permission to use anonymized data for model training
  - Commitment to become paying customer at launch if satisfied
  - Testimonial / case study participation
  
- [ ] **3.7** Recruit 5-8 Design Partners
  - Target profile: CRE firms with 25-100 leases
  - Outreach via: Founder's LinkedIn network, ULI/NAIOP events, cold email
  - Personalized pitch: "Help shape the future of lease abstraction AI"
  - Goal: 5 confirmed by end of Week 8
  
- [ ] **3.8** Create Design Partner Onboarding Kit
  - Welcome email with product overview
  - Onboarding call script (45 min)
  - Training video: "How to use LeaseAI" (10-15 min)
  - Weekly feedback form (Google Form or Typeform)
  - Slack or email channel for support
  
- [ ] **3.9** Schedule Bi-Weekly Design Partner Check-ins
  - 30-min call every 2 weeks per partner
  - Agenda: feature requests, bugs, confusion points, ROI validation
  - Document feedback in product backlog

**Success Criteria:**
- ✅ 5 design partners signed and onboarded
- ✅ Each partner uploads at least 5 leases in first 2 weeks
- ✅ 90% satisfaction score in first 30 days
- ✅ At least 3 partners commit to paid conversion

**Revenue Impact:** Validates product-market fit; generates first testimonials; creates pipeline for Month 4 revenue

---

## Phase 4: Payment Integration & Billing (Weeks 7-9) 💳 REVENUE OPERATIONS

**Goal:** Enable self-serve signup and automated billing  
**Effort:** 2-3 weeks  
**Owner:** Full-stack engineer

### Priority 4A: Stripe Integration
**Tasks:**
- [ ] **4.1** Set up Stripe account
  - Create Stripe Connect account
  - Configure products: Starter ($2,500/mo), Growth ($6,000/mo), Enterprise ($15,000/mo)
  - Set up annual subscription option (16.7% discount = 2 months free)
  - Enable invoicing and receipts
  
- [ ] **4.2** Build subscription checkout flow
  - New page: `pages/9_💳_Subscribe.py`
  - Select tier (Starter / Growth / Enterprise)
  - Select billing frequency (monthly / annual)
  - Stripe Checkout redirect or embedded form
  - Capture subscription ID and link to `clients` table
  
- [ ] **4.3** Implement subscription management
  - Dashboard for clients: view current plan, usage, billing history
  - Upgrade/downgrade capability (prorate charges)
  - Cancel subscription (retain data for 30 days)
  - Payment method update
  
- [ ] **4.4** Add usage tracking & limits
  - Starter: Max 50 leases/month abstraction limit
  - Growth: Max 200 leases/month
  - Enterprise: Unlimited
  - Display usage meter in client dashboard
  - Block uploads when limit reached (or allow overage billing)
  
- [ ] **4.5** Configure webhooks & automation
  - Stripe webhook: `subscription.created` → activate account
  - Stripe webhook: `payment.succeeded` → send receipt email
  - Stripe webhook: `payment.failed` → send dunning email, suspend account after 3 failures
  - Stripe webhook: `subscription.canceled` → archive client data

**Success Criteria:**
- ✅ Can sign up for Starter tier and complete payment
- ✅ Subscription activates account immediately
- ✅ Monthly billing auto-charges on renewal
- ✅ Can upgrade from Starter to Growth mid-cycle (prorated)
- ✅ Failed payments trigger automated retry and email

**Revenue Impact:** Removes manual invoicing bottleneck; enables self-serve growth

---

### Priority 4B: Sales CRM & Pipeline Tracking (Optional)
**Tasks:**
- [ ] **4.6** Integrate HubSpot or Pipedrive (free tier)
  - Capture leads from demo requests
  - Track deal stage: Demo Scheduled → Demo Completed → Proposal Sent → Closed-Won
  - Automated email sequences for follow-up
  
- [ ] **4.7** Build internal admin metrics dashboard
  - New tab in Admin Dashboard: "Sales Metrics"
  - Metrics: MRR, ARR, churn rate, new signups this month, pipeline value
  - Chart: MRR growth over time
  - Use Supabase analytics or build custom queries

**Success Criteria:**
- ✅ All demo requests auto-create deals in CRM
- ✅ Founder can see real-time MRR and ARR
- ✅ Email sequences nurture leads automatically

---

## Phase 5: SOC 2 Preparation & Enterprise Readiness (Weeks 9-12) 🔒 TRUST & SECURITY

**Goal:** Begin SOC 2 Type I audit preparation; enable enterprise sales  
**Effort:** 4 weeks initial prep (full audit is 3-6 months)  
**Owner:** Founder + security consultant (or use Vanta/Drata)

### Priority 5A: Security Documentation
**Tasks:**
- [ ] **5.1** Create Information Security Policy
  - Document data classification (public, internal, confidential, restricted)
  - Document access controls (who can access what data)
  - Document encryption standards (TLS 1.3 in transit, AES-256 at rest)
  - Document incident response plan
  - Document vendor management policy
  - Template: Use Vanta or Drata policy library
  
- [ ] **5.2** Create Data Processing Agreement (DPA)
  - GDPR-compliant (even if primarily North America, some clients require it)
  - Document: data types collected, processing purpose, retention period, deletion process
  - Have legal review (or use Ironclad/Juro template)
  
- [ ] **5.3** Create Master Services Agreement (MSA) Template
  - Standard terms: service levels, data ownership, liability limits, termination
  - Attach DPA as Schedule A
  - Attach Order Form template as Schedule B
  - Have legal review
  
- [ ] **5.4** Document SOC 2 readiness gap analysis
  - Use Vanta or Drata free trial to scan environment
  - Identify gaps: missing 2FA, no access logs, no backup testing, etc.
  - Create remediation plan (prioritized list)

**Success Criteria:**
- ✅ Security Policy published and shared with prospects
- ✅ DPA ready to sign with enterprise customers
- ✅ MSA template reviewed by legal
- ✅ SOC 2 gap analysis complete with 12-month remediation plan

**Revenue Impact:** Unblocks enterprise sales cycles; required for deals >$100K ACV

---

### Priority 5B: Security Hardening
**Tasks:**
- [ ] **5.5** Enable 2FA for all admin users
  - Use Supabase built-in 2FA or Auth0
  - Enforce for admin role
  - Optional for client role
  
- [ ] **5.6** Implement audit logging
  - Log all sensitive actions: lease upload, data export, user role change, delete operations
  - Store logs in `audit_log` table or external service (Logtail, DataDog)
  - Display audit log in Admin Dashboard
  
- [ ] **5.7** Set up automated backups
  - Supabase: enable point-in-time recovery (PITR)
  - Schedule daily full database backups
  - Test restore procedure monthly
  - Document backup policy in Security Policy
  
- [ ] **5.8** Enable static code analysis
  - Add `bandit` (Python security linter) to CI/CD
  - Run on every commit
  - Fix critical/high vulnerabilities
  
- [ ] **5.9** Purchase cyber liability insurance
  - $1M-$2M coverage
  - Required for enterprise RFPs
  - Shop quotes: Embroker, Coalition, Corvus

**Success Criteria:**
- ✅ All admin users have 2FA enabled
- ✅ Audit log captures 100% of sensitive actions
- ✅ Backup restore tested successfully
- ✅ Zero critical security vulnerabilities in static analysis
- ✅ Cyber insurance policy in force

**Revenue Impact:** Security table stakes for enterprise sales; reduces legal liability

---

## Phase 6: Agentic AI Layer (Weeks 10-14) 🤖 DIFFERENTIATION

**Goal:** Build "persistent co-pilot" features: weekly health reports, anomaly detection  
**Effort:** 4-5 weeks  
**Owner:** AI engineer + backend engineer

### Priority 6A: Weekly Portfolio Health Report
**Tasks:**
- [ ] **6.1** Design health report structure
  - Sections:
    1. Executive Summary (3-sentence overview)
    2. Upcoming Critical Dates (next 90 days)
    3. Leases Requiring Attention (low confidence extractions, missing data)
    4. Portfolio Insights (avg rent/sqft, expiration concentration, renewal options expiring)
    5. Recommended Actions (prioritized list of 3-5 items)
  
- [ ] **6.2** Build health report generation pipeline
  - Scheduled job (every Monday 6am)
  - Query Supabase for all client leases
  - Aggregate statistics
  - Use GPT-4o to generate executive summary and recommended actions
  - Store report in `portfolio_health_reports` table
  
- [ ] **6.3** Create email delivery for health reports
  - Send to all Growth/Enterprise clients every Monday
  - HTML email with key insights
  - Attach PDF report
  - Link to dashboard to take action
  
- [ ] **6.4** Build health report dashboard
  - New page: `pages/10_🏥_Portfolio_Health.py`
  - Display current week's report
  - Historical reports archive
  - Interactive charts: lease expiration timeline, rent roll summary

**Success Criteria:**
- ✅ Generates accurate health report for 50-lease portfolio
- ✅ Email delivered every Monday at 6am
- ✅ Clients can view historical reports
- ✅ Recommended actions are actionable (not generic)

**Revenue Impact:** Key differentiator for Growth/Enterprise tiers; drives stickiness and NRR

---

### Priority 6B: Anomaly Detection
**Tasks:**
- [ ] **6.5** Build rent escalation tracker
  - On lease upload, extract rent schedule and escalation terms
  - Calculate expected rent at any date
  - Compare to actual invoiced rent (if available)
  - Flag discrepancies: "Expected $5,200/month but invoiced $5,500"
  
- [ ] **6.6** Build critical date anomaly alerts
  - Check if renewal notice deadline is <30 days away and no action recorded
  - Alert: "⚠️ Renewal notice deadline in 25 days — no action taken"
  - Check if lease expired but still marked as active
  - Alert: "⚠️ Lease expired 45 days ago but status still ACTIVE"
  
- [ ] **6.7** Build confidence score anomaly detection
  - Flag leases with >10 fields marked "LOW" or "NOT FOUND"
  - Alert: "⚠️ Lease has 15 low-confidence fields — recommend manual review"
  
- [ ] **6.8** Integrate anomaly alerts into health report
  - Add "Anomalies Detected This Week" section to health report
  - Display in dashboard with red/yellow/green indicators

**Success Criteria:**
- ✅ Correctly detects rent escalation discrepancies
- ✅ Flags upcoming critical dates 30 days in advance
- ✅ Identifies incomplete/low-quality lease abstracts
- ✅ Anomalies integrated into weekly health report

**Revenue Impact:** Demonstrates proactive value; "system caught $10K rent overcharge" is a powerful retention story

---

## Phase 7: Native API Integrations (Weeks 12-16) 🔌 ENTERPRISE MOAT

**Goal:** Build native Yardi and MRI API connectors (not just CSV export)  
**Effort:** 4-5 weeks  
**Owner:** Backend engineer with API integration experience

**Note:** This is Phase 4 from the Founder's Brief (Months 7-8). Deprioritized to Phase 7 here because CSV exports (Phase 1B) provide 80% of the value with 20% of the effort.

### Priority 7A: Yardi Voyager API Integration
**Tasks:**
- [ ] **7.1** Obtain Yardi API credentials
  - Contact Yardi partner support
  - Apply for API access (may require client reference)
  - Review Yardi API documentation
  
- [ ] **7.2** Build Yardi OAuth connector
  - Implement OAuth 2.0 authentication
  - Store refresh tokens securely
  - Handle token expiration and renewal
  
- [ ] **7.3** Build Yardi lease import module
  - Map LeaseAI lease object to Yardi lease object
  - POST lease data to Yardi API
  - Handle validation errors
  - Sync status: Pending / In Progress / Complete / Failed
  
- [ ] **7.4** Build Yardi tenant import module
  - Extract tenant data from LeaseAI lease
  - Check if tenant already exists in Yardi
  - Create or update tenant record
  
- [ ] **7.5** Build bi-directional sync (optional)
  - Pull existing leases from Yardi into LeaseAI
  - Compare and merge data
  - Resolve conflicts (e.g., different expiration dates)

**Success Criteria:**
- ✅ Can authenticate to Yardi API
- ✅ Can push lease data from LeaseAI to Yardi
- ✅ Lease appears correctly in Yardi UI
- ✅ Sync errors are logged and retried

---

### Priority 7B: MRI Software API Integration
**Tasks:**
- [ ] **7.6** Repeat tasks 7.1-7.5 for MRI Software
  - MRI uses different API (RESTful vs. SOAP)
  - Similar workflow: OAuth, lease object mapping, import, sync

**Success Criteria:**
- ✅ Can authenticate to MRI API
- ✅ Can push lease data from LeaseAI to MRI
- ✅ Lease appears correctly in MRI UI

**Revenue Impact:** Unlocks Enterprise tier ($180K ACV); reduces client onboarding friction from days to hours; creates high switching costs (once syncing, unlikely to churn)

---

## Phase 8: Production Deployment & Monitoring (Weeks 14-16) 🚀 LAUNCH READY

**Goal:** Deploy to production-grade infrastructure; enable monitoring  
**Effort:** 2-3 weeks  
**Owner:** DevOps engineer or founder

### Priority 8A: Infrastructure Upgrade
**Tasks:**
- [ ] **8.1** Evaluate Streamlit Cloud vs. AWS deployment
  - If staying on Streamlit Cloud:
    - Upgrade to Team plan ($42/user/month)
    - Enable custom domain (e.g., app.leaseai.co)
    - Configure environment variables securely
  - If migrating to AWS:
    - Containerize Streamlit app (Docker)
    - Deploy to AWS ECS or App Runner
    - Set up RDS PostgreSQL (or keep Supabase)
    - Set up S3 for PDF storage
    - Set up CloudFront CDN
    - Estimated cost: $200-500/month at <100 users
  
- [ ] **8.2** Configure custom domain
  - Purchase domain: leaseai.com or leaseai.co
  - Set up DNS (Cloudflare recommended)
  - Enable HTTPS with Let's Encrypt or AWS Certificate Manager
  
- [ ] **8.3** Set up monitoring & alerting
  - Application monitoring: Use Sentry (error tracking) or Streamlit built-in
  - Infrastructure monitoring: Use AWS CloudWatch or Datadog
  - Uptime monitoring: Use UptimeRobot or Pingdom
  - Alerts: Email/Slack when app is down or error rate >5%
  
- [ ] **8.4** Set up log aggregation
  - Centralize logs: Use Logtail, Papertrail, or AWS CloudWatch Logs
  - Structured logging: Log all API calls, extraction jobs, errors
  - Retention: 30 days for debugging, 1 year for audit

**Success Criteria:**
- ✅ App accessible at custom domain (e.g., app.leaseai.co)
- ✅ 99.5% uptime over 30 days
- ✅ Error alerts trigger within 5 minutes
- ✅ Can query logs for any user action

---

### Priority 8B: Performance & Scalability
**Tasks:**
- [ ] **8.5** Optimize database queries
  - Add indexes on frequently queried columns (`leases.client_id`, `leases.status`, etc.)
  - Use Supabase query analyzer to find slow queries
  - Add caching for expensive queries (e.g., lease count, portfolio stats)
  
- [ ] **8.6** Optimize AI extraction pipeline
  - Batch multiple lease extractions (if queue builds up)
  - Use async processing (Celery or Cloud Tasks)
  - Set timeout limits (max 5 min per lease)
  
- [ ] **8.7** Load test the application
  - Simulate 50 concurrent users uploading leases
  - Measure: response time, error rate, database load
  - Target: <3 sec page load, <1% error rate

**Success Criteria:**
- ✅ Can handle 50 concurrent users without degradation
- ✅ Average page load time <2 seconds
- ✅ Lease extraction completes in <3 minutes (95th percentile)

---

## Phase 9: Go-to-Market Launch (Weeks 15-20) 📣 FIRST CUSTOMERS

**Goal:** Convert design partners to paying customers; acquire 3-5 new customers  
**Effort:** Ongoing (founder-led sales)  
**Owner:** Founder

### Priority 9A: Design Partner Conversion
**Tasks:**
- [ ] **9.1** Schedule conversion calls with 5 design partners
  - Present final pricing: Starter $2,500/mo or Growth $6,000/mo
  - Offer: "Lock in your rate for 12 months" (no price increases)
  - Close 3-5 partners (60% conversion target)
  
- [ ] **9.2** Create case studies from converted partners
  - Interview: What problem did LeaseAI solve? What's the ROI?
  - Write 1-page case study per client
  - Get permission to use company name or anonymize
  
- [ ] **9.3** Request testimonials and G2/Capterra reviews
  - Ask for LinkedIn recommendation
  - Ask for G2 or Capterra review
  - Display on website and sales deck

**Success Criteria:**
- ✅ 3 design partners convert to paying customers ($7,500-$18,000 MRR)
- ✅ 2 case studies published
- ✅ 3 testimonials collected

---

### Priority 9B: Outbound Sales (Founder-Led)
**Tasks:**
- [ ] **9.4** Build target prospect list (200 contacts)
  - CRE firms with 50-200 leases in Vancouver/BC
  - LinkedIn Sales Navigator search
  - ULI, NAIOP, CoreNet Global member directories
  - Target titles: Head of Real Estate, VP Real Estate, Controller, CFO
  
- [ ] **9.5** Launch cold email campaign
  - Sequence:
    - Email 1: Problem statement + one-liner
    - Email 2 (+3 days): Case study or ROI example
    - Email 3 (+7 days): Demo offer
  - Target: 15% reply rate, 3% demo booking rate
  - Goal: 6-10 demos booked
  
- [ ] **9.6** Conduct demos and close deals
  - Run 60-min demo (from Phase 3A script)
  - Send proposal within 24 hours
  - Follow up 2x/week until close
  - Goal: 30% close rate (2-3 new customers from 6-10 demos)

**Success Criteria:**
- ✅ 200 prospects added to CRM
- ✅ 6-10 demos completed
- ✅ 2-3 new paying customers signed
- ✅ $13,500-$45,000 MRR from new customers

---

### Priority 9C: Website & Landing Page
**Tasks:**
- [ ] **9.7** Build marketing website (leaseai.com)
  - Home page: Hero, problem, solution, features, pricing, CTA
  - About page: Founder story, mission
  - Pricing page: Tier comparison table
  - Blog: Placeholder for content marketing
  - Demo request form (integrates with HubSpot/Pipedrive)
  - Use Webflow, Framer, or Next.js
  
- [ ] **9.8** SEO optimization
  - Target keywords: "lease abstraction software", "ASC 842 compliance tool", "commercial lease AI"
  - Write 3-5 blog posts targeting keywords
  - Submit to Product Hunt, BetaList, G2, Capterra

**Success Criteria:**
- ✅ Website live at leaseai.com
- ✅ Demo requests flow into CRM automatically
- ✅ Ranking on page 2-3 for target keywords within 90 days

---

## Critical Path & Dependencies

```
Phase 1A (Amendment Pipeline) → Blocks: Phase 6 (AI Layer), Phase 7 (Native Integrations)
Phase 1B (Yardi/MRI Export)   → Blocks: Phase 9 (Sales - Growth tier)
Phase 2 (CAM Reconciliation)  → Blocks: Phase 9 (Sales - add-on revenue)
Phase 4 (Payment Integration) → Blocks: Phase 9 (Sales - self-serve)
Phase 5 (SOC 2 Prep)          → Blocks: Enterprise sales (parallel track)
```

**Recommendation:** Phases 1-4 are **critical path to revenue**. Phase 5 (SOC 2) can run in parallel. Phases 6-8 can follow after first customers.

---

## Resource Requirements

| Phase | Effort (Weeks) | Team Required |
|-------|----------------|---------------|
| Phase 1 (Amendment + Yardi/MRI) | 3-4 | 1 full-stack engineer |
| Phase 2 (CAM Reconciliation) | 3 | 1 full-stack engineer |
| Phase 3 (Sales Enablement) | 4 | Founder + contractor (design/video) |
| Phase 4 (Payment Integration) | 2-3 | 1 full-stack engineer |
| Phase 5 (SOC 2 Prep) | 4 (initial) | Founder + Vanta/Drata SaaS |
| Phase 6 (AI Layer) | 4-5 | 1 AI/backend engineer |
| Phase 7 (Native Integrations) | 4-5 | 1 backend engineer |
| Phase 8 (Production Deploy) | 2-3 | DevOps engineer or founder |
| Phase 9 (GTM Launch) | Ongoing | Founder (sales) |

**Minimum Team:** 1 founder + 1 full-stack engineer (current state)  
**Optimal Team (Month 4-6):** 1 founder + 1 full-stack engineer + 1 contractor (design/video) + Vanta/Drata subscription

**Estimated Budget (Phases 1-5):**
- Engineering: $20K-$40K (if contractor at $100-150/hr) or $0 if founder does all coding
- Design/Video: $2K-$5K (contractor)
- SaaS tools: $500/month (Vanta, Stripe, HubSpot, Sentry)
- Infrastructure: $200-$500/month (AWS or Streamlit Team plan)

**Total:** $25K-$50K + 3-4 months of founder time

---

## Success Metrics by Phase

| Phase | Key Metric | Target |
|-------|------------|--------|
| Phase 1 | Amendment Graph™ demo-ready | ✅ Can show 3-amendment lease with query |
| Phase 1 | Yardi/MRI export working | ✅ CSV imports successfully into demo environment |
| Phase 2 | CAM reconciliation functional | ✅ Identifies $5K+ in overcharges in test case |
| Phase 3 | Design partners recruited | ✅ 5 partners signed |
| Phase 4 | Payment integration live | ✅ First self-serve signup completes |
| Phase 5 | SOC 2 gap analysis done | ✅ Remediation plan documented |
| Phase 6 | Health reports generating | ✅ 100% delivery rate for weekly reports |
| Phase 9 | First paying customers | ✅ 3-5 customers, $13.5K-$45K MRR |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Engineering bandwidth too low** | Hire contractor/freelancer for Phases 1-2 (critical path) |
| **Design partners don't convert** | Offer extended free trial or grandfathered discount |
| **Yardi/MRI integration blocked** | CSV exports are 80% solution; defer native API to Phase 7 |
| **SOC 2 too slow/expensive** | Use Vanta/Drata to automate; defer Type II until Series A |
| **Founder overwhelmed** | Ruthlessly prioritize Phases 1-4; defer Phases 6-8 |

---

## Recommended Execution Order (Next 16 Weeks)

**Weeks 1-4:** Phase 1 (Amendment Pipeline + Yardi/MRI CSV)  
**Weeks 5-7:** Phase 2 (CAM Reconciliation)  
**Weeks 5-8:** Phase 3 (Sales Enablement) — parallel  
**Weeks 7-9:** Phase 4 (Payment Integration)  
**Weeks 9-12:** Phase 5 (SOC 2 Prep) + Phase 6 (AI Layer) — parallel  
**Weeks 12-16:** Phase 8 (Production Deploy) + Phase 9 (GTM Launch)  
**Weeks 16+:** Phase 7 (Native Integrations) — after first customers

**End State (Week 16):**
- ✅ Amendment Resolution Graph™ fully operational
- ✅ Yardi/MRI CSV exports working
- ✅ CAM reconciliation module shipped
- ✅ Payment integration live (Stripe)
- ✅ SOC 2 prep underway (gap analysis complete)
- ✅ Weekly health reports generating
- ✅ 3-5 paying customers ($13.5K-$45K MRR)
- ✅ Production-ready infrastructure

**ARR Projection (Month 6 post-roadmap):** $162K-$540K (vs. original target $456K at Month 6)

---

## Conclusion

This roadmap **prioritizes revenue-driving features** (Amendment Pipeline, Yardi/MRI, CAM Reconciliation) while **building competitive moats** (Amendment Graph™ IP, compliance depth) and **enabling go-to-market** (sales collateral, payment integration).

**Critical Success Factor:** Execute Phases 1-4 without compromise. Phases 5-8 can be deferred or parallelized based on founder bandwidth.

**Next Steps:**
1. Review and approve roadmap with stakeholders
2. Hire contractor or engineer for Phases 1-2 (if needed)
3. Begin Phase 1A (Amendment Pipeline) immediately
4. Schedule bi-weekly roadmap check-ins to track progress

---

**Prepared By:** Cloud Agent (Cursor)  
**Next Review:** Every 2 weeks during execution
