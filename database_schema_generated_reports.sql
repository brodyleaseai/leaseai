-- ============================================================================
-- GENERATED REPORTS ARCHIVE + COMPLETE CAM WORKPAPER
-- Run this in the Supabase SQL Editor after database_schema_cam_reconciliation.sql
--
-- What this adds:
--   1. generated_reports  — every product PDF (lease abstract, CAM workpaper)
--      organized by lease, kind, year, with storage path and checksum
--   2. Settlement columns on cam_reconciliations (paid, remaining due, cap)
--   3. should_challenge on cam_line_items
--   4. Private storage bucket leaseai-reports for the PDF bytes
--
-- Safe to re-run. Does not drop data.
-- ============================================================================

-- Table: generated product PDFs (abstracts, CAM workpapers, later ASC 842, etc.)
CREATE TABLE IF NOT EXISTS public.generated_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID REFERENCES public.leases(id) ON DELETE CASCADE,
    client_id UUID,
    reconciliation_id UUID REFERENCES public.cam_reconciliations(id) ON DELETE SET NULL,

    report_kind VARCHAR(50) NOT NULL,
    -- LEASE_ABSTRACT | CAM_WORKPAPER | CAM_STATEMENT | DISPUTE_LETTER | ASC842
    reconciliation_year INTEGER,

    filename TEXT NOT NULL,
    storage_bucket TEXT NOT NULL DEFAULT 'leaseai-reports',
    storage_path TEXT NOT NULL,
    file_url TEXT,
    file_size_bytes INTEGER,
    content_sha256 TEXT,
    content_type TEXT NOT NULL DEFAULT 'application/pdf',

    metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generated_reports_lease
    ON public.generated_reports (lease_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_reports_kind
    ON public.generated_reports (report_kind, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_reports_recon
    ON public.generated_reports (reconciliation_id);
CREATE INDEX IF NOT EXISTS idx_generated_reports_client
    ON public.generated_reports (client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_reports_path
    ON public.generated_reports (storage_bucket, storage_path);

COMMENT ON TABLE public.generated_reports IS
    'Archived product PDFs (lease abstracts, CAM workpapers) with storage pointers';

-- Complete CAM workpaper columns (paid / remaining due / cap / linked PDF)
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS estimated_cam_paid DECIMAL(12,2);
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS landlord_trueup_billed DECIMAL(12,2);
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS lease_remaining_due DECIMAL(12,2);
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS excluded_building_charges DECIMAL(12,2);
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS allowable_building_charges DECIMAL(12,2);
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS cam_cap_applied BOOLEAN;
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS calculation_steps JSONB;
ALTER TABLE public.cam_reconciliations
    ADD COLUMN IF NOT EXISTS generated_report_id UUID;

COMMENT ON COLUMN public.cam_reconciliations.estimated_cam_paid IS
    'Estimated CAM already paid by the tenant during the year';
COMMENT ON COLUMN public.cam_reconciliations.lease_remaining_due IS
    'Allowable tenant share minus estimated paid (negative = credit due tenant)';
COMMENT ON COLUMN public.cam_reconciliations.generated_report_id IS
    'Latest archived CAM workpaper in generated_reports';

ALTER TABLE public.cam_line_items
    ADD COLUMN IF NOT EXISTS should_challenge BOOLEAN DEFAULT FALSE;

GRANT ALL ON public.generated_reports TO authenticated, service_role;

-- Private bucket for generated PDFs (source leases stay in the existing leases bucket)
INSERT INTO storage.buckets (id, name, public)
VALUES ('leaseai-reports', 'leaseai-reports', false)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "leaseai reports service" ON storage.objects;
CREATE POLICY "leaseai reports service"
    ON storage.objects
    FOR ALL
    TO service_role
    USING (bucket_id = 'leaseai-reports')
    WITH CHECK (bucket_id = 'leaseai-reports');
