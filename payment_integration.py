"""
LeaseAI Stripe billing service.

Expands the original PaymentHandler checkout stub with subscription
management, usage-aware plan metadata, and customer portal sessions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import stripe

import config

stripe.api_key = config.STRIPE_SECRET_KEY

APP_URL = getattr(config, "APP_URL", "http://localhost:8501")
# Stripe tax code: Software as a service (SaaS) — business use
# Required when Managed Payments is enabled on the Stripe account.
SAAS_TAX_CODE = "txcd_10103000"


class PaymentHandler:
    """Stripe subscription helper used by the Billing page and webhooks."""

    # unit_amount is cents. $2,500/mo = 250000
    PLANS = {
        "starter": {
            "name": "Starter",
            "monthly_amount": 250000,
            "annual_amount": 2500000,  # 10 months = 2 months free
            "currency": "usd",
            "lease_limit": 50,
            "description": "50 lease abstractions per month",
        },
        "growth": {
            "name": "Growth",
            "monthly_amount": 600000,
            "annual_amount": 6000000,
            "currency": "usd",
            "lease_limit": 200,
            "description": "200 lease abstractions per month",
        },
        "enterprise": {
            "name": "Enterprise",
            "monthly_amount": 1500000,
            "annual_amount": 15000000,
            "currency": "usd",
            "lease_limit": None,
            "description": "Unlimited lease abstractions",
        },
    }

    def __init__(self, supabase_client=None):
        self.sb = supabase_client

    def is_configured(self) -> bool:
        key = config.STRIPE_SECRET_KEY or ""
        return bool(key) and not key.startswith("sk_test_your-stripe")

    def get_plan(self, plan_type: str) -> Dict[str, Any]:
        plan = self.PLANS.get((plan_type or "").lower())
        if not plan:
            raise ValueError(f"Invalid plan: {plan_type}")
        return plan

    def create_checkout_session(
        self,
        plan_type: str,
        client_email: str,
        billing_interval: str = "monthly",
        client_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> str:
        plan = self.get_plan(plan_type)
        interval = "year" if billing_interval == "annual" else "month"
        amount = plan["annual_amount"] if interval == "year" else plan["monthly_amount"]

        customer_id = self._ensure_customer(client_email, client_id)

        session_kwargs = {
            "mode": "subscription",
            # Account default is Managed Payments, which rejects inline price_data
            # products without a pre-created tax code. Disable it on this session.
            "managed_payments": {"enabled": False},
        }
        if customer_id:
            session_kwargs["customer"] = customer_id
        else:
            session_kwargs["customer_email"] = client_email

        session = stripe.checkout.Session.create(
            **session_kwargs,
            line_items=[
                {
                    "price_data": {
                        "currency": plan["currency"],
                        "product_data": {
                            "name": f"LeaseAI {plan['name']}",
                            "description": plan["description"],
                            "tax_code": SAAS_TAX_CODE,
                        },
                        "unit_amount": amount,
                        "recurring": {"interval": interval},
                    },
                    "quantity": 1,
                }
            ],
            client_reference_id=str(client_id) if client_id else None,
            metadata={
                "client_id": str(client_id) if client_id else "",
                "plan_tier": plan_type.lower(),
                "billing_interval": "annual" if interval == "year" else "monthly",
            },
            subscription_data={
                "metadata": {
                    "client_id": str(client_id) if client_id else "",
                    "plan_tier": plan_type.lower(),
                    "billing_interval": "annual" if interval == "year" else "monthly",
                }
            },
            success_url=success_url or f"{APP_URL}/?payment=success",
            cancel_url=cancel_url or f"{APP_URL}/?payment=cancelled",
            allow_promotion_codes=True,
        )
        return session.url

    def create_billing_portal_session(self, stripe_customer_id: str, return_url: Optional[str] = None) -> str:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url or APP_URL,
        )
        return session.url

    def change_plan(
        self,
        stripe_subscription_id: str,
        new_plan_type: str,
        billing_interval: str = "monthly",
    ) -> Dict[str, Any]:
        plan = self.get_plan(new_plan_type)
        interval = "year" if billing_interval == "annual" else "month"
        amount = plan["annual_amount"] if interval == "year" else plan["monthly_amount"]

        subscription = stripe.Subscription.retrieve(stripe_subscription_id)
        item_id = subscription["items"]["data"][0]["id"]

        price = stripe.Price.create(
            currency=plan["currency"],
            unit_amount=amount,
            recurring={"interval": interval},
            product_data={"name": f"LeaseAI {plan['name']}", "tax_code": SAAS_TAX_CODE},
        )

        updated = stripe.Subscription.modify(
            stripe_subscription_id,
            items=[{"id": item_id, "price": price.id}],
            proration_behavior="create_prorations",
            metadata={
                **(subscription.get("metadata") or {}),
                "plan_tier": new_plan_type.lower(),
                "billing_interval": "annual" if interval == "year" else "monthly",
            },
        )
        return updated

    def cancel_subscription(self, stripe_subscription_id: str, immediately: bool = False) -> Dict[str, Any]:
        if immediately:
            return stripe.Subscription.delete(stripe_subscription_id)
        return stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)

    def list_invoices(self, stripe_customer_id: str, limit: int = 12) -> list:
        invoices = stripe.Invoice.list(customer=stripe_customer_id, limit=limit)
        return invoices.get("data", [])

    def _ensure_customer(self, email: str, client_id: Optional[str]) -> Optional[str]:
        if self.sb and client_id:
            try:
                existing = (
                    self.sb.table("clients")
                    .select("stripe_customer_id")
                    .eq("id", client_id)
                    .limit(1)
                    .execute()
                )
                if existing.data and existing.data[0].get("stripe_customer_id"):
                    return existing.data[0]["stripe_customer_id"]
            except Exception:
                pass

        customer = stripe.Customer.create(
            email=email,
            metadata={"client_id": str(client_id) if client_id else ""},
        )

        if self.sb and client_id:
            try:
                self.sb.table("clients").update(
                    {"stripe_customer_id": customer.id}
                ).eq("id", client_id).execute()
            except Exception:
                pass

        return customer.id

    def apply_subscription_to_client(
        self,
        client_id: Optional[str],
        stripe_customer_id: str,
        subscription_obj: Dict[str, Any],
        plan_tier: Optional[str] = None,
        billing_interval: Optional[str] = None,
    ) -> None:
        if not self.sb:
            return

        metadata = subscription_obj.get("metadata") or {}
        plan_tier = plan_tier or metadata.get("plan_tier") or "starter"
        billing_interval = billing_interval or metadata.get("billing_interval") or "monthly"
        status = subscription_obj.get("status") or "active"
        period_end = _unix_to_iso(subscription_obj.get("current_period_end"))
        period_start = _unix_to_iso(subscription_obj.get("current_period_start"))

        update = {
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": subscription_obj.get("id"),
            "plan_tier": plan_tier,
            "billing_interval": billing_interval,
            "subscription_status": status,
            "current_period_end": period_end,
            "cancel_at_period_end": bool(subscription_obj.get("cancel_at_period_end")),
            "subscription_updated_at": datetime.utcnow().isoformat(),
        }
        if status == "active":
            update["failed_payment_count"] = 0

        if client_id:
            self.sb.table("clients").update(update).eq("id", client_id).execute()
        elif stripe_customer_id:
            self.sb.table("clients").update(update).eq(
                "stripe_customer_id", stripe_customer_id
            ).execute()

        record = {
            "client_id": client_id,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": subscription_obj.get("id"),
            "plan_tier": plan_tier,
            "billing_interval": billing_interval,
            "status": status,
            "current_period_start": period_start,
            "current_period_end": period_end,
            "cancel_at_period_end": bool(subscription_obj.get("cancel_at_period_end")),
            "raw_payload": subscription_obj,
            "updated_at": datetime.utcnow().isoformat(),
        }
        try:
            self.sb.table("subscriptions").upsert(
                record, on_conflict="stripe_subscription_id"
            ).execute()
        except Exception:
            try:
                self.sb.table("subscriptions").insert(record).execute()
            except Exception:
                pass


def _unix_to_iso(value) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.utcfromtimestamp(int(value)).isoformat()
    except Exception:
        return None


def get_client_billing(supabase_client, client_id: str) -> Dict[str, Any]:
    defaults = {
        "plan_tier": "none",
        "subscription_status": "none",
        "billing_interval": None,
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
        "failed_payment_count": 0,
    }
    if not client_id:
        return defaults
    try:
        result = (
            supabase_client.table("clients")
            .select(
                "plan_tier, subscription_status, billing_interval, stripe_customer_id, "
                "stripe_subscription_id, current_period_end, cancel_at_period_end, failed_payment_count"
            )
            .eq("id", client_id)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            for key, value in defaults.items():
                row.setdefault(key, value)
            return row
    except Exception:
        pass
    return defaults
