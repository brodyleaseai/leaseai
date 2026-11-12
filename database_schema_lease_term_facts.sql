-- ============================================================================
-- LEASE TERM FACTS (anonymized terms warehouse)
-- Typed, de-identified facts copied from processed leases.
-- Does not store party names, street addresses, filenames, or source text.
-- Run in the Supabase SQL Editor.
-- ============================================================================

ALTER TABLE public.clients
    ADD COLUMN IF NOT EXISTS allow_anonymized_corpus BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.clients.allow_anonymized_corpus IS
    'When true, this customer opted in so de-identified term facts may be included in aggregated industry statistics.';

CREATE TABLE IF NOT EXISTS public.lease_term_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lease_id UUID NOT NULL REFERENCES public.leases(id) ON DELETE CASCADE,
    client_id UUID REFERENCES public.clients(id) ON DELETE SET NULL,
    as_of DATE NOT NULL DEFAULT CURRENT_DATE,
    review_status TEXT NOT NULL DEFAULT 'EXTRACTED',
    country TEXT,
    region TEXT,
    locality TEXT,
    asset_class TEXT,
    lease_type TEXT,
    net_lease_type TEXT,
    commencement_year INTEGER,
    expiration_year INTEGER,
    term_months INTEGER,
    rsf NUMERIC,
    building_rsf NUMERIC,
    monthly_rent NUMERIC,
    annual_rent NUMERIC,
    rent_per_rsf_year NUMERIC,
    free_rent_months NUMERIC,
    escalation_type TEXT,
    escalation_pct NUMERIC,
    cam_cap_pct NUMERIC,
    renewal_options INTEGER,
    renewal_term_months INTEGER,
    renewal_notice_months INTEGER,
    security_deposit NUMERIC,
    has_percentage_rent BOOLEAN,
    has_early_termination BOOLEAN,
    governing_law TEXT,
    source_quality TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lease_id)
);

CREATE INDEX IF NOT EXISTS idx_lease_term_facts_as_of ON public.lease_term_facts (as_of);
CREATE INDEX IF NOT EXISTS idx_lease_term_facts_market
    ON public.lease_term_facts (country, region, locality);
CREATE INDEX IF NOT EXISTS idx_lease_term_facts_consent_client
    ON public.lease_term_facts (client_id);

COMMENT ON TABLE public.lease_term_facts IS
    'Internal typed lease-term facts. lease_id is for upsert only and is omitted from partner export.';

ALTER TABLE public.lease_term_facts ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.lease_term_facts TO service_role;

-- Partner / benchmark export: opted-in customers only, no identifiers.
CREATE OR REPLACE VIEW public.lease_term_facts_export AS
SELECT
    f.as_of,
    f.review_status,
    f.country,
    f.region,
    f.locality,
    f.asset_class,
    f.lease_type,
    f.net_lease_type,
    f.commencement_year,
    f.expiration_year,
    f.term_months,
    f.rsf,
    f.building_rsf,
    f.monthly_rent,
    f.annual_rent,
    f.rent_per_rsf_year,
    f.free_rent_months,
    f.escalation_type,
    f.escalation_pct,
    f.cam_cap_pct,
    f.renewal_options,
    f.renewal_term_months,
    f.renewal_notice_months,
    f.security_deposit,
    f.has_percentage_rent,
    f.has_early_termination,
    f.governing_law,
    f.source_quality
FROM public.lease_term_facts f
JOIN public.clients c ON c.id = f.client_id
WHERE c.allow_anonymized_corpus IS TRUE;

GRANT SELECT ON public.lease_term_facts_export TO service_role;
