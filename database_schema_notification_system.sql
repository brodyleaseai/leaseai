-- LeaseAI - Notification Log Schema
-- Phase 6: Agentic AI Layer - Session 2
-- 
-- Database schema for tracking email notifications sent by the automated monitoring system

-- Notification Log Table
-- Tracks all notifications sent (weekly reports, critical alerts, deadline reminders)
CREATE TABLE IF NOT EXISTS notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL CHECK (notification_type IN ('WEEKLY_REPORT', 'CRITICAL_ALERT', 'DEADLINE_REMINDER', 'CAM_AUDIT', 'CUSTOM')),
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    related_id UUID,  -- ID of related report, anomaly, or lease
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'SENT' CHECK (status IN ('SENT', 'FAILED', 'BOUNCED', 'OPENED', 'CLICKED')),
    error_message TEXT,
    metadata JSONB,  -- Additional context (e.g., email open/click tracking, delivery stats)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_notification_log_client ON notification_log(client_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_type ON notification_log(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_log_recipient ON notification_log(recipient_email);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_log_related ON notification_log(related_id);

-- Row-Level Security
ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own notifications
CREATE POLICY notification_log_select_policy ON notification_log
    FOR SELECT
    USING (auth.role() = 'authenticated' AND client_id = auth.uid());

-- Policy: Service role can insert notifications
CREATE POLICY notification_log_insert_policy ON notification_log
    FOR INSERT
    WITH CHECK (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- Policy: Service role can update notifications (e.g., status changes)
CREATE POLICY notification_log_update_policy ON notification_log
    FOR UPDATE
    USING (auth.role() = 'service_role');

-- Client Notification Preferences Table
-- Stores per-client email notification preferences
CREATE TABLE IF NOT EXISTS client_notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    email_address VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    
    -- Notification toggles
    weekly_health_reports BOOLEAN DEFAULT TRUE,
    critical_anomaly_alerts BOOLEAN DEFAULT TRUE,
    deadline_reminders BOOLEAN DEFAULT TRUE,
    cam_audit_alerts BOOLEAN DEFAULT TRUE,
    
    -- Reminder thresholds (days before deadline)
    deadline_reminder_days INTEGER[] DEFAULT ARRAY[7, 14, 30],
    
    -- Digest settings
    digest_frequency VARCHAR(20) DEFAULT 'WEEKLY' CHECK (digest_frequency IN ('DAILY', 'WEEKLY', 'MONTHLY', 'NEVER')),
    digest_day_of_week INTEGER DEFAULT 1 CHECK (digest_day_of_week BETWEEN 0 AND 6),  -- 0=Sunday, 1=Monday
    digest_time_of_day TIME DEFAULT '09:00:00',
    
    -- Timezone
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_client_notification_prefs ON client_notification_preferences(client_id);

-- Row-Level Security
ALTER TABLE client_notification_preferences ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view and edit their own preferences
CREATE POLICY client_notification_prefs_policy ON client_notification_preferences
    FOR ALL
    USING (auth.role() = 'authenticated' AND client_id = auth.uid());

-- Email Delivery Queue Table (optional - for production scale)
-- Queues emails for batch sending to improve performance and reliability
CREATE TABLE IF NOT EXISTS email_delivery_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    subject TEXT NOT NULL,
    html_body TEXT NOT NULL,
    attachments JSONB,  -- Array of {filename, path, content_type}
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),  -- 1=highest, 10=lowest
    scheduled_send_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENDING', 'SENT', 'FAILED', 'CANCELLED')),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_delivery_queue(status);
CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled ON email_delivery_queue(scheduled_send_at);
CREATE INDEX IF NOT EXISTS idx_email_queue_priority ON email_delivery_queue(priority);

-- Row-Level Security
ALTER TABLE email_delivery_queue ENABLE ROW LEVEL SECURITY;

-- Policy: Service role only (email queue is internal)
CREATE POLICY email_queue_service_policy ON email_delivery_queue
    FOR ALL
    USING (auth.role() = 'service_role');

-- Helper function to clean up old notifications (called by monthly cleanup job)
CREATE OR REPLACE FUNCTION cleanup_old_notifications(retention_days INTEGER DEFAULT 180)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM notification_log
    WHERE sent_at < NOW() - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to get notification statistics
CREATE OR REPLACE FUNCTION get_notification_stats(
    p_client_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    notification_type VARCHAR,
    total_sent BIGINT,
    avg_per_day NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.notification_type,
        COUNT(*) as total_sent,
        ROUND(COUNT(*)::NUMERIC / p_days, 2) as avg_per_day
    FROM notification_log n
    WHERE n.client_id = p_client_id
        AND n.sent_at >= NOW() - INTERVAL '1 day' * p_days
        AND n.status = 'SENT'
    GROUP BY n.notification_type
    ORDER BY total_sent DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Comments
COMMENT ON TABLE notification_log IS 'Tracks all email notifications sent to clients (health reports, alerts, reminders)';
COMMENT ON TABLE client_notification_preferences IS 'Per-client email notification preferences and settings';
COMMENT ON TABLE email_delivery_queue IS 'Queue for batch email sending (production scale)';

COMMENT ON COLUMN notification_log.notification_type IS 'Type of notification: WEEKLY_REPORT, CRITICAL_ALERT, DEADLINE_REMINDER, etc.';
COMMENT ON COLUMN notification_log.related_id IS 'UUID of related entity (health report, anomaly, lease)';
COMMENT ON COLUMN notification_log.status IS 'Delivery status: SENT, FAILED, BOUNCED, OPENED, CLICKED';

COMMENT ON COLUMN client_notification_preferences.deadline_reminder_days IS 'Array of days before deadline to send reminders (e.g., [7, 14, 30])';
COMMENT ON COLUMN client_notification_preferences.digest_frequency IS 'How often to send digest emails: DAILY, WEEKLY, MONTHLY, NEVER';
COMMENT ON COLUMN client_notification_preferences.digest_day_of_week IS '0=Sunday, 1=Monday, etc. for weekly digests';
