import streamlit as st
import sys
import os
from datetime import datetime
import json

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LeaseAI CAM Reconciliation",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── load config ───────────────────────────────────────────────────────────────
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
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── custom css ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f1117; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .leaseai-header {
        background: linear-gradient(90deg, #1a1f2e 0%, #2d3561 100%);
        border-radius: 10px;
        padding: 18px 28px;
        margin-bottom: 24px;
    }
    .leaseai-header h1 { color: #ffffff; margin: 0; font-size: 1.6rem; }
    .leaseai-header span { color: #8892b0; font-size: 0.9rem; }
    .metric-card {
        background: #1a1f2e;
        border: 1px solid #2d3561;
        border-radius: 10px;
        padding: 18px 22px;
        text-align: center;
    }
    .metric-card .val { font-size: 2rem; font-weight: 700; color: #64b5f6; }
    .metric-card .lbl { font-size: 0.8rem; color: #8892b0; margin-top: 4px; }
    .variance-positive { color: #4ade80; font-weight: 600; }
    .variance-negative { color: #f87171; font-weight: 600; }
    .severity-minor { color: #4ade80; }
    .severity-moderate { color: #fbbf24; }
    .severity-major { color: #fb923c; }
    .severity-critical { color: #f87171; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_all_leases():
    """Fetch all leases from database"""
    res = sb.table("leases").select("*, clients(name)").order("created_at", desc=True).execute()
    return res.data or []

def fetch_cam_provisions(lease_id):
    """Fetch CAM provisions for a lease"""
    res = sb.table("cam_provisions").select("*").eq("lease_id", lease_id).execute()
    return res.data[0] if res.data else None

def fetch_cam_reconciliations(lease_id=None):
    """Fetch CAM reconciliations, optionally filtered by lease"""
    query = sb.table("cam_reconciliations").select("*, leases(property_address, tenant_name)")
    if lease_id:
        query = query.eq("lease_id", lease_id)
    res = query.order("reconciliation_year", desc=True).execute()
    return res.data or []

def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "N/A"
    return f"${amount:,.2f}"

def get_severity_badge(severity):
    """Return colored badge for severity"""
    if not severity:
        return ""
    
    colors = {
        'MINOR': 'severity-minor',
        'MODERATE': 'severity-moderate',
        'MAJOR': 'severity-major',
        'CRITICAL': 'severity-critical'
    }
    
    color_class = colors.get(severity, 'severity-minor')
    return f'<span class="{color_class}">{severity}</span>'

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="leaseai-header">
    <div>
        <h1>💵 CAM Reconciliation</h1>
        <span>Common Area Maintenance charge verification and dispute management</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 New Reconciliation", "📋 History"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("### CAM Reconciliation Overview")
    
    # Show success message if just saved
    if st.session_state.get('last_reconciliation_saved'):
        st.success("✅ Reconciliation saved successfully! Dashboard metrics updated below.")
        # Clear the flag
        del st.session_state['last_reconciliation_saved']
    
    # Fetch all reconciliations
    all_reconciliations = fetch_cam_reconciliations()
    
    # Calculate metrics
    total_reconciliations = len(all_reconciliations)
    total_variance = sum(r.get('variance_amount', 0) or 0 for r in all_reconciliations)
    disputed = len([r for r in all_reconciliations if r.get('dispute_status') and r.get('dispute_status') != 'NOT_DISPUTED'])
    resolved_savings = sum(
        r.get('resolution_amount', 0) or 0 
        for r in all_reconciliations 
        if r.get('dispute_status') == 'RESOLVED'
    )
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val">{total_reconciliations}</div>
            <div class="lbl">Total Reconciliations</div>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        variance_class = "variance-negative" if total_variance > 0 else "variance-positive"
        st.markdown(f"""
        <div class="metric-card">
            <div class="val {variance_class}">${abs(total_variance):,.0f}</div>
            <div class="lbl">Total Overcharges Found</div>
        </div>""", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val">{disputed}</div>
            <div class="lbl">Active Disputes</div>
        </div>""", unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="val variance-positive">${resolved_savings:,.0f}</div>
            <div class="lbl">Recovered Savings</div>
        </div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Recent reconciliations table
    if all_reconciliations:
        st.markdown("### Recent Reconciliations")
        
        for recon in all_reconciliations[:10]:
            lease_info = recon.get('leases', {})
            property_address = lease_info.get('property_address', 'Unknown Property')
            
            col_a, col_b, col_c, col_d, col_e = st.columns([3, 1, 2, 2, 1])
            
            with col_a:
                st.markdown(f"**{property_address}**  \n<span style='color:#8892b0;font-size:0.8rem;'>Year: {recon.get('reconciliation_year', 'N/A')}</span>", unsafe_allow_html=True)
            
            with col_b:
                variance = recon.get('variance_amount', 0) or 0
                variance_class = "variance-negative" if variance > 0 else "variance-positive"
                st.markdown(f"<span class='{variance_class}'>${abs(variance):,.2f}</span>", unsafe_allow_html=True)
            
            with col_c:
                status = recon.get('status', 'DRAFT')
                st.markdown(f"<span style='font-size:0.85rem;'>Status: {status}</span>", unsafe_allow_html=True)
            
            with col_d:
                dispute_status = recon.get('dispute_status', 'NOT_DISPUTED')
                st.markdown(f"<span style='font-size:0.85rem;'>Dispute: {dispute_status}</span>", unsafe_allow_html=True)
            
            with col_e:
                if st.button("View", key=f"view_{recon['id']}"):
                    st.session_state['view_reconciliation_id'] = recon['id']
                    st.rerun()
            
            st.markdown("<hr style='margin:8px 0; border:none; border-top:1px solid #2d3561;'>", unsafe_allow_html=True)
    else:
        st.info("No CAM reconciliations yet. Start by creating a new reconciliation in the 'New Reconciliation' tab.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: NEW RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("### Create New CAM Reconciliation")
    
    # Step 1: Select Lease
    st.markdown("#### Step 1: Select Lease")
    
    leases = fetch_all_leases()
    if not leases:
        st.warning("No leases found. Please upload and process leases first.")
    else:
        lease_options = {
            f"{lease.get('property_address', 'Unknown')} - {lease.get('tenant_name', 'Unknown')}": lease['id']
            for lease in leases
        }
        
        selected_lease_name = st.selectbox(
            "Select a lease to reconcile CAM charges for:",
            options=list(lease_options.keys())
        )
        
        selected_lease_id = lease_options[selected_lease_name]
        
        # Fetch CAM provisions
        cam_provisions = fetch_cam_provisions(selected_lease_id)
        
        if cam_provisions:
            st.success("✅ CAM provisions found for this lease")
            
            with st.expander("📋 View CAM Provisions from Lease"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Tenant Pro-Rata Share:**")
                    prorata = cam_provisions.get('tenant_prorata_share', 0)
                    st.write(f"{prorata*100:.2f}%" if prorata else "Not specified")
                    
                    st.markdown("**CAM Base Year:**")
                    st.write(cam_provisions.get('cam_base_year', 'Not specified'))
                    
                    st.markdown("**CAM Stop Amount:**")
                    st.write(format_currency(cam_provisions.get('cam_stop_amount')))
                
                with col2:
                    st.markdown("**CAM Cap:**")
                    if cam_provisions.get('has_cam_cap'):
                        cap_pct = cam_provisions.get('cam_cap_percentage', 0)
                        st.write(f"Yes - {cap_pct}% annual maximum increase")
                    else:
                        st.write("No cap specified")
                    
                    st.markdown("**Tenant Audit Right:**")
                    st.write("Yes" if cam_provisions.get('tenant_audit_right') else "No")
                    
                    st.markdown("**Excluded Items:**")
                    excluded = cam_provisions.get('excluded_items', [])
                    st.write(", ".join(excluded) if excluded else "None specified")
        else:
            st.warning("⚠️ No CAM provisions extracted from lease. You can still proceed, but calculations may be limited.")
            
            if st.button("Extract CAM Provisions Now"):
                st.info("CAM provision extraction will be implemented in the next phase.")
        
        st.markdown("---")
        
        # Step 2: Reconciliation Details
        st.markdown("#### Step 2: Reconciliation Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            recon_year = st.number_input(
                "Reconciliation Year",
                min_value=2020,
                max_value=datetime.now().year,
                value=datetime.now().year - 1
            )
            
            statement_date = st.date_input(
                "CAM Statement Date",
                value=datetime.now()
            )
        
        with col2:
            landlord_total = st.number_input(
                "Total Landlord Charges (from CAM statement)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f"
            )
            
            tenant_share_billed = st.number_input(
                "Tenant Share Billed (your portion)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f"
            )
        
        st.markdown("---")
        
        # Step 3: Upload CAM Statement (optional)
        st.markdown("#### Step 3: Upload Landlord CAM Statement (Optional)")
        st.caption("Upload the PDF or CSV of the landlord's CAM reconciliation statement for automatic line-item extraction")
        
        uploaded_file = st.file_uploader(
            "Upload CAM Statement",
            type=['pdf', 'csv', 'xlsx'],
            help="We'll automatically extract and categorize line items"
        )
        
        if uploaded_file:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info("🔄 Automatic line-item extraction will be implemented in Phase 2B")
        
        st.markdown("---")
        
        # Step 4: Calculate & Review
        st.markdown("#### Step 4: Calculate & Review")
        
        if st.button("🧮 Calculate CAM Reconciliation", type="primary", use_container_width=True):
            if landlord_total > 0 and tenant_share_billed > 0:
                try:
                    from cam_engine import calculate_cam_charges
                    
                    # Calculate correct tenant share
                    if cam_provisions:
                        calc_result = calculate_cam_charges(landlord_total, cam_provisions)
                        calculated_share = calc_result['calculated_tenant_share']
                    else:
                        # Fallback: assume direct billing
                        calculated_share = tenant_share_billed
                        calc_result = {'calculated_tenant_share': calculated_share}
                    
                    # Calculate variance
                    variance = tenant_share_billed - calculated_share
                    variance_percentage = ((tenant_share_billed - calculated_share) / tenant_share_billed * 100) if tenant_share_billed > 0 else 0
                    
                    # Store in session state so it persists across reruns
                    st.session_state['cam_calc_results'] = {
                        'lease_id': selected_lease_id,
                        'recon_year': recon_year,
                        'statement_date': statement_date,
                        'landlord_total': landlord_total,
                        'tenant_share_billed': tenant_share_billed,
                        'calculated_share': calculated_share,
                        'variance': variance,
                        'variance_percentage': variance_percentage
                    }
                    
                    st.success("✅ Calculation complete! Results shown below.")
                    
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")
            else:
                st.warning("Please enter both the landlord total charges and tenant share billed amounts.")
        
        # Show results if they exist in session state
        if 'cam_calc_results' in st.session_state:
            results = st.session_state['cam_calc_results']
            
            # Display results
            st.markdown("### 📊 Reconciliation Results")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Landlord Billed Amount",
                    format_currency(results['tenant_share_billed'])
                )
            
            with col2:
                st.metric(
                    "Correct Amount (Per Lease)",
                    format_currency(results['calculated_share'])
                )
            
            with col3:
                variance = results['variance']
                variance_label = "Overcharge" if variance > 0 else "Undercharge"
                st.metric(
                    variance_label,
                    format_currency(abs(variance)),
                    delta=f"{abs(results['variance_percentage']):.1f}%",
                    delta_color="inverse" if variance > 0 else "normal"
                )
            
            # Recommendation
            if abs(variance) < 100:
                st.success("✅ Variance is minor (< $100). Recommended action: ACCEPT")
            elif abs(variance) < 500:
                st.warning("⚠️ Moderate variance found (< $500). Recommended action: REQUEST CLARIFICATION")
            else:
                st.error(f"🚨 Significant overcharge found: {format_currency(abs(variance))}. Recommended action: CHALLENGE")
            
            st.markdown("---")
            
            # Save button (now outside the Calculate button's block!)
            if st.button("💾 Save Reconciliation to Database", use_container_width=True, type="primary", key="save_recon"):
                st.write("🔍 **Debug: Save button clicked**")
                
                try:
                    # Prepare record
                    recon_record = {
                        'lease_id': results['lease_id'],
                        'reconciliation_year': int(results['recon_year']),
                        'statement_date': results['statement_date'].isoformat(),
                        'landlord_total_charges': float(results['landlord_total']),
                        'landlord_tenant_share': float(results['tenant_share_billed']),
                        'calculated_total_charges': float(results['landlord_total']),
                        'calculated_tenant_share': float(results['calculated_share']),
                        'variance_amount': float(results['variance']),
                        'variance_percentage': float(results['variance_percentage']),
                        'status': 'UNDER_REVIEW',
                        'dispute_status': 'NOT_DISPUTED' if abs(results['variance']) < 100 else 'CHALLENGE_DRAFTED',
                        'uploaded_by': st.session_state.get('user_id'),
                        'uploaded_at': datetime.now().isoformat()
                    }
                    
                    # Show what we're trying to save (debug)
                    with st.expander("🔍 Debug: Data being saved"):
                        st.json(recon_record)
                    
                    st.write("🔄 Attempting to insert into database...")
                    
                    # Attempt insert
                    result = sb.table("cam_reconciliations").insert(recon_record).execute()
                    
                    st.write("✅ Insert command completed")
                    st.write(f"📊 Result type: {type(result)}")
                    st.write(f"📊 Result data: {result.data if hasattr(result, 'data') else 'No data attribute'}")
                    
                    if result.data:
                        st.success("✅ CAM reconciliation saved successfully!")
                        st.balloons()
                        st.info("💡 Switch to the 'Dashboard' or 'History' tab to view your saved reconciliation.")
                        
                        # Store success state to show on other tabs
                        st.session_state['last_reconciliation_saved'] = True
                        st.session_state['saved_reconciliation_id'] = result.data[0].get('id')
                        
                        # Clear calculation results
                        del st.session_state['cam_calc_results']
                        
                        # Show saved record
                        with st.expander("📋 Saved Record Details"):
                            st.json(result.data[0])
                    else:
                        st.warning("⚠️ Save completed but no data returned.")
                        st.write("This might mean the save succeeded but Supabase didn't return the record.")
                        st.info("Check the 'History' tab to see if the record appears.")
                    
                except Exception as e:
                    st.error(f"❌ Failed to save reconciliation")
                    st.error(f"**Error type:** {type(e).__name__}")
                    st.error(f"**Error message:** {str(e)}")
                    
                    # Show full traceback for debugging
                    import traceback
                    with st.expander("🔍 Full Error Traceback"):
                        st.code(traceback.format_exc())
                    
                    # More helpful error messages
                    error_str = str(e).lower()
                    if 'does not exist' in error_str or 'relation' in error_str:
                        st.error("🗄️ **Issue:** Database tables not found")
                        st.info("**Solution:** Run the database schema script in Supabase SQL Editor")
                    elif 'permission denied' in error_str:
                        st.error("🔒 **Issue:** Permission denied")
                        st.info("**Solution:** Run GRANT statements in Supabase SQL Editor")
                    elif 'foreign key' in error_str or 'violates' in error_str:
                        st.error("🔗 **Issue:** Foreign key constraint violation")
                        st.info("**Solution:** The lease_id might not exist in the leases table")
                        st.write(f"Lease ID being used: {results['lease_id']}")
                    elif 'null value' in error_str:
                        st.error("⚠️ **Issue:** Required field is null")
                        st.info("Check which fields are missing in the error message above")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("### CAM Reconciliation History")
    
    all_reconciliations = fetch_cam_reconciliations()
    
    if not all_reconciliations:
        st.info("No reconciliation history yet. Create your first reconciliation in the 'New Reconciliation' tab.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "DRAFT", "UNDER_REVIEW", "DISCREPANCY_FOUND", "DISPUTE_FILED", "RESOLVED"]
            )
        
        with col2:
            year_filter = st.selectbox(
                "Filter by Year",
                options=["All"] + sorted(list(set(r.get('reconciliation_year') for r in all_reconciliations if r.get('reconciliation_year'))), reverse=True)
            )
        
        # Apply filters
        filtered = all_reconciliations
        if status_filter != "All":
            filtered = [r for r in filtered if r.get('status') == status_filter]
        if year_filter != "All":
            filtered = [r for r in filtered if r.get('reconciliation_year') == year_filter]
        
        st.markdown(f"**Showing {len(filtered)} reconciliation(s)**")
        st.markdown("---")
        
        # Display results
        for recon in filtered:
            lease_info = recon.get('leases', {})
            property_address = lease_info.get('property_address', 'Unknown Property')
            tenant_name = lease_info.get('tenant_name', 'Unknown Tenant')
            
            with st.expander(f"📄 {property_address} - Year {recon.get('reconciliation_year', 'N/A')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Property:** {property_address}")
                    st.markdown(f"**Tenant:** {tenant_name}")
                    st.markdown(f"**Year:** {recon.get('reconciliation_year', 'N/A')}")
                    st.markdown(f"**Status:** {recon.get('status', 'N/A')}")
                
                with col2:
                    st.markdown(f"**Landlord Billed:** {format_currency(recon.get('landlord_tenant_share'))}")
                    st.markdown(f"**Correct Amount:** {format_currency(recon.get('calculated_tenant_share'))}")
                    
                    variance = recon.get('variance_amount', 0) or 0
                    variance_class = "variance-negative" if variance > 0 else "variance-positive"
                    st.markdown(f"**Variance:** <span class='{variance_class}'>{format_currency(abs(variance))}</span>", unsafe_allow_html=True)
                    
                    st.markdown(f"**Dispute Status:** {recon.get('dispute_status', 'NOT_DISPUTED')}")
                
                # Action buttons
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("📄 View Details", key=f"detail_{recon['id']}"):
                        st.info("Detailed view coming in Phase 2B")
                
                with col_b:
                    if st.button("📝 Generate Dispute Letter", key=f"dispute_{recon['id']}"):
                        st.info("Dispute letter generation coming in Phase 2B")
                
                with col_c:
                    if st.button("📊 Download Report", key=f"report_{recon['id']}"):
                        st.info("PDF report generation coming in Phase 2B")

st.markdown("---")
st.markdown('<span style="font-size:0.75rem; color:#555;">LeaseAI CAM Reconciliation v1.0 — Phase 2A</span>', unsafe_allow_html=True)
