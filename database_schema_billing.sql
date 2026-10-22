-- LeaseAI Phase 4: Billing, subscriptions, and usage tracking
-- Run in Supabase SQL Editor

-- Billing columns on clients
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
ADD COLUMN IF NOT EXISTS plan_tier TEXT DEFAULT 'none',
ADD COLUMN IF NOT EXISTS billing_interval TEXT,
ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'none',
ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS failed_payment_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS subscription_updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_clients_stripe_customer ON clients(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_clients_subscription_status ON clients(subscription_status);
CREATE INDEX IF NOT EXISTS idx_clients_plan_tier ON clients(plan_tier);

-- Subscription history
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT UNIQUE,
    plan_tier TEXT NOT NULL,
    billing_interval TEXT NOT NULL,
    status TEXT NOT NULL,
    amount_cents INTEGER,
    currency TEXT DEFAULT 'usd',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_client ON subscriptions(client_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

-- Monthly abstraction usage
CREATE TABLE IF NOT EXISTS usage_monthly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    year_month TEXT NOT NULL,
    lease_count INTEGER DEFAULT 0,
    last_upload_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (client_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_usage_monthly_client ON usage_monthly(client_id);

-- Cached invoices from Stripe
CREATE TABLE IF NOT EXISTS billing_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    stripe_invoice_id TEXT UNIQUE,
    stripe_customer_id TEXT,
    amount_paid_cents INTEGER,
    amount_due_cents INTEGER,
    currency TEXT DEFAULT 'usd',
    status TEXT,
    invoice_pdf TEXT,
    hosted_invoice_url TEXT,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_invoices_client ON billing_invoices(client_id);

-- Idempotent webhook log
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    payload JSONB,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_type ON stripe_webhook_events(event_type);

GRANT SELECT, INSERT, UPDATE ON clients TO service_role, authenticated;
GRANT SELECT, INSERT, UPDATE ON subscriptions TO service_role, authenticated;
GRANT SELECT, INSERT, UPDATE ON usage_monthly TO service_role, authenticated;
GRANT SELECT, INSERT, UPDATE ON billing_invoices TO service_role, authenticated;
GRANT SELECT, INSERT, UPDATE ON stripe_webhook_events TO service_role, authenticated;

DO $$
BEGIN
    RAISE NOTICE 'Phase 4 billing schema applied.';
END $$;
