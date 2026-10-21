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

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
auth = AuthManager(sb)
dates_manager = CriticalDatesManager(sb)

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Header
st.title("📅 Critical Dates Management")
st.markdown("Track and manage important lease dates with automated notifications")
st.markdown("---")

# Tab navigation
tab1, tab2, tab3 = st.tabs([
    "📋 Upcoming Dates",
    "➕ Add Critical Date",
    "🔔 Notification Settings"
])

with tab1:
    st.subheader("Upcoming Critical Dates")
    
    # Fetch all leases with critical dates
    try:
        critical_dates_response = sb.table("critical_dates").select("*, leases(filename, clients(name))").order("date_value").execute()
        critical_dates = critical_dates_response.data or []
        
        if critical_dates:
            # Filter by date range
            date_filter = st.radio("Show", ["All Dates", "Next 30 Days", "Next 60 Days", "Next 90 Days"], horizontal=True)
            
            today = datetime.now().date()
            
            if date_filter == "Next 30 Days":
                cutoff_date = today + timedelta(days=30)
                critical_dates = [d for d in critical_dates if datetime.fromisoformat(d['date_value'].replace("Z", "")).date() <= cutoff_date]
            elif date_filter == "Next 60 Days":
                cutoff_date = today + timedelta(days=60)
                critical_dates = [d for d in critical_dates if datetime.fromisoformat(d['date_value'].replace("Z", "")).date() <= cutoff_date]
            elif date_filter == "Next 90 Days":
                cutoff_date = today + timedelta(days=90)
                critical_dates = [d for d in critical_dates if datetime.fromisoformat(d['date_value'].replace("Z", "")).date() <= cutoff_date]
            
            st.markdown(f"**{len(critical_dates)} dates found**")
            st.markdown("---")
            
            for date_entry in critical_dates:
                date_value = datetime.fromisoformat(date_entry['date_value'].replace("Z", "")).date()
                days_until = (date_value - today).days
                
                lease_info = date_entry.get('leases', {})
                filename = lease_info.get('filename', 'Unknown')
                client_name = (lease_info.get('clients') or {}).get('name', 'Unknown')
                
                # Color code based on urgency
                if days_until < 0:
                    urgency_color = "🔴"
                    urgency_text = f"OVERDUE by {abs(days_until)} days"
                elif days_until <= 7:
                    urgency_color = "🔴"
                    urgency_text = f"{days_until} days"
                elif days_until <= 30:
                    urgency_color = "🟡"
                    urgency_text = f"{days_until} days"
                else:
                    urgency_color = "🟢"
                    urgency_text = f"{days_until} days"
                
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                
                with col1:
                    st.markdown(f"**{date_entry.get('date_type', 'Unknown')}**")
                    st.caption(f"{filename} - {client_name}")
                    if date_entry.get('description'):
                        st.caption(date_entry['description'])
                
                with col2:
                    st.write(f"📅 {date_value.strftime('%B %d, %Y')}")
                
                with col3:
                    st.markdown(f"{urgency_color} **{urgency_text}**")
                
                with col4:
                    if st.button("🗑️", key=f"delete_{date_entry['id']}"):
                        sb.table("critical_dates").delete().eq("id", date_entry['id']).execute()
                        st.rerun()
                
                st.divider()
        else:
            st.info("No critical dates found. Add one in the 'Add Critical Date' tab.")
    
    except Exception as e:
        st.info("Critical dates table not yet created. Add a critical date first.")

with tab2:
    st.subheader("Add New Critical Date")
    
    # Select lease
    leases_response = sb.table("leases").select("id, filename, clients(name)").execute()
    leases = leases_response.data or []
    
    if not leases:
        st.warning("No leases found. Upload a lease first.")
    else:
        lease_options = {
            f"{l.get('filename', 'Unknown')} - {(l.get('clients') or {}).get('name', 'Unknown')}": l['id']
            for l in leases
        }
        
        selected_lease_label = st.selectbox("Select Lease", list(lease_options.keys()))
        selected_lease_id = lease_options[selected_lease_label]
        
        col1, col2 = st.columns(2)
        
        with col1:
            date_type = st.selectbox("Date Type", dates_manager.DATE_TYPES)
            date_value = st.date_input("Date")
        
        with col2:
            description = st.text_area("Description (optional)", height=100)
            notification_days = st.multiselect(
                "Send Notifications (days before)",
                [1, 7, 14, 30, 60, 90],
                default=[30, 7, 1]
            )
        
        if st.button("➕ Add Critical Date", type="primary", use_container_width=True):
            try:
                # Add to database
                date_data = {
                    "lease_id": selected_lease_id,
                    "date_type": date_type,
                    "date_value": date_value.isoformat(),
                    "description": description if description else None,
                    "notification_intervals": notification_days,
                    "created_at": datetime.now().isoformat()
                }
                
                sb.table("critical_dates").insert(date_data).execute()
                
                st.success(f"✅ Critical date added: {date_type} on {date_value.strftime('%B %d, %Y')}")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error adding critical date: {str(e)}")

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
