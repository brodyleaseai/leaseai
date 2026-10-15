-- ═══════════════════════════════════════════════════════════════════════════════
-- ASC 842 Calculations Table Schema
-- Run this in Supabase SQL Editor to create/fix the calculations table
-- ═══════════════════════════════════════════════════════════════════════════════

-- Drop existing table if it has wrong structure (be careful - deletes data!)
-- Only run this if you want to start fresh
-- DROP TABLE IF EXISTS asc842_calculations CASCADE;

-- Create asc842_calculations table
CREATE TABLE IF NOT EXISTS asc842_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign key to leases table
    lease_id UUID REFERENCES leases(id) ON DELETE CASCADE,
    
    -- Calculation metadata
    calculation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Classification result
    lease_classification TEXT NOT NULL,
    
    -- Key calculated values
    initial_rou_asset NUMERIC(15, 2) NOT NULL,
    initial_liability NUMERIC(15, 2) NOT NULL,
    lease_term_months INTEGER NOT NULL,
    discount_rate NUMERIC(5, 4) NOT NULL,
    
    -- Store full calculation inputs as JSON for audit trail
    calculation_data JSONB,
    
    -- Optional: Store full schedules as JSON (if you want)
    liability_schedule JSONB,
    rou_schedule JSONB,
    journal_entries JSONB,
    
    -- Metadata
    notes TEXT,
    created_by UUID,
    
    -- Indexes for better query performance
    CONSTRAINT asc842_calculations_lease_id_fkey FOREIGN KEY (lease_id) REFERENCES leases(id)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_asc842_lease_id ON asc842_calculations(lease_id);
CREATE INDEX IF NOT EXISTS idx_asc842_calculation_date ON asc842_calculations(calculation_date);
CREATE INDEX IF NOT EXISTS idx_asc842_classification ON asc842_calculations(lease_classification);

-- Grant permissions to all roles
GRANT ALL ON asc842_calculations TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- Add helpful comment
COMMENT ON TABLE asc842_calculations IS 'ASC 842 / IFRS 16 lease accounting compliance calculations';

-- Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ asc842_calculations table created successfully!';
END $$;
