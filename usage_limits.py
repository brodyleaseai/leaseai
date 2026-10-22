"""
LeaseAI monthly abstraction usage limits.
Starter 50 / Growth 200 / Enterprise unlimited / no plan trial 3.
Admins are never blocked.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from payment_integration import PaymentHandler, get_client_billing

TRIAL_LIMIT = 3


def current_year_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def plan_limit(plan_tier: str, subscription_status: str) -> Optional[int]:
    status = (subscription_status or "none").lower()
    tier = (plan_tier or "none").lower()
    if status not in ("active", "trialing"):
        return TRIAL_LIMIT
    plan = PaymentHandler.PLANS.get(tier)
    if not plan:
        return TRIAL_LIMIT
    return plan.get("lease_limit")


def get_usage(supabase_client, client_id: str, year_month: Optional[str] = None) -> int:
    if not client_id:
        return 0
    month = year_month or current_year_month()
    try:
        result = (
            supabase_client.table("usage_monthly")
            .select("lease_count")
            .eq("client_id", client_id)
            .eq("year_month", month)
            .limit(1)
            .execute()
        )
        if result.data:
            return int(result.data[0].get("lease_count") or 0)
    except Exception:
        pass
    return 0


def increment_usage(supabase_client, client_id: str) -> int:
    if not client_id:
        return 0
    month = current_year_month()
    used = get_usage(supabase_client, client_id, month)
    new_count = used + 1
    payload = {
        "client_id": client_id,
        "year_month": month,
        "lease_count": new_count,
        "last_upload_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        existing = (
            supabase_client.table("usage_monthly")
            .select("id")
            .eq("client_id", client_id)
            .eq("year_month", month)
            .limit(1)
            .execute()
        )
        if existing.data:
            supabase_client.table("usage_monthly").update(payload).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            payload["created_at"] = datetime.utcnow().isoformat()
            supabase_client.table("usage_monthly").insert(payload).execute()
    except Exception:
        pass
    return new_count


def check_can_upload(
    supabase_client,
    client_id: Optional[str],
    user_role: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Returns (allowed, message, usage_info).
    Admins always allowed.
    """
    if (user_role or "").lower() == "admin":
        return True, "Admin accounts have unlimited abstractions.", {
            "used": 0,
            "limit": None,
            "remaining": None,
            "plan_tier": "admin",
        }

    billing = get_client_billing(supabase_client, client_id) if client_id else {}
    tier = billing.get("plan_tier") or "none"
    status = billing.get("subscription_status") or "none"
    limit = plan_limit(tier, status)
    used = get_usage(supabase_client, client_id) if client_id else 0
    remaining = None if limit is None else max(limit - used, 0)

    info = {
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "plan_tier": tier,
        "subscription_status": status,
    }

    if limit is None:
        return True, "Enterprise plan: unlimited abstractions.", info

    if used >= limit:
        if status not in ("active", "trialing"):
            return False, (
                f"Trial limit reached ({used}/{limit} leases this month). "
                "Subscribe on the Billing page to continue."
            ), info
        return False, (
            f"Monthly limit reached ({used}/{limit} leases on the {tier.title()} plan). "
            "Upgrade on the Billing page or wait until next month."
        ), info

    return True, f"{used}/{limit} leases used this month.", info
