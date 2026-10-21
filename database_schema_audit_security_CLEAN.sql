-- LeaseAI - Audit Logging & Security Schema (CLEAN INSTALL)
-- Phase 5: Security Hardening & Enterprise Readiness
-- 
-- This script drops existing tables and creates them fresh

-- ============================================================================
-- DROP EXISTING TABLES (IF ANY)
-- ============================================================================

DROP TABLE IF EXISTS backup_verifications CASCADE;
DROP TABLE IF EXISTS security_events CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;

-- Drop functions if they exist
DROP FUNCTION IF EXISTS archive_old_audit_logs(INTEGER);
DROP FUNCTION IF EXISTS get_user_audit_summary(UUID, INTEGER);
DROP FUNCTION IF EXISTS get_resource_audit_history(VARCHAR, UUID, INTEGER);
DROP FUNCTION IF EXISTS get_security_event_stats(INTEGER);

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Who performed the action
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    
    -- What action was performed
    action_type VARCHAR(100) NOT NULL,
    action_category VARCHAR(50) NOT NULL CHECK (action_category IN ('AUTH', 'DATA', 'ADMIN', 'EXPORT', 'SECURITY')),
    
    -- What resource was affected
    resource_type VARCHAR(100),
    resource_id UUID,
    resource_name TEXT,
    
    -- Action details
    action_description TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    session_id TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'SUCCESS' CHECK (status IN ('SUCCESS', 'FAILED', 'PARTIAL')),
    error_message TEXT,
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action_type ON audit_log(action_type);
CREATE INDEX idx_audit_log_action_category ON audit_log(action_category);
CREATE INDEX idx_audit_log_resource_type ON audit_log(resource_type);
CREATE INDEX idx_audit_log_resource_id ON audit_log(resource_id);
CREATE INDEX idx_audit_log_performed_at ON audit_log(performed_at DESC);
CREATE INDEX idx_audit_log_status ON audit_log(status);
CREATE INDEX idx_audit_log_user_action_date ON audit_log(user_id, action_type, performed_at DESC);

-- Row-Level Security
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY audit_log_select_own ON audit_log
    FOR SELECT
    USING (auth.uid() = user_id OR auth.role() = 'service_role');

CREATE POLICY audit_log_insert_policy ON audit_log
    FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- SECURITY EVENTS TABLE
-- ============================================================================

CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    
    -- User context
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    
    -- Event details
    description TEXT NOT NULL,
    details JSONB,
    
    -- Network context
    ip_address INET,
    user_agent TEXT,
    country_code VARCHAR(2),
    
    -- Status
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES auth.users(id),
    resolution_notes TEXT,
    
    -- Timestamps
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_security_events_event_type ON security_events(event_type);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_user_id ON security_events(user_id);
CREATE INDEX idx_security_events_occurred_at ON security_events(occurred_at DESC);
CREATE INDEX idx_security_events_resolved ON security_events(resolved);

-- Row-Level Security
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY security_events_select_policy ON security_events
    FOR SELECT
    USING (auth.role() = 'service_role');

CREATE POLICY security_events_insert_policy ON security_events
    FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY security_events_update_policy ON security_events
    FOR UPDATE
    USING (auth.role() = 'service_role');

-- ============================================================================
-- BACKUP VERIFICATION TABLE
-- ============================================================================

CREATE TABLE backup_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    backup_date DATE NOT NULL,
    verification_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    backup_type VARCHAR(50) NOT NULL CHECK (backup_type IN ('FULL', 'INCREMENTAL', 'PITR')),
    
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'PARTIAL')),
    
    -- Test details
    test_description TEXT,
    records_restored INTEGER,
    restore_time_seconds INTEGER,
    
    -- Issues
    issues_found TEXT[],
    
    -- Metadata
    verified_by UUID REFERENCES auth.users(id),
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_backup_verifications_date ON backup_verifications(verification_date DESC);
CREATE INDEX idx_backup_verifications_status ON backup_verifications(status);

-- Row-Level Security
ALTER TABLE backup_verifications ENABLE ROW LEVEL SECURITY;

-- Policy
CREATE POLICY backup_verifications_policy ON backup_verifications
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to archive old audit logs
CREATE OR REPLACE FUNCTION archive_old_audit_logs(retention_days INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO archived_count
    FROM audit_log
    WHERE performed_at < NOW() - INTERVAL '1 day' * retention_days;
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get audit summary for a user
CREATE OR REPLACE FUNCTION get_user_audit_summary(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    action_category VARCHAR,
    action_count BIGINT,
    last_action TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.action_category,
        COUNT(*) as action_count,
        MAX(a.performed_at) as last_action
    FROM audit_log a
    WHERE a.user_id = p_user_id
        AND a.performed_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY a.action_category
    ORDER BY action_count DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get audit history for a resource
CREATE OR REPLACE FUNCTION get_resource_audit_history(
    p_resource_type VARCHAR,
    p_resource_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    performed_at TIMESTAMP WITH TIME ZONE,
    action_type VARCHAR,
    user_email VARCHAR,
    action_description TEXT,
    old_values JSONB,
    new_values JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.performed_at,
        a.action_type,
        a.user_email,
        a.action_description,
        a.old_values,
        a.new_values
    FROM audit_log a
    WHERE a.resource_type = p_resource_type
        AND a.resource_id = p_resource_id
    ORDER BY a.performed_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get security event statistics
CREATE OR REPLACE FUNCTION get_security_event_stats(
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    event_type VARCHAR,
    severity VARCHAR,
    event_count BIGINT,
    unresolved_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.event_type,
        s.severity,
        COUNT(*) as event_count,
        COUNT(*) FILTER (WHERE s.resolved = FALSE) as unresolved_count
    FROM security_events s
    WHERE s.occurred_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY s.event_type, s.severity
    ORDER BY unresolved_count DESC, event_count DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE audit_log IS 'Comprehensive audit trail of all sensitive actions in the system';
COMMENT ON TABLE security_events IS 'Security-specific events requiring monitoring or investigation';
COMMENT ON TABLE backup_verifications IS 'Track and verify database backup restore tests';

COMMENT ON COLUMN audit_log.action_type IS 'Specific action taken (e.g., LEASE_UPLOAD, DATA_EXPORT)';
COMMENT ON COLUMN audit_log.action_category IS 'High-level category: AUTH, DATA, ADMIN, EXPORT, SECURITY';
COMMENT ON COLUMN audit_log.old_values IS 'Previous state before the action (for updates/deletes)';
COMMENT ON COLUMN audit_log.new_values IS 'New state after the action (for creates/updates)';

COMMENT ON COLUMN security_events.severity IS 'Event severity: LOW, MEDIUM, HIGH, CRITICAL';
COMMENT ON COLUMN security_events.resolved IS 'Whether the security event has been investigated and resolved';
