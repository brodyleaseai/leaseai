-- ═══════════════════════════════════════════════════════════════════════════════
-- Fix Amendment Resolution Graph™ Permissions
-- Run this in Supabase SQL Editor to grant access to all amendment tables
-- ═══════════════════════════════════════════════════════════════════════════════

-- Backend-only grants. Do not grant to anon — that is the
-- rls_disabled_in_public / public table leak Supabase warned about.
GRANT ALL ON public.amendments TO authenticated, service_role;
GRANT ALL ON public.amendment_clauses TO authenticated, service_role;
GRANT ALL ON public.lease_clause_history TO authenticated, service_role;
GRANT ALL ON public.amendment_relationships TO authenticated, service_role;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.get_controlling_clause TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_amendment_chain TO authenticated, service_role;

GRANT USAGE ON SCHEMA public TO authenticated, service_role;

-- Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ Amendment table permissions granted successfully!';
END $$;
