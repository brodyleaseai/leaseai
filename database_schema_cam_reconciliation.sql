-- ============================================================================
-- CAM RECONCILIATION DATABASE SCHEMA
-- Phase 2A: CAM Data Model
-- LeaseAI - Property Management Platform
-- ============================================================================

-- Table 1: CAM Reconciliations
-- Stores high-level CAM reconciliation records for each lease/year
CREATE TABLE IF NOT EXISTS public.cam_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID NOT NULL REFERENCES public.leases(id) ON DELETE CASCADE,
    
    -- Period Information
    reconciliation_year INTEGER NOT NULL,
    statement_date DATE,
    
    -- Landlord Charges (from CAM statement)
    landlord_total_charges DECIMAL(12,2),
    landlord_tenant_share DECIMAL(12,2),
    
    -- Calculated Charges (per lease terms)
    calculated_total_charges DECIMAL(12,2),
    calculated_tenant_share DECIMAL(12,2),
    
    -- Variance Analysis
    variance_amount DECIMAL(12,2),
    variance_percentage DECIMAL(5,2),
    
    -- Status & Workflow
    status VARCHAR(50) DEFAULT 'DRAFT',
    -- Status options: DRAFT, UNDER_REVIEW, DISCREPANCY_FOUND, DISPUTE_FILED, ACCEPTED, RESOLVED
    
    dispute_status VARCHAR(50),
    -- Dispute status: NOT_DISPUTED, CHALLENGE_DRAFTED, SENT_TO_LANDLORD, UNDER_NEGOTIATION, RESOLVED, CLOSED
    
    resolution_amount DECIMAL(12,2),
    resolution_date DATE,
    resolution_notes TEXT,
    
    -- Metadata
    uploaded_by UUID,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    
    -- Attachments
    landlord_statement_url TEXT,
    reconciliation_report_url TEXT,
    dispute_letter_url TEXT,
    
    -- Audit Trail
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_lease_year UNIQUE(lease_id, reconciliation_year)
);

-- Table 2: CAM Line Items
-- Stores individual line items from CAM statements with categorization
CREATE TABLE IF NOT EXISTS public.cam_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID NOT NULL REFERENCES public.cam_reconciliations(id) ON DELETE CASCADE,
    
    -- Line Item Details
    line_number INTEGER,
    category VARCHAR(100),
    -- Categories: UTILITIES, MAINTENANCE, REPAIRS, INSURANCE, PROPERTY_TAX, MANAGEMENT_FEE, 
    --            SECURITY, LANDSCAPING, SNOW_REMOVAL, JANITORIAL, HVAC, ELEVATOR, PARKING, OTHER
    
    description TEXT,
    
    -- Landlord's Charges
    landlord_amount DECIMAL(12,2),
    landlord_notes TEXT,
    
    -- Calculated/Expected Amount
    calculated_amount DECIMAL(12,2),
    
    -- Variance
    variance_amount DECIMAL(12,2),
    variance_percentage DECIMAL(5,2),
    
    -- Flags
    is_disputed BOOLEAN DEFAULT FALSE,
    is_excluded BOOLEAN DEFAULT FALSE,  -- Per lease terms (e.g., capital improvements excluded)
    is_over_cap BOOLEAN DEFAULT FALSE,   -- Exceeds CAM cap per lease
    
    dispute_reason TEXT,
    recommended_action VARCHAR(100),
    -- Actions: ACCEPT, CHALLENGE, REQUEST_CLARIFICATION, EXCLUDED_PER_LEASE
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table 3: CAM Provisions (extracted from leases)
-- Stores CAM-specific terms extracted from lease agreements
CREATE TABLE IF NOT EXISTS public.cam_provisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID NOT NULL REFERENCES public.leases(id) ON DELETE CASCADE,
    
    -- Base Year & Stops
    cam_base_year INTEGER,
    cam_stop_amount DECIMAL(12,2),
    cam_base_amount DECIMAL(12,2),
    
    -- Tenant's Share
    tenant_prorata_share DECIMAL(5,4),  -- e.g., 0.0523 = 5.23%
    tenant_square_footage INTEGER,
    building_square_footage INTEGER,
    
    -- CAM Caps & Escalations
    has_cam_cap BOOLEAN DEFAULT FALSE,
    cam_cap_percentage DECIMAL(5,2),  -- e.g., 5.00 = 5% max annual increase
    cam_cap_amount DECIMAL(12,2),     -- Fixed dollar cap
    
    -- Exclusions (items landlord cannot charge)
    excluded_items TEXT[],  -- Array of excluded categories
    exclusions_description TEXT,
    
    -- Payment Terms
    cam_payment_frequency VARCHAR(50),  -- MONTHLY, QUARTERLY, ANNUALLY
    cam_reconciliation_deadline VARCHAR(100),  -- e.g., "Within 90 days of year-end"
    tenant_audit_right BOOLEAN DEFAULT FALSE,
    audit_deadline VARCHAR(100),
    
    -- Confidence Scores
    base_year_confidence VARCHAR(20),
    prorata_share_confidence VARCHAR(20),
    exclusions_confidence VARCHAR(20),
    
    -- Metadata
    extracted_at TIMESTAMP DEFAULT NOW(),
    extracted_by VARCHAR(50),  -- AI extraction or manual entry
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_lease_cam UNIQUE(lease_id)
);

-- Table 4: CAM Statement Uploads
-- Tracks uploaded landlord CAM statements (PDFs/CSVs)
CREATE TABLE IF NOT EXISTS public.cam_statement_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID REFERENCES public.cam_reconciliations(id) ON DELETE SET NULL,
    lease_id UUID NOT NULL REFERENCES public.leases(id) ON DELETE CASCADE,
    
    -- File Details
    filename VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_size_bytes BIGINT,
    file_type VARCHAR(50),  -- PDF, CSV, XLSX
    
    -- Extraction Status
    extraction_status VARCHAR(50) DEFAULT 'PENDING',
    -- Status: PENDING, PROCESSING, COMPLETED, FAILED
    
    extraction_confidence DECIMAL(5,2),  -- Overall confidence score
    extracted_data JSONB,  -- Structured extraction results
    
    -- Metadata
    uploaded_by UUID,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table 5: CAM Dispute History
-- Tracks dispute communications and resolution timeline
CREATE TABLE IF NOT EXISTS public.cam_dispute_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID NOT NULL REFERENCES public.cam_reconciliations(id) ON DELETE CASCADE,
    
    -- Action/Event Details
    action TEXT NOT NULL,  -- e.g., "Status updated to DISPUTE_FILED", "Dispute letter sent"
    notes TEXT,            -- Additional notes/details about the action
    
    -- Metadata
    performed_by TEXT,     -- User ID or username who performed the action
    performed_at TIMESTAMP DEFAULT NOW(),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- CAM Reconciliations
CREATE INDEX IF NOT EXISTS idx_cam_reconciliations_lease_id ON public.cam_reconciliations(lease_id);
CREATE INDEX IF NOT EXISTS idx_cam_reconciliations_year ON public.cam_reconciliations(reconciliation_year);
CREATE INDEX IF NOT EXISTS idx_cam_reconciliations_status ON public.cam_reconciliations(status);
CREATE INDEX IF NOT EXISTS idx_cam_reconciliations_dispute_status ON public.cam_reconciliations(dispute_status);

-- CAM Line Items
CREATE INDEX IF NOT EXISTS idx_cam_line_items_reconciliation_id ON public.cam_line_items(reconciliation_id);
CREATE INDEX IF NOT EXISTS idx_cam_line_items_category ON public.cam_line_items(category);
CREATE INDEX IF NOT EXISTS idx_cam_line_items_disputed ON public.cam_line_items(is_disputed);

-- CAM Provisions
CREATE INDEX IF NOT EXISTS idx_cam_provisions_lease_id ON public.cam_provisions(lease_id);

-- CAM Uploads
CREATE INDEX IF NOT EXISTS idx_cam_uploads_lease_id ON public.cam_statement_uploads(lease_id);
CREATE INDEX IF NOT EXISTS idx_cam_uploads_status ON public.cam_statement_uploads(extraction_status);

-- CAM Dispute History
CREATE INDEX IF NOT EXISTS idx_cam_dispute_history_reconciliation_id ON public.cam_dispute_history(reconciliation_id);
CREATE INDEX IF NOT EXISTS idx_cam_dispute_history_performed_at ON public.cam_dispute_history(performed_at);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

-- Grant permissions to authenticated users
GRANT ALL ON public.cam_reconciliations TO authenticated, service_role;
GRANT ALL ON public.cam_line_items TO authenticated, service_role;
GRANT ALL ON public.cam_provisions TO authenticated, service_role;
GRANT ALL ON public.cam_statement_uploads TO authenticated, service_role;
GRANT ALL ON public.cam_dispute_history TO authenticated, service_role;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - Optional
-- ============================================================================

-- Enable RLS (can be enabled later for multi-tenant security)
-- ALTER TABLE public.cam_reconciliations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.cam_line_items ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.cam_provisions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.cam_statement_uploads ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.cam_dispute_history ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- SAMPLE QUERIES (for testing)
-- ============================================================================

-- Find all CAM reconciliations with discrepancies > $500
-- SELECT * FROM cam_reconciliations WHERE ABS(variance_amount) > 500;

-- Get CAM breakdown by category for a reconciliation
-- SELECT category, SUM(landlord_amount) as total, SUM(variance_amount) as variance
-- FROM cam_line_items 
-- WHERE reconciliation_id = 'xxx'
-- GROUP BY category
-- ORDER BY ABS(SUM(variance_amount)) DESC;

-- Find leases with CAM caps
-- SELECT l.*, cp.cam_cap_percentage, cp.cam_cap_amount
-- FROM leases l
-- JOIN cam_provisions cp ON l.id = cp.lease_id
-- WHERE cp.has_cam_cap = TRUE;

-- Calculate total savings from successful disputes
-- SELECT SUM(resolution_amount) as total_savings
-- FROM cam_reconciliations
-- WHERE dispute_status = 'RESOLVED' AND resolution_amount > 0;
