-- ═══════════════════════════════════════════════════════════════════════════════
-- Fix Amendment Resolution Graph™ Permissions
-- Run this in Supabase SQL Editor to grant access to all amendment tables
-- ═══════════════════════════════════════════════════════════════════════════════

-- Grant full access to amendment tables for all roles
GRANT ALL ON public.amendments TO anon, authenticated, service_role;
GRANT ALL ON public.amendment_clauses TO anon, authenticated, service_role;
GRANT ALL ON public.lease_clause_history TO anon, authenticated, service_role;
GRANT ALL ON public.amendment_relationships TO anon, authenticated, service_role;

-- Grant access to sequences for ID generation
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- Grant execute permissions on RPC functions
GRANT EXECUTE ON FUNCTION public.get_controlling_clause TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_amendment_chain TO anon, authenticated, service_role;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ Amendment table permissions granted successfully!';
END $$;
