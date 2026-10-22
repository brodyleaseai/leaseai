"""
Admin Dashboard for LeaseAI
Lease review, approval, and management interface for administrators.
"""
import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Admin Dashboard - LeaseAI",
    page_icon="📊",
    layout="wide",
)

# Load config
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    try:
        from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    except ImportError:
        st.error("No secrets configured. Add them to Streamlit Cloud or config.py.")
        st.stop()

from supabase import create_client
from auth_module import AuthManager

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
auth = AuthManager(sb)

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Check admin role
if st.session_state.get("user_role") != "admin":
    st.error("🚫 Admin access only. Please log in as an administrator.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 LeaseAI Admin Dashboard")
with col2:
    st.write(f"👤 {st.session_state.get('user_name', 'Admin')}")
    if st.button("Logout", use_container_width=True):
        auth.logout()
        st.switch_page("Home.py")

st.markdown("---")

# Dashboard Overview
st.subheader("📈 Platform Overview")

col1, col2, col3, col4 = st.columns(4)

from query_cache import cached

# Total leases
leases = cached("admin_leases_status", 45, lambda: (sb.table("leases").select("id, status").execute().data or []))
total_leases = len(leases)

# Pending review
pending = sum(1 for l in leases if (l.get("status") or "").upper() in ["READY FOR REVIEW", "PENDING"])

# Approved
approved = sum(1 for l in leases if (l.get("status") or "").upper() == "APPROVED")

# Flagged
flagged = sum(1 for l in leases if (l.get("status") or "").upper() == "FLAGGED")

with col1:
    st.metric("Total Leases", total_leases)
with col2:
    st.metric("Pending Review", pending, delta=None, delta_color="off")
with col3:
    st.metric("Approved", approved, delta=None, delta_color="normal")
with col4:
    st.metric("Flagged", flagged, delta=None, delta_color="inverse")

st.markdown("---")

# Recent Activity
st.subheader("📋 Recent Leases")

recent_leases_data = cached(
    "admin_recent_leases",
    30,
    lambda: (sb.table("leases").select("*, clients(name)").order("created_at", desc=True).limit(10).execute().data or []),
)

if recent_leases_data:
    for lease in recent_leases_data:
        col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])
        
        with col_a:
            st.markdown(f"**{lease.get('filename', 'Unknown')}**")
            client_name = (lease.get('clients') or {}).get('name', 'Unknown Client')
            st.caption(f"Client: {client_name}")
        
        with col_b:
            created_at = lease.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    st.write(dt.strftime("%b %d, %Y %I:%M %p"))
                except:
                    st.write(created_at[:10])
        
        with col_c:
            status = lease.get("status", "PENDING")
            if status == "APPROVED":
                st.success(f"✅ {status}")
            elif status == "FLAGGED":
                st.error(f"🚩 {status}")
            else:
                st.info(f"⏳ {status}")
        
        with col_d:
            if st.button("Review", key=f"review_{lease['id']}"):
                st.session_state["review_lease_id"] = lease["id"]
                st.switch_page("pages/2_📋_Lease_Review.py")
        
        st.divider()
else:
    st.info("No leases found.")

# Sales metrics
st.markdown("---")
st.subheader("Sales Metrics")
try:
    client_rows = cached(
        "admin_clients_billing",
        60,
        lambda: (sb.table("clients").select(
            "id, plan_tier, subscription_status, billing_interval, created_at"
        ).execute().data or []),
    )
    active = [c for c in client_rows if (c.get("subscription_status") or "") in ("active", "trialing")]
    plan_mrr = {"starter": 2500, "growth": 6000, "enterprise": 15000}
    mrr = 0
    for row in active:
        monthly = plan_mrr.get((row.get("plan_tier") or "").lower(), 0)
        if (row.get("billing_interval") or "") == "annual":
            monthly = int(monthly * 10 / 12)
        mrr += monthly
    from datetime import datetime as _dt
    start = _dt.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_month = 0
    for row in client_rows:
        created_at = row.get("created_at") or ""
        try:
            created_dt = _dt.fromisoformat(str(created_at).replace("Z", "+00:00")).replace(tzinfo=None)
            if created_dt >= start:
                new_month += 1
        except Exception:
            pass
    canceled = [c for c in client_rows if (c.get("subscription_status") or "") == "canceled"]
    churn = (len(canceled) / max(len(client_rows), 1)) * 100
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("MRR", f"${mrr:,.0f}")
    m2.metric("ARR", f"${mrr * 12:,.0f}")
    m3.metric("Active subscriptions", len(active))
    m4.metric("New clients this month", new_month)
    st.caption(f"Canceled share of all clients: {churn:.1f}%")
    if st.button("Open Billing"):
        st.switch_page("pages/15_💳_Billing.py")
except Exception:
    st.caption("Apply database_schema_billing.sql to see live MRR and ARR.")

# Quick Actions
st.markdown("---")
st.subheader("⚡ Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📤 Upload New Lease", use_container_width=True):
        st.switch_page("pages/1_📤_Upload_Lease.py")

with col2:
    if st.button("🔗 Amendment Graph", use_container_width=True):
        st.switch_page("pages/3_🔗_Amendment_Graph.py")

with col3:
    if st.button("📊 ASC 842 Compliance", use_container_width=True):
        st.switch_page("pages/5_📈_ASC842_Dashboard.py")
