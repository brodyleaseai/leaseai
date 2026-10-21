"""
Enhanced Client Portal for LeaseAI
Client-facing interface with file upload and extraction integration.
"""
import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Client Portal - LeaseAI",
    page_icon="👥",
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
        st.switch_page("app.py")
    st.stop()

# Allow both admins and clients to access
user_role = st.session_state.get("user_role")
if user_role not in ["client", "admin"]:
    st.error("🚫 Access denied. Client or admin access required.")
    if st.button("← Go to Home"):
        st.switch_page("app.py")
    st.stop()

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("👥 LeaseAI Client Portal")
    st.caption("Upload leases, track processing, and download abstracts")
with col2:
    st.write(f"👤 {st.session_state.get('user_name', 'Client')}")
    if st.button("Logout", use_container_width=True):
        auth.logout()
        st.switch_page("app.py")

st.markdown("---")

# Dashboard Overview
st.subheader("📊 Your Lease Dashboard")

# Get client_id based on role
user_role = st.session_state.get("user_role")
if user_role == "admin":
    # Admins see all leases
    leases_response = sb.table("leases").select("id, filename, status, created_at, page_count").order("created_at", desc=True).execute()
    export_history_response = sb.table("export_history").select("*").order("exported_at", desc=True).limit(10).execute()
else:
    # Clients see only their leases
    client_id = st.session_state.get("user_id")
    leases_response = sb.table("leases").select("id, filename, status, created_at, page_count").eq("client_id", client_id).order("created_at", desc=True).execute()
    export_history_response = sb.table("export_history").select("*").eq("user_id", client_id).order("exported_at", desc=True).limit(10).execute()

leases = leases_response.data or []
export_history = export_history_response.data or []

total_leases = len(leases)
pending = sum(1 for l in leases if (l.get("status") or "").upper() in ["READY FOR REVIEW", "PENDING"])
approved = sum(1 for l in leases if (l.get("status") or "").upper() == "APPROVED")
total_exports = len(export_history)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Leases", total_leases)
with col2:
    st.metric("In Review", pending)
with col3:
    st.metric("Approved", approved)
with col4:
    st.metric("Exports", total_exports)

st.markdown("---")

# My Leases
st.subheader("📋 My Leases")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📋 All Leases", "📥 Export History", "🔍 Compare"])

with tab1:
    if leases:
        for lease in leases:
            col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])
            
            with col_a:
                st.markdown(f"**{lease.get('filename', 'Unknown')}**")
                st.caption(f"{lease.get('page_count', '?')} pages")
            
            with col_b:
                created_at = lease.get("created_at", "")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        st.write(dt.strftime("%b %d, %Y"))
                    except:
                        st.write(created_at[:10])
            
            with col_c:
                status = lease.get("status", "PENDING")
                if status == "APPROVED":
                    st.success(f"✅ {status}")
                elif status == "FLAGGED":
                    st.warning(f"⚠️ {status}")
                else:
                    st.info(f"⏳ {status}")
            
            with col_d:
                if st.button("View", key=f"view_{lease['id']}"):
                    st.session_state["review_lease_id"] = lease["id"]
                    st.session_state["review_page"] = "🔍 Review a Lease"  # Go directly to review page
                    st.switch_page("pages/2_📋_Lease_Review.py")
            
            st.divider()
    else:
        st.info("No leases uploaded yet. Use the 'Upload Lease' page to get started.")
        if st.button("📤 Upload Your First Lease", use_container_width=True):
            st.switch_page("pages/1_📤_Upload_Lease.py")

with tab2:
    # Export History
    st.subheader("📥 Recent Exports")
    
    if export_history:
        for export in export_history:
            col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])
            
            with col_a:
                export_type = export.get("export_type", "UNKNOWN")
                icon = {
                    "PDF_REPORT": "📄",
                    "YARDI_CSV": "📊",
                    "MRI_CSV": "📊",
                    "ASC842_REPORT": "📈"
                }.get(export_type, "📁")
                st.markdown(f"{icon} **{export_type.replace('_', ' ').title()}**")
            
            with col_b:
                exported_at = export.get("exported_at", "")
                if exported_at:
                    try:
                        dt = datetime.fromisoformat(exported_at.replace("Z", "+00:00"))
                        st.caption(dt.strftime("%b %d, %I:%M %p"))
                    except:
                        st.caption(exported_at[:16])
            
            with col_c:
                file_size = export.get("file_size_bytes", 0)
                if file_size:
                    size_kb = file_size / 1024
                    st.caption(f"{size_kb:.1f} KB")
            
            with col_d:
                lease_id = export.get("lease_id")
                if lease_id and st.button("View", key=f"export_{export['id']}"):
                    st.session_state["review_lease_id"] = lease_id
                    st.session_state["review_page"] = "🔍 Review a Lease"  # Go directly to review page
                    st.switch_page("pages/2_📋_Lease_Review.py")
            
            st.divider()
    else:
        st.info("No exports yet. Generate a PDF or CSV export from the Lease Review page.")

with tab3:
    # Lease Comparison
    st.subheader("🔍 Compare Leases")
    
    if len(leases) >= 2:
        st.info("💡 Select two leases to compare side-by-side and identify differences.")
        if st.button("🔍 Go to Comparison Tool", use_container_width=True, type="primary"):
            st.switch_page("pages/8_🔍_Compare_Leases.py")
    else:
        st.warning("⚠️ You need at least 2 leases to use the comparison tool.")
        st.caption("Upload more leases to enable this feature.")

# Quick Actions
st.markdown("---")
st.subheader("⚡ Quick Actions")

col1, col2 = st.columns(2)

with col1:
    if st.button("📤 Upload New Lease", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📤_Upload_Lease.py")

with col2:
    if st.button("📋 View All Leases", use_container_width=True):
        st.switch_page("pages/2_📋_Lease_Review.py")

# Help & Support
st.markdown("---")
st.subheader("❓ Help & Support")

with st.expander("📖 How to Use LeaseAI"):
    st.markdown("""
    ### Getting Started
    
    1. **Upload a Lease** - Click "Upload New Lease" and select your PDF lease document
    2. **AI Processing** - Our AI extracts all key fields automatically (20-40 seconds)
    3. **Review** - Check the extracted data in "My Leases"
    4. **Download** - Get your completed lease abstract
    
    ### What We Extract
    
    LeaseAI automatically extracts 84+ fields including:
    - Tenant and landlord information
    - Lease dates and terms
    - Rent and payment details
    - Square footage and property details
    - Options and special provisions
    - Critical dates and deadlines
    
    ### Need Help?
    
    Contact our support team at support@leaseai.com
    """)

with st.expander("💰 Billing Information"):
    st.markdown("""
    ### Current Plan
    
    **Professional Plan** - $99/month
    - Unlimited lease uploads
    - 84-field extraction
    - Amendment tracking
    - ASC 842 compliance calculations
    - Priority support
    
    ### Billing History
    
    *Billing integration coming soon*
    """)
