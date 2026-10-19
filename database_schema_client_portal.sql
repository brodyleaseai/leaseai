-- Export History Tracking
-- Track when clients download reports and exports

CREATE TABLE IF NOT EXISTS export_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID REFERENCES leases(id) ON DELETE CASCADE,
    user_id UUID,  -- Removed foreign key constraint to users table
    export_type VARCHAR(50) NOT NULL, -- 'PDF_REPORT', 'YARDI_CSV', 'MRI_CSV', 'ASC842_REPORT'
    export_format VARCHAR(20), -- 'PDF', 'CSV', 'XLSX'
    file_size_bytes INTEGER,
    exported_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    
    -- For tracking what data was included
    fields_exported JSONB,
    date_range JSONB, -- {from: date, to: date} for bulk exports
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_export_history_lease_id ON export_history(lease_id);
CREATE INDEX idx_export_history_user_id ON export_history(user_id);
CREATE INDEX idx_export_history_exported_at ON export_history(exported_at DESC);
CREATE INDEX idx_export_history_type ON export_history(export_type);

-- Lease Processing Status
-- Track real-time progress of lease extraction

CREATE TABLE IF NOT EXISTS lease_processing_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID REFERENCES leases(id) ON DELETE CASCADE UNIQUE,
    
    -- Progress tracking
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED', -- QUEUED, PROCESSING, EXTRACTING, COMPLETE, FAILED
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    current_step VARCHAR(100), -- 'Uploading...', 'Running OCR...', 'Extracting fields...'
    total_steps INTEGER DEFAULT 8,
    completed_steps INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_completion_at TIMESTAMP,
    processing_duration_seconds INTEGER,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    extraction_method VARCHAR(50), -- 'GPT4', 'GPT4_WITH_OCR', 'TESSERACT_FALLBACK'
    page_count INTEGER,
    file_size_bytes INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lease_processing_lease_id ON lease_processing_status(lease_id);
CREATE INDEX idx_lease_processing_status ON lease_processing_status(status);

-- Lease Comparisons
-- Track when clients compare leases

CREATE TABLE IF NOT EXISTS lease_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- Removed foreign key constraint to users table
    lease_a_id UUID REFERENCES leases(id) ON DELETE CASCADE,
    lease_b_id UUID REFERENCES leases(id) ON DELETE CASCADE,
    
    -- Comparison metadata
    comparison_type VARCHAR(50) DEFAULT 'SIDE_BY_SIDE', -- SIDE_BY_SIDE, DELTA, SUMMARY
    fields_compared JSONB, -- List of field names compared
    differences_found INTEGER,
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lease_comparisons_user_id ON lease_comparisons(user_id);
CREATE INDEX idx_lease_comparisons_created_at ON lease_comparisons(created_at DESC);

-- Client Portal Activity Log
-- Track client portal usage for analytics

CREATE TABLE IF NOT EXISTS portal_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- Removed foreign key constraint to users table
    activity_type VARCHAR(50) NOT NULL, -- LOGIN, UPLOAD, VIEW_LEASE, DOWNLOAD_REPORT, COMPARE_LEASES
    resource_type VARCHAR(50), -- LEASE, REPORT, EXPORT
    resource_id UUID,
    
    -- Details
    metadata JSONB,
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_portal_activity_user_id ON portal_activity_log(user_id);
CREATE INDEX idx_portal_activity_created_at ON portal_activity_log(created_at DESC);
CREATE INDEX idx_portal_activity_type ON portal_activity_log(activity_type);

-- Client Preferences
-- Store client-specific settings and preferences

CREATE TABLE IF NOT EXISTS client_preferences (
    user_id UUID PRIMARY KEY,  -- Removed foreign key constraint to users table
    
    -- Dashboard preferences
    default_view VARCHAR(50) DEFAULT 'GRID', -- GRID, LIST, TIMELINE
    leases_per_page INTEGER DEFAULT 20,
    show_archived BOOLEAN DEFAULT FALSE,
    
    -- Notification preferences
    email_on_complete BOOLEAN DEFAULT TRUE,
    email_on_approval BOOLEAN DEFAULT TRUE,
    email_on_export BOOLEAN DEFAULT FALSE,
    
    -- Export preferences
    default_export_format VARCHAR(20) DEFAULT 'PDF', -- PDF, CSV, XLSX
    include_low_confidence BOOLEAN DEFAULT TRUE,
    
    -- Display preferences
    date_format VARCHAR(20) DEFAULT 'MM/DD/YYYY',
    currency_format VARCHAR(20) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'America/Los_Angeles',
    
    -- Feature flags for this client
    enable_comparisons BOOLEAN DEFAULT TRUE,
    enable_bulk_export BOOLEAN DEFAULT FALSE,
    enable_api_access BOOLEAN DEFAULT FALSE,
    
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE export_history IS 'Tracks all exports (PDF, CSV) for audit and analytics';
COMMENT ON TABLE lease_processing_status IS 'Real-time status tracking for lease extraction pipeline';
COMMENT ON TABLE lease_comparisons IS 'Tracks lease comparison sessions for analytics';
COMMENT ON TABLE portal_activity_log IS 'Activity log for client portal usage analytics';
COMMENT ON TABLE client_preferences IS 'Client-specific preferences and settings';
