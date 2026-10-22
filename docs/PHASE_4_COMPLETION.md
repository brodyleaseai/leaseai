# Phase 4: Payment Integration & Billing

**Status:** Implementation complete. Stripe account and live keys are operator steps.

## Already existed (kept, not rebuilt)

- `payment_integration.py` checkout stub (amounts were cents-wrong; now $2,500 = 250000 cents)
- `config.py` Stripe env vars
- Client portal / Home billing placeholders

## Added

- `database_schema_billing.sql`
- Expanded `payment_integration.py`
- `usage_limits.py`
- `stripe_webhook_handler.py`
- `pages/15_💳_Billing.py`
- Usage enforcement on upload and bulk upload
- Admin Dashboard sales metrics (MRR / ARR)
- `docs/STRIPE_SETUP_GUIDE.md`

## Not built

- HubSpot / Pipedrive (roadmap 4B optional; needs your CRM account)
- Creating the Stripe account itself (you do this in the Stripe Dashboard)
