"""
Delete one or more leases. Plain filename so Windows can download it reliably.
"""
import sys
import os
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Delete Leases | LeaseAI", page_icon="🗑️", layout="wide")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

from supabase import create_client
from auth_module import AuthManager
from lease_delete import delete_leases

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
auth = AuthManager(sb)

if not st.session_state.get("authenticated", False):
    st.warning("Please log in from the Home page first.")
    if st.button("Go to Home"):
        st.switch_page("Home.py")
    st.stop()

role = (st.session_state.get("user_role") or "").lower()
if role not in ("admin", "administrator", "owner", ""):
    st.error("Only administrators can delete leases.")
    if st.button("Go to Home"):
        st.switch_page("Home.py")
    st.stop()

st.title("🗑️ Delete Leases")
st.caption("Permanently remove leases and their extracted fields. This cannot be undone.")

leases = (
    sb.table("leases")
    .select("id, filename, tenant_name, property_address, status, created_at, clients(name)")
    .order("created_at", desc=True)
    .execute()
    .data
    or []
)

if not leases:
    st.info("There are no leases to delete.")
    st.stop()

def _label(lease):
    name = lease.get("filename") or "Lease"
    tenant = lease.get("tenant_name") or (lease.get("clients") or {}).get("name") or ""
    address = lease.get("property_address") or ""
    status = lease.get("status") or ""
    created = (lease.get("created_at") or "")[:10]
    return f"{name} | {tenant} | {address} | {status} | {created} | {lease['id']}"

choices = {_label(lease): lease["id"] for lease in leases}

selected_labels = st.multiselect(
    "Select leases to delete",
    options=list(choices.keys()),
    help="You can select one lease or several at the same time.",
)
selected_ids = [choices[label] for label in selected_labels]

st.write(f"**{len(selected_ids)}** lease(s) selected out of {len(leases)}.")

if selected_ids:
    st.dataframe(
        [
            {
                "File": next((l.get("filename") for l in leases if l["id"] == lid), ""),
                "Tenant": next((l.get("tenant_name") for l in leases if l["id"] == lid), ""),
                "Property": next((l.get("property_address") for l in leases if l["id"] == lid), ""),
                "Status": next((l.get("status") for l in leases if l["id"] == lid), ""),
            }
            for lid in selected_ids
        ],
        use_container_width=True,
        hide_index=True,
    )

confirm = st.checkbox("I understand this permanently deletes the selected leases")

if st.button("🗑️ Delete selected leases", type="primary", disabled=not (selected_ids and confirm)):
    deleted = delete_leases(sb, selected_ids)
    st.success(f"Deleted {deleted} lease(s) at {datetime.now().strftime('%I:%M %p')}.")
    st.rerun()

if st.button("Back to Home"):
    st.switch_page("Home.py")
