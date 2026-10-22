"""
Stripe webhook processor for LeaseAI billing.

Handles:
- checkout.session.completed / subscription.created -> activate account
- invoice.payment_succeeded -> store invoice, optional receipt email
- invoice.payment_failed -> increment failures, suspend after 3
- customer.subscription.updated / deleted -> sync or archive

Run locally with Stripe CLI:
  stripe listen --forward-to localhost:8787/webhook
  python stripe_webhook_handler.py
"""

from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import stripe
from supabase import create_client

import config
from payment_integration import PaymentHandler

stripe.api_key = config.STRIPE_SECRET_KEY

SUSPEND_AFTER_FAILURES = 3


def get_supabase():
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def process_stripe_event(event: Dict[str, Any], supabase_client=None) -> str:
    sb = supabase_client or get_supabase()
    handler = PaymentHandler(sb)
    event_id = event.get("id")
    event_type = event.get("type")
    payload = event.get("data", {}).get("object", {})

    if _already_processed(sb, event_id):
        return "duplicate"

    _log_event(sb, event_id, event_type, event)

    try:
        if event_type in ("checkout.session.completed", "customer.subscription.created"):
            _handle_subscription_activated(sb, handler, event_type, payload)
        elif event_type == "customer.subscription.updated":
            _handle_subscription_updated(sb, handler, payload)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_canceled(sb, payload)
        elif event_type == "invoice.payment_succeeded":
            _handle_payment_succeeded(sb, payload)
        elif event_type == "invoice.payment_failed":
            _handle_payment_failed(sb, payload)
        _mark_processed(sb, event_id)
        return "processed"
    except Exception as exc:
        _mark_processed(sb, event_id, error=str(exc))
        raise


def _handle_subscription_activated(sb, handler: PaymentHandler, event_type: str, payload: Dict[str, Any]):
    client_id = _client_id_from(payload)
    if event_type == "checkout.session.completed":
        customer_id = payload.get("customer")
        subscription_id = payload.get("subscription")
        metadata = payload.get("metadata") or {}
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
        else:
            subscription = {"id": None, "status": "active", "metadata": metadata}
        handler.apply_subscription_to_client(
            client_id=client_id or metadata.get("client_id"),
            stripe_customer_id=customer_id,
            subscription_obj=subscription if isinstance(subscription, dict) else subscription.to_dict(),
            plan_tier=metadata.get("plan_tier"),
            billing_interval=metadata.get("billing_interval"),
        )
        return

    customer_id = payload.get("customer")
    metadata = payload.get("metadata") or {}
    handler.apply_subscription_to_client(
        client_id=client_id or metadata.get("client_id"),
        stripe_customer_id=customer_id,
        subscription_obj=payload,
        plan_tier=metadata.get("plan_tier"),
        billing_interval=metadata.get("billing_interval"),
    )


def _handle_subscription_updated(sb, handler: PaymentHandler, payload: Dict[str, Any]):
    metadata = payload.get("metadata") or {}
    handler.apply_subscription_to_client(
        client_id=metadata.get("client_id"),
        stripe_customer_id=payload.get("customer"),
        subscription_obj=payload,
        plan_tier=metadata.get("plan_tier"),
        billing_interval=metadata.get("billing_interval"),
    )


def _handle_subscription_canceled(sb, payload: Dict[str, Any]):
    customer_id = payload.get("customer")
    subscription_id = payload.get("id")
    update = {
        "subscription_status": "canceled",
        "cancel_at_period_end": False,
        "stripe_subscription_id": None,
        "subscription_updated_at": datetime.utcnow().isoformat(),
        "canceled_at": datetime.utcnow().isoformat() if False else None,
    }
    # Keep plan_tier for 30-day data retention; status canceled blocks paid limits
    if customer_id:
        sb.table("clients").update({
            "subscription_status": "canceled",
            "cancel_at_period_end": False,
            "subscription_updated_at": datetime.utcnow().isoformat(),
        }).eq("stripe_customer_id", customer_id).execute()
    if subscription_id:
        try:
            sb.table("subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("stripe_subscription_id", subscription_id).execute()
        except Exception:
            pass


def _handle_payment_succeeded(sb, payload: Dict[str, Any]):
    customer_id = payload.get("customer")
    client_id = _find_client_id(sb, customer_id)
    invoice = {
        "client_id": client_id,
        "stripe_invoice_id": payload.get("id"),
        "stripe_customer_id": customer_id,
        "amount_paid_cents": payload.get("amount_paid"),
        "amount_due_cents": payload.get("amount_due"),
        "currency": payload.get("currency"),
        "status": payload.get("status"),
        "invoice_pdf": payload.get("invoice_pdf"),
        "hosted_invoice_url": payload.get("hosted_invoice_url"),
        "period_start": _unix_to_iso(payload.get("period_start")),
        "period_end": _unix_to_iso(payload.get("period_end")),
        "paid_at": datetime.utcnow().isoformat(),
    }
    try:
        sb.table("billing_invoices").upsert(invoice, on_conflict="stripe_invoice_id").execute()
    except Exception:
        try:
            sb.table("billing_invoices").insert(invoice).execute()
        except Exception:
            pass

    if customer_id:
        sb.table("clients").update({
            "failed_payment_count": 0,
            "subscription_status": "active",
            "subscription_updated_at": datetime.utcnow().isoformat(),
        }).eq("stripe_customer_id", customer_id).execute()

    _send_receipt_email(sb, client_id, payload)


def _handle_payment_failed(sb, payload: Dict[str, Any]):
    customer_id = payload.get("customer")
    if not customer_id:
        return
    client = None
    try:
        result = (
            sb.table("clients")
            .select("id, email, failed_payment_count")
            .eq("stripe_customer_id", customer_id)
            .limit(1)
            .execute()
        )
        client = result.data[0] if result.data else None
    except Exception:
        client = None

    failures = int((client or {}).get("failed_payment_count") or 0) + 1
    new_status = "past_due"
    if failures >= SUSPEND_AFTER_FAILURES:
        new_status = "unpaid"

    update = {
        "failed_payment_count": failures,
        "subscription_status": new_status,
        "subscription_updated_at": datetime.utcnow().isoformat(),
    }
    sb.table("clients").update(update).eq("stripe_customer_id", customer_id).execute()
    _send_dunning_email(client, failures, new_status)


def _send_receipt_email(sb, client_id: Optional[str], invoice: Dict[str, Any]):
    email = _client_email(sb, client_id)
    if not email:
        return
    amount = (invoice.get("amount_paid") or 0) / 100
    url = invoice.get("hosted_invoice_url") or ""
    _send_email(
        email,
        "LeaseAI payment receipt",
        f"<p>We received your payment of ${amount:,.2f}.</p>"
        f"<p><a href='{url}'>View invoice</a></p>",
    )


def _send_dunning_email(client: Optional[Dict[str, Any]], failures: int, status: str):
    if not client or not client.get("email"):
        return
    if status == "unpaid":
        body = (
            f"<p>We could not collect payment after {failures} attempts. "
            "Your account is suspended until a payment method is updated.</p>"
        )
    else:
        body = (
            f"<p>Payment attempt {failures} failed. "
            "Please update your card on the Billing page to avoid interruption.</p>"
        )
    _send_email(client["email"], "LeaseAI payment failed", body)


def _send_email(to_email: str, subject: str, html: str):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        if not config.SENDGRID_API_KEY or config.SENDGRID_API_KEY == "your-sendgrid-key-here":
            print(f"[billing email skipped] {subject} -> {to_email}")
            return
        message = Mail(
            from_email=config.SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html,
        )
        SendGridAPIClient(config.SENDGRID_API_KEY).send(message)
    except Exception as exc:
        print(f"[billing email failed] {exc}")


def _client_id_from(payload: Dict[str, Any]) -> Optional[str]:
    metadata = payload.get("metadata") or {}
    return metadata.get("client_id") or payload.get("client_reference_id")


def _find_client_id(sb, stripe_customer_id: Optional[str]) -> Optional[str]:
    if not stripe_customer_id:
        return None
    try:
        result = (
            sb.table("clients")
            .select("id")
            .eq("stripe_customer_id", stripe_customer_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
    except Exception:
        return None
    return None


def _client_email(sb, client_id: Optional[str]) -> Optional[str]:
    if not client_id:
        return None
    try:
        result = sb.table("clients").select("email").eq("id", client_id).limit(1).execute()
        if result.data:
            return result.data[0].get("email")
    except Exception:
        return None
    return None


def _already_processed(sb, event_id: Optional[str]) -> bool:
    if not event_id:
        return False
    try:
        result = (
            sb.table("stripe_webhook_events")
            .select("processed")
            .eq("stripe_event_id", event_id)
            .limit(1)
            .execute()
        )
        return bool(result.data and result.data[0].get("processed"))
    except Exception:
        return False


def _log_event(sb, event_id, event_type, event):
    if not event_id:
        return
    try:
        sb.table("stripe_webhook_events").insert({
            "stripe_event_id": event_id,
            "event_type": event_type,
            "processed": False,
            "payload": event,
        }).execute()
    except Exception:
        pass


def _mark_processed(sb, event_id, error: Optional[str] = None):
    if not event_id:
        return
    try:
        sb.table("stripe_webhook_events").update({
            "processed": error is None,
            "error_message": error,
            "processed_at": datetime.utcnow().isoformat(),
        }).eq("stripe_event_id", event_id).execute()
    except Exception:
        pass


def _unix_to_iso(value):
    if not value:
        return None
    try:
        return datetime.utcfromtimestamp(int(value)).isoformat()
    except Exception:
        return None


class _WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if urlparse(self.path).path not in ("/webhook", "/"):
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)
        sig = self.headers.get("Stripe-Signature")
        try:
            if config.STRIPE_WEBHOOK_SECRET and not config.STRIPE_WEBHOOK_SECRET.startswith("whsec_your"):
                event = stripe.Webhook.construct_event(payload, sig, config.STRIPE_WEBHOOK_SECRET)
            else:
                event = json.loads(payload)
            result = process_stripe_event(event)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(result.encode("utf-8"))
        except Exception as exc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(exc).encode("utf-8"))

    def log_message(self, format, *args):
        print("[stripe webhook]", format % args)


if __name__ == "__main__":
    port = 8787
    print(f"Stripe webhook listener on http://localhost:{port}/webhook")
    HTTPServer(("0.0.0.0", port), _WebhookHandler).serve_forever()
