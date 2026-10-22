# LeaseAI Stripe Setup Guide

Phase 4 billing uses Stripe Checkout, the Customer Portal, and webhooks.

## 1. Create a Stripe account

1. Sign up at https://dashboard.stripe.com/register
2. Stay in **Test mode** until the first live customer
3. Open **Developers → API keys**
4. Copy the Secret key and Publishable key

You do not need Stripe Connect for this billing model. LeaseAI is the merchant of record.

## 2. Products and prices

The app creates prices at checkout time (`price_data`), so you do not have to pre-create products.

Roadmap pricing:

| Plan | Monthly | Annual (2 months free) | Lease limit |
|------|---------|------------------------|-------------|
| Starter | $2,500 | $25,000 | 50 / month |
| Growth | $6,000 | $60,000 | 200 / month |
| Enterprise | $15,000 | $150,000 | Unlimited |

## 3. Environment variables

Add to `.env` or Streamlit secrets:

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
APP_URL=http://localhost:8501
```

`config.py` already reads these keys.

## 4. Database

Run `database_schema_billing.sql` in the Supabase SQL Editor.

## 5. Customer Portal

Stripe Dashboard → Settings → Billing → Customer portal → Enable.

This is required for card updates and invoice history from the Billing page.

## 6. Webhooks

Events to send:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

Local test:

```
stripe listen --forward-to localhost:8787/webhook
python stripe_webhook_handler.py
```

Paste the CLI webhook secret into `STRIPE_WEBHOOK_SECRET`.

Production: point a Stripe webhook endpoint at a public URL running `stripe_webhook_handler.py` (port 8787 by default).

## 7. Email

Receipt and dunning emails use SendGrid when `SENDGRID_API_KEY` is set. If it is not set, events still update the database.

## 8. Install

```
pip install stripe
```

## 9. Test checkout

1. `streamlit run Home.py`
2. Log in
3. Open **Billing**
4. Choose Starter monthly
5. Pay with Stripe test card `4242 4242 4242 4242`
6. Confirm the client row shows `plan_tier=starter` and `subscription_status=active`
