"""
LeaseAI Billing: subscribe, manage plan, usage meter, invoices.
"""

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from supabase import create_client

sys.path.append(str(Path(__file__).parent.parent))

import config
from payment_integration import PaymentHandler, get_client_billing
from usage_limits import check_can_upload, current_year_month

st.set_page_config(page_title="Billing - LeaseAI", page_icon="💳", layout="wide")

if not st.session_state.get("authenticated", False):
    st.warning("Please log in from the Home page first.")
    if st.button("Go to Home"):
        st.switch_page("Home.py")
    st.stop()

try:
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
except Exception as exc:
    st.error(f"Database connection failed: {exc}")
    st.stop()

handler = PaymentHandler(sb)
user_role = st.session_state.get("user_role", "user")
user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id")

# Admin may bill a selected client; clients bill themselves
client_id = user_id
if user_role == "admin":
    try:
        clients = sb.table("clients").select("id, email, name, company_name").execute().data or []
    except Exception:
        clients = []
    if clients:
        labels = {}
        for row in clients:
            label = row.get("company_name") or row.get("name") or row.get("email") or row["id"]
            labels[f"{label} ({row.get('email') or 'no email'})"] = row["id"]
        picked = st.sidebar.selectbox("Bill this client", list(labels.keys()))
        client_id = labels[picked]
    st.sidebar.caption("Admins can subscribe or manage billing for any client.")

if handler.is_configured():
    try:
        lookup_email = user_email
        if user_role == "admin" and client_id:
            try:
                row = sb.table("clients").select("email").eq("id", client_id).limit(1).execute()
                if row.data:
                    lookup_email = row.data[0].get("email") or user_email
            except Exception:
                pass
        handler.sync_subscription_from_stripe(client_id, email=lookup_email)
    except Exception as exc:
        st.caption(f"Could not refresh plan from Stripe: {exc}")

billing = get_client_billing(sb, client_id)
allowed, usage_msg, usage = check_can_upload(sb, client_id, user_role)

payment_status = None
try:
    payment_status = st.query_params.get("payment")
except Exception:
    payment_status = None

st.title("Billing & Subscription")
st.caption("Starter $2,500/mo · Growth $6,000/mo · Enterprise $15,000/mo · Annual saves 2 months")

if payment_status == "success":
    st.success("Checkout completed. Stripe will activate the subscription in a few seconds. Refresh this page.")
elif payment_status == "cancelled":
    st.warning("Checkout cancelled. No charge was made.")

if not handler.is_configured():
    st.info(
        "Stripe keys are still placeholders. Add STRIPE_SECRET_KEY to your .env or Streamlit secrets, "
        "then restart the app. You can still review plans and usage below."
    )

tab1, tab2, tab3 = st.tabs(["Current plan", "Subscribe / change plan", "Invoices"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Plan", (billing.get("plan_tier") or "none").title())
    col2.metric("Status", (billing.get("subscription_status") or "none").replace("_", " ").title())
    col3.metric("Interval", (billing.get("billing_interval") or "—").title())
    period_end = billing.get("current_period_end") or "—"
    col4.metric("Renews / ends", str(period_end)[:10] if period_end != "—" else "—")

    st.markdown("### Usage this month")
    limit = usage.get("limit")
    used = usage.get("used") or 0
    if limit is None:
        st.progress(0)
        st.write(f"{used} leases processed · unlimited")
    else:
        pct = min(used / limit, 1.0) if limit else 0
        st.progress(pct)
        st.write(f"{used} / {limit} lease abstractions ({usage_msg})")
        if not allowed:
            st.error(usage_msg)

    if billing.get("cancel_at_period_end"):
        st.warning("Cancellation is scheduled at the end of the current period. Data is retained for 30 days.")

    if billing.get("failed_payment_count"):
        st.error(f"Failed payment attempts: {billing.get('failed_payment_count')}")

    st.markdown("### Manage payment method")
    if billing.get("stripe_customer_id") and handler.is_configured():
        if st.button("Open Stripe customer portal", type="primary"):
            try:
                portal = handler.create_billing_portal_session(
                    billing["stripe_customer_id"],
                    return_url=f"{config.APP_URL}",
                )
                st.link_button("Continue to Stripe portal", portal)
            except Exception as exc:
                st.error(f"Could not open portal: {exc}")
                st.caption("Enable the Stripe Customer Portal in the Stripe Dashboard under Settings → Billing → Customer portal.")
    else:
        st.caption("Subscribe first to manage cards and invoices in Stripe.")

    if billing.get("stripe_subscription_id") and billing.get("subscription_status") in ("active", "trialing", "past_due"):
        if st.button("Cancel at period end"):
            try:
                handler.cancel_subscription(billing["stripe_subscription_id"], immediately=False)
                sb.table("clients").update({
                    "cancel_at_period_end": True,
                    "subscription_updated_at": datetime.utcnow().isoformat(),
                }).eq("id", client_id).execute()
                st.success("Subscription will end at the current period close. Data stays available for 30 days.")
                st.rerun()
            except Exception as exc:
                st.error(f"Cancel failed: {exc}")

with tab2:
    st.markdown("### Choose a plan")
    interval = st.radio("Billing frequency", ["monthly", "annual"], horizontal=True)
    cols = st.columns(3)
    for col, key in zip(cols, ("starter", "growth", "enterprise")):
        plan = PaymentHandler.PLANS[key]
        amount = plan["annual_amount"] if interval == "annual" else plan["monthly_amount"]
        dollars = amount / 100
        period = "/ year" if interval == "annual" else "/ month"
        with col:
            st.subheader(plan["name"])
            st.markdown(f"**${dollars:,.0f}** {period}")
            st.caption(plan["description"])
            if interval == "annual":
                st.caption("Includes 2 months free")
            current = (billing.get("plan_tier") == key and billing.get("subscription_status") in ("active", "trialing"))
            label = "Current plan" if current and billing.get("billing_interval") == interval else f"Choose {plan['name']}"
            if st.button(label, key=f"buy_{key}_{interval}", disabled=current and billing.get("billing_interval") == interval, use_container_width=True):
                if not handler.is_configured():
                    st.error("Add a real STRIPE_SECRET_KEY before checkout.")
                elif not user_email and user_role != "admin":
                    st.error("Your account needs an email address.")
                else:
                    email = user_email
                    if user_role == "admin":
                        try:
                            row = sb.table("clients").select("email").eq("id", client_id).limit(1).execute()
                            email = (row.data[0].get("email") if row.data else None) or user_email
                        except Exception:
                            email = user_email
                    try:
                        if billing.get("stripe_subscription_id") and billing.get("subscription_status") in ("active", "trialing", "past_due"):
                            handler.change_plan(billing["stripe_subscription_id"], key, interval)
                            sb.table("clients").update({
                                "plan_tier": key,
                                "billing_interval": interval,
                                "subscription_updated_at": datetime.utcnow().isoformat(),
                            }).eq("id", client_id).execute()
                            st.success(f"Plan updated to {plan['name']} ({interval}). Stripe will prorate the difference.")
                            st.rerun()
                        else:
                            url = handler.create_checkout_session(
                                plan_type=key,
                                client_email=email,
                                billing_interval=interval,
                                client_id=client_id,
                                success_url=f"{config.APP_URL}/?payment=success",
                                cancel_url=f"{config.APP_URL}/?payment=cancelled",
                            )
                            st.session_state["stripe_checkout_url"] = url
                    except Exception as exc:
                        st.error(f"Checkout failed: {exc}")

    if st.session_state.get("stripe_checkout_url"):
        st.link_button("Continue to Stripe Checkout", st.session_state["stripe_checkout_url"], type="primary")

with tab3:
    st.markdown("### Billing history")
    invoices = []
    try:
        local = (
            sb.table("billing_invoices")
            .select("*")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        invoices = local.data or []
    except Exception:
        invoices = []

    if not invoices and billing.get("stripe_customer_id") and handler.is_configured():
        try:
            invoices = []
            for inv in handler.list_invoices(billing["stripe_customer_id"]):
                data = inv.to_dict() if hasattr(inv, "to_dict") else dict(inv)
                invoices.append({
                    "stripe_invoice_id": data.get("id"),
                    "amount_paid_cents": data.get("amount_paid"),
                    "status": data.get("status"),
                    "hosted_invoice_url": data.get("hosted_invoice_url"),
                    "created_at": datetime.utcfromtimestamp(data.get("created") or 0).isoformat(),
                })
        except Exception as exc:
            st.caption(f"Could not load Stripe invoices: {exc}")

    if not invoices:
        st.info("No invoices yet.")
    else:
        for inv in invoices:
            amount = (inv.get("amount_paid_cents") or 0) / 100
            url = inv.get("hosted_invoice_url")
            line = f"{str(inv.get('created_at') or '')[:10]}  ·  ${amount:,.2f}  ·  {inv.get('status')}"
            if url:
                st.markdown(f"{line}  ·  [View]({url})")
            else:
                st.write(line)

st.caption(f"Usage period {current_year_month()} · Stripe test keys are fine until you go live")
