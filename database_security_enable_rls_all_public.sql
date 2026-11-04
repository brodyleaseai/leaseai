-- ============================================================================
-- LeaseAI — enable RLS on every public table and close anonymous access
-- ============================================================================
-- Fixes Supabase advisor: rls_disabled_in_public
--   "Anyone with your project URL can read, edit, and delete all data"
--
-- Why this is safe for LeaseAI:
--   The Streamlit app uses SUPABASE_SERVICE_KEY (service_role).
--   service_role bypasses RLS. The app keeps working.
--   The public anon key can no longer read or write lease data.
--
-- Run in Supabase: SQL Editor → New query → paste → Run
-- ============================================================================

-- 1. Enable RLS on every ordinary table in public.
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND NOT c.relrowsecurity
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
            t.schema_name,
            t.table_name
        );
        RAISE NOTICE 'Enabled RLS on %.%', t.schema_name, t.table_name;
    END LOOP;

    -- Also enable on tables that already have RLS (idempotent).
    FOR t IN
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
            t.schema_name,
            t.table_name
        );
    END LOOP;
END $$;

-- 2. Drop policies that allow the anonymous / PUBLIC roles.
DO $$
DECLARE
    pol record;
BEGIN
    FOR pol IN
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
          AND (
              'anon' = ANY (roles)
              OR 'public' = ANY (roles)
          )
    LOOP
        EXECUTE format(
            'DROP POLICY IF EXISTS %I ON %I.%I',
            pol.policyname,
            pol.schemaname,
            pol.tablename
        );
        RAISE NOTICE 'Dropped anon/public policy % on %.%',
            pol.policyname, pol.schemaname, pol.tablename;
    END LOOP;
END $$;

-- 3. Revoke table, sequence, and function rights from anon and PUBLIC.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, PUBLIC;

ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, PUBLIC;

-- 4. Keep backend access. service_role bypasses RLS; these grants are for
--    completeness if a table was created without default Supabase grants.
GRANT USAGE ON SCHEMA public TO service_role, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- authenticated may keep grants, but with RLS and no anon policies they
-- cannot read unless a specific policy allows it. Streamlit does not use
-- the anon key or end-user JWTs for data access.

-- ============================================================================
-- Verification — after Run, execute this block. Every row must show
-- rls_enabled = true. anon_privileges should be empty or '{none}'.
-- ============================================================================

SELECT
    c.relname AS table_name,
    c.relrowsecurity AS rls_enabled,
    COALESCE(
        (
            SELECT array_agg(privilege_type ORDER BY privilege_type)
            FROM information_schema.role_table_grants g
            WHERE g.table_schema = 'public'
              AND g.table_name = c.relname
              AND g.grantee = 'anon'
        ),
        ARRAY[]::text[]
    ) AS anon_privileges
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY c.relname;
