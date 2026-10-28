"""
Critical Dates Management System for LeaseAI
Tracks and sends notifications for important lease dates.
"""
import streamlit as st
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Critical Dates - LeaseAI",
    page_icon="📅",
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
from critical_dates import CriticalDatesManager
from critical_date_extract import critical_dates_from_fields, records_for_database

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
auth = AuthManager(sb)
dates_manager = CriticalDatesManager(sb)

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

st.title("📅 Critical Dates Management")
st.markdown("Select a lease to see dates extracted from that abstract, then track upcoming deadlines.")
st.markdown("---")


def lease_label(lease):
    property_name = lease.get("property_address") or lease.get("filename") or "Unknown"
    tenant = lease.get("tenant_name") or "Unknown tenant"
    return f"{property_name} — {tenant} ({str(lease['id'])[:8]})"


def load_extracted_fields(lease_id):
    try:
        response = sb.table("extracted_fields").select("*").eq("lease_id", lease_id).execute()
        return response.data or []
    except Exception:
        return []


def existing_date_keys(lease_id):
    try:
        response = sb.table("critical_dates").select("date_type, date_value").eq("lease_id", lease_id).execute()
        return {(row.get("date_type"), row.get("date_value")) for row in (response.data or [])}
    except Exception:
        return set()


leases_response = sb.table("leases").select("id, filename, property_address, tenant_name, clients(name)").execute()
leases = leases_response.data or []
lease_options = {"All leases": None}
for lease in leases:
    lease_options[lease_label(lease)] = lease["id"]

selected_lease_label = st.selectbox("Select lease", list(lease_options.keys()), key="critical_dates_selected_lease")
selected_lease_id = lease_options[selected_lease_label]

tab1, tab2, tab3 = st.tabs([
    "📋 Lease Dates",
    "➕ Add Critical Date",
    "🔔 Notification Settings"
])

with tab1:
    today = datetime.now().date()

    if selected_lease_id:
        extracted_rows = load_extracted_fields(selected_lease_id)
        extracted_dates = critical_dates_from_fields(extracted_rows)
        st.subheader("Extracted from this lease")
        if extracted_dates:
            st.dataframe(
                [
                    {
                        "Date type": row["date_type"],
                        "Date": row["date_value"],
                        "Source": row.get("description") or row.get("source_field"),
                    }
                    for row in extracted_dates
                ],
                use_container_width=True,
                hide_index=True,
            )
            if st.button("💾 Save extracted dates to tracker", type="primary", key=f"save_extracted_{selected_lease_id}"):
                already = existing_date_keys(selected_lease_id)
                added = 0
                for record in records_for_database(selected_lease_id, extracted_dates):
                    if (record["date_type"], record["date_value"]) in already:
                        continue
                    try:
                        sb.table("critical_dates").insert(record).execute()
                        added += 1
                    except Exception as error:
                        st.error(f"Could not save {record['date_type']}: {error}")
                if added:
                    st.success(f"Saved {added} extracted date(s) to the tracker.")
                    st.rerun()
                else:
                    st.info("Those extracted dates are already in the tracker.")
        else:
            st.warning("No calendar critical dates could be resolved from this lease’s extracted fields. Review the abstract or add a date manually.")

        st.markdown("---")
        st.subheader("Saved tracker dates for this lease")
        try:
            saved = dates_manager.get_dates_by_lease(selected_lease_id)
        except Exception:
            saved = []
        if saved:
            for date_entry in saved:
                date_value = datetime.fromisoformat(str(date_entry["date_value"]).replace("Z", "")).date()
                days_until = (date_value - today).days
                if days_until < 0:
                    urgency = f"🔴 OVERDUE by {abs(days_until)} days"
                elif days_until <= 30:
                    urgency = f"🟡 {days_until} days"
                else:
                    urgency = f"🟢 {days_until} days"
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{date_entry.get('date_type', 'Unknown')}**")
                    if date_entry.get("description"):
                        st.caption(date_entry["description"])
                with col2:
                    st.write(f"📅 {date_value.strftime('%B %d, %Y')}")
                with col3:
                    st.markdown(f"**{urgency}**")
                with col4:
                    if st.button("🗑️", key=f"delete_{date_entry['id']}"):
                        sb.table("critical_dates").delete().eq("id", date_entry["id"]).execute()
                        st.rerun()
                st.divider()
        else:
            st.caption("Nothing saved to the tracker yet for this lease.")
    else:
        st.subheader("Upcoming Critical Dates")
        try:
            from query_cache import cached
            critical_dates = cached(
                "critical_dates_all",
                45,
                lambda: (sb.table("critical_dates").select("*, leases(filename, property_address, tenant_name, clients(name))").order("date_value").execute().data or []),
            )
        except Exception:
            critical_dates = []

        if critical_dates:
            date_filter = st.radio("Show", ["All Dates", "Next 30 Days", "Next 60 Days", "Next 90 Days"], horizontal=True)
            if date_filter != "All Dates":
                days = int(date_filter.split()[1])
                cutoff_date = today + timedelta(days=days)
                critical_dates = [
                    row for row in critical_dates
                    if datetime.fromisoformat(str(row["date_value"]).replace("Z", "")).date() <= cutoff_date
                ]
            st.markdown(f"**{len(critical_dates)} dates found**")
            st.markdown("---")
            for date_entry in critical_dates:
                date_value = datetime.fromisoformat(str(date_entry["date_value"]).replace("Z", "")).date()
                days_until = (date_value - today).days
                lease_info = date_entry.get("leases") or {}
                label = lease_info.get("property_address") or lease_info.get("filename") or "Unknown"
                tenant = lease_info.get("tenant_name") or (lease_info.get("clients") or {}).get("name") or ""
                if days_until < 0:
                    urgency = f"🔴 OVERDUE by {abs(days_until)} days"
                elif days_until <= 30:
                    urgency = f"🟡 {days_until} days"
                else:
                    urgency = f"🟢 {days_until} days"
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{date_entry.get('date_type', 'Unknown')}**")
                    st.caption(f"{label} — {tenant}")
                    if date_entry.get("description"):
                        st.caption(date_entry["description"])
                with col2:
                    st.write(f"📅 {date_value.strftime('%B %d, %Y')}")
                with col3:
                    st.markdown(f"**{urgency}**")
                with col4:
                    if st.button("🗑️", key=f"delete_{date_entry['id']}"):
                        sb.table("critical_dates").delete().eq("id", date_entry["id"]).execute()
                        st.rerun()
                st.divider()
        else:
            st.info("No critical dates found. Select a lease to load extracted dates, or add one manually.")

with tab2:
    st.subheader("Add New Critical Date")
    if not leases:
        st.warning("No leases found. Upload a lease first.")
    else:
        add_options = {label: lease_id for label, lease_id in lease_options.items() if lease_id}
        default_index = 0
        if selected_lease_id:
            labels = list(add_options.keys())
            for index, label in enumerate(labels):
                if add_options[label] == selected_lease_id:
                    default_index = index
                    break
        add_label = st.selectbox("Lease", list(add_options.keys()), index=default_index, key="critical_dates_add_lease")
        add_lease_id = add_options[add_label]
        extracted_dates = critical_dates_from_fields(load_extracted_fields(add_lease_id))
        if extracted_dates:
            st.caption("Extracted dates for this lease (save them from the Lease Dates tab, or add another date below).")
            st.dataframe(
                [{"Date type": row["date_type"], "Date": row["date_value"]} for row in extracted_dates],
                use_container_width=True,
                hide_index=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            date_type = st.selectbox("Date Type", dates_manager.DATE_TYPES)
            date_value = st.date_input("Date")
        with col2:
            description = st.text_area("Description (optional)", height=100)
            notification_days = st.multiselect(
                "Send Notifications (days before)",
                [1, 7, 14, 30, 60, 90],
                default=[30, 7, 1],
            )

        if st.button("➕ Add Critical Date", type="primary", use_container_width=True):
            try:
                sb.table("critical_dates").insert({
                    "lease_id": add_lease_id,
                    "date_type": date_type,
                    "date_value": date_value.isoformat(),
                    "description": description or None,
                    "notification_intervals": notification_days,
                    "created_at": datetime.now().isoformat(),
                }).execute()
                st.success(f"Critical date added: {date_type} on {date_value.strftime('%B %d, %Y')}")
                st.rerun()
            except Exception as error:
                st.error(f"Error adding critical date: {error}")

with tab3:
    st.subheader("🔔 Notification Settings")
    st.markdown("""
    ### Automatic Email Notifications

    LeaseAI can automatically send email notifications for upcoming critical dates.

    **Default Notification Schedule:**
    - 90 days before
    - 60 days before
    - 30 days before
    - 14 days before
    - 7 days before
    - 1 day before

    **Notification Recipients:**
    - Lease owner (client email)
    - Assigned reviewers
    - Admin users (configurable)
    """)
    st.info("Email notification settings will be configured in a future update.")
