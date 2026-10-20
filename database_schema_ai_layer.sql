-- ============================================================================
-- PHASE 6: AGENTIC AI LAYER - DATABASE SCHEMA
-- Portfolio Health Reports, Anomaly Detection, and Proactive Alerts
-- ============================================================================

-- ============================================================================
-- TABLE 1: PORTFOLIO HEALTH REPORTS
-- Auto-generated weekly reports with insights and recommendations
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.portfolio_health_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    
    -- Report Metadata
    report_date DATE NOT NULL,
    report_week INTEGER, -- Week number of year (1-52)
    report_year INTEGER,
    
    -- Executive Summary (GPT-4o generated)
    executive_summary TEXT,
    
    -- Portfolio Metrics
    total_leases INTEGER,
    active_leases INTEGER,
    expiring_soon INTEGER, -- Next 90 days
    requires_attention INTEGER, -- Low confidence, missing data
    
    -- Financial Metrics
    total_monthly_rent NUMERIC(12,2),
    avg_rent_per_sqft NUMERIC(8,2),
    total_portfolio_sqft INTEGER,
    
    -- Critical Dates Summary
    critical_dates_30_days INTEGER,
    critical_dates_60_days INTEGER,
    critical_dates_90_days INTEGER,
    
    -- Anomalies Detected
    anomalies_detected INTEGER,
    high_severity_anomalies INTEGER,
    
    -- Recommended Actions (JSON array of action items)
    recommended_actions JSONB,
    
    -- Health Score (0-100)
    health_score INTEGER,
    health_status VARCHAR(20), -- EXCELLENT, GOOD, NEEDS_ATTENTION, CRITICAL
    
    -- Report Status
    status VARCHAR(50) DEFAULT 'GENERATED',
    -- Status: GENERATED, SENT, VIEWED, ARCHIVED
    
    -- Email Delivery
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    
    -- Metadata
    generated_by VARCHAR(50) DEFAULT 'AI_AGENT',
    generated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_client_report_date UNIQUE(client_id, report_date)
);

-- ============================================================================
-- TABLE 2: LEASE ANOMALIES
-- Detected issues requiring attention
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.lease_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID REFERENCES public.leases(id) ON DELETE CASCADE,
    
    -- Anomaly Details
    anomaly_type VARCHAR(50) NOT NULL,
    -- Types: RENT_ESCALATION_MISMATCH, CRITICAL_DATE_APPROACHING, 
    --        LOW_CONFIDENCE_FIELDS, EXPIRED_LEASE_ACTIVE, MISSING_DATA,
    --        CAM_OVERCHARGE, ASC842_NONCOMPLIANT, DOCUMENT_MISSING
    
    severity VARCHAR(20) NOT NULL,
    -- Severity: LOW, MEDIUM, HIGH, CRITICAL
    
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Specific Data
    field_name VARCHAR(100), -- If related to specific field
    expected_value TEXT,
    actual_value TEXT,
    variance_amount NUMERIC(12,2), -- For financial anomalies
    
    -- Dates
    reference_date DATE, -- Date anomaly relates to (e.g., deadline date)
    days_until_deadline INTEGER, -- If time-sensitive
    
    -- Status
    status VARCHAR(50) DEFAULT 'OPEN',
    -- Status: OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, DISMISSED
    
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    resolved_by UUID,
    
    -- Alert Status
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_sent_at TIMESTAMP,
    
    -- Metadata
    detected_at TIMESTAMP DEFAULT NOW(),
    detected_by VARCHAR(50) DEFAULT 'AI_AGENT',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLE 3: PORTFOLIO ALERTS
-- Real-time alerts for immediate action
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.portfolio_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    lease_id UUID REFERENCES public.leases(id) ON DELETE SET NULL,
    anomaly_id UUID REFERENCES public.lease_anomalies(id) ON DELETE SET NULL,
    
    -- Alert Details
    alert_type VARCHAR(50) NOT NULL,
    -- Types: DEADLINE_APPROACHING, ANOMALY_DETECTED, HEALTH_REPORT_READY,
    --        COMPLIANCE_ISSUE, DOCUMENT_EXPIRING, PAYMENT_DUE
    
    severity VARCHAR(20) NOT NULL,
    priority INTEGER DEFAULT 3, -- 1 (highest) to 5 (lowest)
    
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Actions
    action_url TEXT, -- Deep link to relevant page
    action_label VARCHAR(100), -- e.g., "Review Lease", "Update Field"
    
    -- Status
    status VARCHAR(50) DEFAULT 'ACTIVE',
    -- Status: ACTIVE, READ, ACKNOWLEDGED, DISMISSED, EXPIRED
    
    read_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    dismissed_at TIMESTAMP,
    
    -- Notification Channels
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    sms_sent BOOLEAN DEFAULT FALSE,
    sms_sent_at TIMESTAMP,
    
    -- Expiration
    expires_at TIMESTAMP, -- Auto-dismiss after this date
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLE 4: ANOMALY DETECTION RULES
-- Configurable rules for what triggers anomalies
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.anomaly_detection_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    
    -- Rule Configuration
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    
    -- Thresholds
    threshold_value NUMERIC(12,2),
    threshold_percentage NUMERIC(5,2),
    threshold_days INTEGER,
    
    -- Severity Mapping
    severity_low NUMERIC(12,2),
    severity_medium NUMERIC(12,2),
    severity_high NUMERIC(12,2),
    severity_critical NUMERIC(12,2),
    
    -- Alert Configuration
    send_email BOOLEAN DEFAULT TRUE,
    send_sms BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_client_rule UNIQUE(client_id, rule_name)
);

-- ============================================================================
-- TABLE 5: HEALTH REPORT ACTIONS
-- Track recommended actions from health reports
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.health_report_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    health_report_id UUID REFERENCES public.portfolio_health_reports(id) ON DELETE CASCADE,
    lease_id UUID REFERENCES public.leases(id) ON DELETE SET NULL,
    
    -- Action Details
    action_type VARCHAR(50) NOT NULL,
    -- Types: REVIEW_LEASE, UPDATE_FIELD, RENEW_LEASE, UPLOAD_DOCUMENT,
    --        REVIEW_CAM, RUN_ASC842, CONTACT_LANDLORD
    
    priority INTEGER DEFAULT 3, -- 1 (highest) to 5 (lowest)
    
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'PENDING',
    -- Status: PENDING, IN_PROGRESS, COMPLETED, SKIPPED
    
    completed_at TIMESTAMP,
    completed_by UUID,
    completion_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Portfolio Health Reports
CREATE INDEX IF NOT EXISTS idx_health_reports_client_date ON public.portfolio_health_reports(client_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_health_reports_status ON public.portfolio_health_reports(status);

-- Lease Anomalies
CREATE INDEX IF NOT EXISTS idx_anomalies_lease_id ON public.lease_anomalies(lease_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_type_severity ON public.lease_anomalies(anomaly_type, severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_status ON public.lease_anomalies(status);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON public.lease_anomalies(detected_at DESC);

-- Portfolio Alerts
CREATE INDEX IF NOT EXISTS idx_alerts_client_id ON public.portfolio_alerts(client_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.portfolio_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON public.portfolio_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON public.portfolio_alerts(created_at DESC);

-- Anomaly Detection Rules
CREATE INDEX IF NOT EXISTS idx_detection_rules_client ON public.anomaly_detection_rules(client_id);
CREATE INDEX IF NOT EXISTS idx_detection_rules_enabled ON public.anomaly_detection_rules(enabled);

-- Health Report Actions
CREATE INDEX IF NOT EXISTS idx_report_actions_health_report ON public.health_report_actions(health_report_id);
CREATE INDEX IF NOT EXISTS idx_report_actions_status ON public.health_report_actions(status);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT ALL ON public.portfolio_health_reports TO authenticated, service_role;
GRANT ALL ON public.lease_anomalies TO authenticated, service_role;
GRANT ALL ON public.portfolio_alerts TO authenticated, service_role;
GRANT ALL ON public.anomaly_detection_rules TO authenticated, service_role;
GRANT ALL ON public.health_report_actions TO authenticated, service_role;

-- ============================================================================
-- DEFAULT ANOMALY DETECTION RULES (INSERT AFTER CLIENT CREATION)
-- ============================================================================

-- Example default rules (to be inserted via application logic):
/*
INSERT INTO anomaly_detection_rules (client_id, rule_name, rule_type, threshold_days, send_email) VALUES
  (client_id, 'Critical Date Warning - 30 Days', 'CRITICAL_DATE_APPROACHING', 30, true),
  (client_id, 'Critical Date Warning - 60 Days', 'CRITICAL_DATE_APPROACHING', 60, true),
  (client_id, 'Expired Lease Check', 'EXPIRED_LEASE_ACTIVE', 0, true),
  (client_id, 'Low Confidence Fields', 'LOW_CONFIDENCE_FIELDS', NULL, true),
  (client_id, 'Rent Escalation Variance', 'RENT_ESCALATION_MISMATCH', NULL, true);
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check all AI layer tables exist
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN (
    'portfolio_health_reports',
    'lease_anomalies',
    'portfolio_alerts',
    'anomaly_detection_rules',
    'health_report_actions'
  )
ORDER BY tablename;

-- ============================================================================
-- NOTES
-- ============================================================================

-- This schema supports:
-- 1. Weekly automated health reports with AI-generated insights
-- 2. Real-time anomaly detection across portfolio
-- 3. Proactive alerts with configurable rules
-- 4. Action item tracking and completion
-- 5. Historical trend analysis
-- 6. Multi-tenant support (client_id in all tables)

-- Future enhancements:
-- - Machine learning model tracking (predictions, confidence scores)
-- - Custom alert channels (Slack, Teams, webhook)
-- - Report templates and customization
-- - Anomaly pattern recognition
-- - Predictive analytics tables
