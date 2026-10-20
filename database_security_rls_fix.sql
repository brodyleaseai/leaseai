-- ============================================================================
-- SUPABASE ROW-LEVEL SECURITY (RLS) FIX
-- Secure all LeaseAI tables with RLS policies
-- ============================================================================

-- This script enables Row-Level Security on all tables and creates policies
-- to allow authenticated users full access to their data

-- ============================================================================
-- ENABLE ROW-LEVEL SECURITY ON ALL TABLES
-- ============================================================================

ALTER TABLE public.leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.extracted_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asc842_calculations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cam_reconciliations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cam_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cam_provisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cam_statement_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cam_dispute_history ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- CREATE RLS POLICIES FOR AUTHENTICATED USERS
-- ============================================================================

-- Policy: Allow authenticated users to SELECT, INSERT, UPDATE, DELETE all data
-- This is a simple policy suitable for single-tenant or development use
-- For multi-tenant production, you'd add user_id filtering

-- LEASES TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.leases
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- EXTRACTED_FIELDS TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.extracted_fields
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- ASC842_CALCULATIONS TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.asc842_calculations
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- CAM_RECONCILIATIONS TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.cam_reconciliations
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- CAM_LINE_ITEMS TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.cam_line_items
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- CAM_PROVISIONS TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.cam_provisions
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- CAM_STATEMENT_UPLOADS TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.cam_statement_uploads
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- CAM_DISPUTE_HISTORY TABLE
CREATE POLICY "Allow all operations for authenticated users" ON public.cam_dispute_history
    FOR ALL
    USING (auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'authenticated');

-- ============================================================================
-- ALLOW SERVICE ROLE TO BYPASS RLS (for backend operations)
-- ============================================================================

-- Service role can bypass RLS - this is needed for backend operations
-- The service_role key should NEVER be exposed in client-side code

-- Note: Service role automatically bypasses RLS, no additional policy needed
-- Just ensure you're using the service_role key in your backend/Streamlit app

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these queries to verify RLS is enabled:

-- Check RLS status on all tables
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN (
        'leases', 
        'extracted_fields', 
        'asc842_calculations',
        'cam_reconciliations',
        'cam_line_items',
        'cam_provisions',
        'cam_statement_uploads',
        'cam_dispute_history'
    )
ORDER BY tablename;

-- Check policies on all tables
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ============================================================================
-- NOTES
-- ============================================================================

-- CURRENT SETUP: Simple single-tenant policy
-- - All authenticated users can access all data
-- - Suitable for: Development, single-user, single-tenant applications

-- FOR MULTI-TENANT PRODUCTION (Future Enhancement):
-- You would add user_id or tenant_id columns and modify policies like:
--
-- CREATE POLICY "Users can only see their own leases" ON public.leases
--     FOR SELECT
--     USING (auth.uid() = uploaded_by);
--
-- CREATE POLICY "Users can only insert their own leases" ON public.leases
--     FOR INSERT
--     WITH CHECK (auth.uid() = uploaded_by);
-- 
-- And so on for each table

-- IMPORTANT: Your Streamlit app uses the SERVICE_ROLE key, which bypasses RLS
-- This is correct for backend applications
-- Never use service_role key in client-side JavaScript/browser code!
