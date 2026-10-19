"""
LeaseAI - Lease Comparison Page
Compare two leases side-by-side
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Compare Leases | LeaseAI",
    page_icon="🔍",
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
        st.error("No secrets configured.")
        st.stop()

from supabase import create_client
from lease_comparison import render_comparison_view

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Custom CSS
st.markdown("""
<style>
    .comparison-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="comparison-header">
    <h1>🔍 Compare Leases</h1>
    <p>Identify differences between two lease agreements</p>
</div>
""", unsafe_allow_html=True)

# Fetch all leases
leases_response = sb.table("leases").select("*, clients(name)").order("created_at", desc=True).execute()
leases = leases_response.data or []

if len(leases) < 2:
    st.warning("⚠️ You need at least 2 leases to perform a comparison.")
    st.info("💡 Upload more leases to enable comparison features.")
    
    if st.button("📤 Upload Lease", type="primary"):
        st.switch_page("pages/1_📤_Upload_Lease.py")
    
    st.stop()

# Lease selection
st.subheader("📋 Select Leases to Compare")

col1, col2 = st.columns(2)

# Build lease options
lease_options = {
    f"{l.get('filename', 'Lease')} — {(l.get('clients') or {}).get('name', '')}": l['id']
    for l in leases
}

with col1:
    st.markdown("**Lease A**")
    selected_a_label = st.selectbox(
        "Select first lease",
        list(lease_options.keys()),
        key="lease_a",
        label_visibility="collapsed"
    )
    lease_a_id = lease_options[selected_a_label]

with col2:
    st.markdown("**Lease B**")
    # Filter out Lease A from options
    lease_b_options = {k: v for k, v in lease_options.items() if v != lease_a_id}
    
    if not lease_b_options:
        st.error("No other leases available for comparison")
        st.stop()
    
    selected_b_label = st.selectbox(
        "Select second lease",
        list(lease_b_options.keys()),
        key="lease_b",
        label_visibility="collapsed"
    )
    lease_b_id = lease_b_options[selected_b_label]

# Fetch lease data
lease_a_response = sb.table("leases").select("*").eq("id", lease_a_id).single().execute()
lease_a = lease_a_response.data

lease_b_response = sb.table("leases").select("*").eq("id", lease_b_id).single().execute()
lease_b = lease_b_response.data

# Fetch fields
fields_a_response = sb.table("extracted_fields").select("*").eq("lease_id", lease_a_id).order("field_number").execute()
fields_a = fields_a_response.data or []

fields_b_response = sb.table("extracted_fields").select("*").eq("lease_id", lease_b_id).order("field_number").execute()
fields_b = fields_b_response.data or []

st.markdown("---")

# Render comparison
if lease_a and lease_b and fields_a and fields_b:
    render_comparison_view(lease_a, fields_a, lease_b, fields_b, sb)
else:
    st.error("❌ Could not load lease data for comparison.")

# Back button
st.markdown("---")
if st.button("← Back to Dashboard"):
    st.switch_page("Home.py")
