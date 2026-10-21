-- Grant Permissions for Audit Logging Tables
-- Run this after creating the audit tables to allow service_role access

-- Grant permissions on audit_log table
GRANT SELECT, INSERT ON public.audit_log TO service_role;
GRANT SELECT, INSERT ON public.audit_log TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Grant permissions on security_events table
GRANT SELECT, INSERT, UPDATE ON public.security_events TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.security_events TO authenticated;

-- Grant permissions on backup_verifications table
GRANT ALL ON public.backup_verifications TO service_role;
GRANT SELECT ON public.backup_verifications TO authenticated;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION archive_old_audit_logs(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_user_audit_summary(UUID, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_resource_audit_history(VARCHAR, UUID, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION get_security_event_stats(INTEGER) TO service_role;

-- Allow authenticated users to call read-only functions
GRANT EXECUTE ON FUNCTION get_user_audit_summary(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_resource_audit_history(VARCHAR, UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_security_event_stats(INTEGER) TO authenticated;
