-- ============================================================================
-- CAM DISPUTE HISTORY TABLE - SCHEMA UPDATE
-- Phase 2B: Updated column names to match application code
-- ============================================================================

-- Drop the old table if it exists (backup data first if needed!)
DROP TABLE IF EXISTS public.cam_dispute_history CASCADE;

-- Recreate with correct column names
CREATE TABLE public.cam_dispute_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID NOT NULL REFERENCES public.cam_reconciliations(id) ON DELETE CASCADE,
    
    -- Action/Event Details
    action TEXT NOT NULL,  -- e.g., "Status updated to DISPUTE_FILED", "Dispute letter sent", etc.
    notes TEXT,            -- Additional notes/details about the action
    
    -- Metadata
    performed_by TEXT,     -- User ID or username
    performed_at TIMESTAMP DEFAULT NOW(),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_cam_dispute_history_reconciliation_id 
    ON public.cam_dispute_history(reconciliation_id);

CREATE INDEX IF NOT EXISTS idx_cam_dispute_history_performed_at 
    ON public.cam_dispute_history(performed_at);

-- Permissions
GRANT ALL ON public.cam_dispute_history TO authenticated, service_role;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Run this to verify the table structure:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'cam_dispute_history' 
-- ORDER BY ordinal_position;
