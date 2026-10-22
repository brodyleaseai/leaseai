-- Phase 8: query indexes and application logs
-- Run in Supabase SQL Editor

CREATE INDEX IF NOT EXISTS idx_leases_client_id ON leases(client_id);
CREATE INDEX IF NOT EXISTS idx_leases_status ON leases(status);
CREATE INDEX IF NOT EXISTS idx_leases_created_at ON leases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leases_client_status ON leases(client_id, status);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leases' AND column_name = 'uploaded_by'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_leases_uploaded_by ON leases(uploaded_by);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_extracted_fields_lease_id ON extracted_fields(lease_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'critical_dates') THEN
        CREATE INDEX IF NOT EXISTS idx_critical_dates_date_value ON critical_dates(date_value);
        CREATE INDEX IF NOT EXISTS idx_critical_dates_lease_id ON critical_dates(lease_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS application_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    message TEXT,
    user_id TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_application_logs_created ON application_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_application_logs_type ON application_logs(event_type);

CREATE TABLE IF NOT EXISTS extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID,
    filename TEXT,
    status TEXT DEFAULT 'QUEUED',
    error_message TEXT,
    lease_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON extraction_jobs(status);

GRANT SELECT, INSERT ON application_logs TO service_role, authenticated;
GRANT SELECT, INSERT, UPDATE ON extraction_jobs TO service_role, authenticated;

DO $$
BEGIN
    RAISE NOTICE 'Phase 8 performance schema applied.';
END $$;
