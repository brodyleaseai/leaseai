import streamlit as st
import sys
import os
from datetime import datetime
import json

from cam_engine import (
    analyze_line_items,
    defaults_from_parsed_statement,
    enrich_cam_provisions,
    reconcile_cam_charges,
)

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
    try:
        query = sb.table("cam_reconciliations").select("*, leases(property_address, tenant_name)")
        if lease_id:
            query = query.eq("lease_id", lease_id)
        res = query.order("reconciliation_year", desc=True).execute()
        return res.data or []
    except Exception as e:
        # If join fails, try without join
        st.warning(f"Note: Could not join with leases table: {str(e)}")
        query = sb.table("cam_reconciliations").select("*")
        if lease_id:
            query = query.eq("lease_id", lease_id)
        res = query.order("reconciliation_year", desc=True).execute()
        return res.data or []

def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "N/A"
    return f"${amount:,.2f}"

def get_openai_api_key():
    """Read OpenAI from Streamlit secrets or local config/.env. Never fail if secrets.toml is missing."""
    try:
        key = st.secrets["OPENAI_API_KEY"]
        if key:
            return key
    except Exception:
        pass
    try:
        import config as app_config
        key = getattr(app_config, "OPENAI_API_KEY", None)
        if key and not str(key).startswith("your-"):
            return key
    except Exception:
        pass
    return None

def init_cam_form_state():
    """Create Step 2 widget keys before the inputs render."""
    today = datetime.now()
    st.session_state.setdefault("cam_recon_year", today.year - 1)
    st.session_state.setdefault("cam_statement_date", today.date())
    st.session_state.setdefault("cam_landlord_total", 0.0)
    st.session_state.setdefault("cam_tenant_share_billed", 0.0)

def store_parsed_statement(parsed):
    """Copy statement totals into Step 2 and queue an automatic calculation."""
    defaults = defaults_from_parsed_statement(parsed)
    st.session_state["parsed_cam_statement"] = parsed
    st.session_state["cam_recon_year"] = int(defaults["recon_year"])
    st.session_state["cam_statement_date"] = defaults["statement_date"]
    st.session_state["cam_landlord_total"] = float(defaults["landlord_total"])
    st.session_state["cam_tenant_share_billed"] = float(defaults["tenant_share_billed"])
    st.session_state["cam_run_calc_after_parse"] = True
    n = parsed.get("total_line_items") or len(parsed.get("line_items") or [])
    st.session_state["cam_parse_message"] = (
        f"Extracted {n} line items and filled the reconciliation totals from the statement."
    )

def load_extracted_field_map(lease_id):
    """Lease abstract fields keyed by name, for filling blank CAM terms."""
    try:
        fields_res = sb.table("extracted_fields").select("*").eq("lease_id", lease_id).execute()
    except Exception:
        return {}
    mapped = {}
    for field in fields_res.data or []:
        name = field.get("field_name")
        if not name:
            continue
        mapped[name] = field.get("reviewed_value") or field.get("raw_value")
    return mapped

def run_cam_calculation(lease_id, cam_provisions, recon_year, statement_date, landlord_total, tenant_share_billed):
    """Compare billed tenant share to the amount allowed by the lease."""
    landlord_total = float(landlord_total or 0)
    tenant_share_billed = float(tenant_share_billed or 0)
    provisions = enrich_cam_provisions(cam_provisions, load_extracted_field_map(lease_id))
    parsed = st.session_state.get("parsed_cam_statement") or {}
    line_items = parsed.get("line_items") or []
    calc_result = reconcile_cam_charges(
        landlord_total,
        tenant_share_billed,
        provisions,
        line_items,
    )
    calculated_share = calc_result["calculated_tenant_share"]
    variance = tenant_share_billed - calculated_share
    variance_percentage = (
        ((tenant_share_billed - calculated_share) / tenant_share_billed * 100)
        if tenant_share_billed else 0
    )
    st.session_state["cam_calc_results"] = {
        "lease_id": lease_id,
        "recon_year": recon_year,
        "statement_date": statement_date,
        "landlord_total": landlord_total,
        "tenant_share_billed": tenant_share_billed,
        "calculated_share": calculated_share,
        "variance": variance,
        "variance_percentage": variance_percentage,
        "calculations": calc_result.get("calculations") or [],
        "excluded_building_charges": calc_result.get("excluded_building_charges") or 0,
        "allowable_building_charges": calc_result.get("allowable_building_charges"),
        "cam_cap_applied": calc_result.get("cam_cap_applied"),
        "provisions_used": provisions,
        "analyzed_line_items": calc_result.get("analyzed_line_items") or [],
    }
    return st.session_state["cam_calc_results"]


def load_lease_and_provisions(lease_id):
    lease_res = sb.table("leases").select("*").eq("id", lease_id).execute()
    lease_data = lease_res.data[0] if lease_res.data else {}
    cam_prov_res = sb.table("cam_provisions").select("*").eq("lease_id", lease_id).execute()
    cam_prov = cam_prov_res.data[0] if cam_prov_res.data else {}
    return lease_data, cam_prov


def report_line_items(results, cam_prov):
    stored = results.get("analyzed_line_items") or []
    if stored:
        return stored
    parsed = st.session_state.get("parsed_cam_statement") or {}
    return analyze_line_items(parsed.get("line_items") or [], cam_prov or {})


def build_cam_report(results):
    """Generate the tenant CAM workpaper and cache it for download / email."""
    from cam_pdf_report import cam_report_filename, generate_cam_pdf_report

    lease_data, cam_prov = load_lease_and_provisions(results["lease_id"])
    lease_data = dict(lease_data or {})
    fields = load_extracted_field_map(results["lease_id"])
    if not lease_data.get("landlord_name"):
        lease_data["landlord_name"] = (
            fields.get("Landlord Legal Name") or fields.get("Landlord Name")
        )
    if not lease_data.get("tenant_name"):
        lease_data["tenant_name"] = (
            fields.get("Tenant Legal Name") or fields.get("Tenant Name")
        )
    if not lease_data.get("property_address"):
        lease_data["property_address"] = fields.get("Property Address")
    provisions = results.get("provisions_used") or cam_prov
    line_items = report_line_items(results, provisions)
    recon_data = {
        "reconciliation_year": results["recon_year"],
        "statement_date": (
            results["statement_date"].isoformat()
            if hasattr(results["statement_date"], "isoformat")
            else results["statement_date"]
        ),
        "landlord_total_charges": results["landlord_total"],
        "landlord_tenant_share": results["tenant_share_billed"],
        "calculated_total_charges": results.get("allowable_building_charges"),
        "calculated_tenant_share": results["calculated_share"],
        "variance_amount": results["variance"],
        "variance_percentage": results["variance_percentage"],
        "calculations": results.get("calculations") or [],
        "excluded_building_charges": results.get("excluded_building_charges") or 0,
        "allowable_building_charges": results.get("allowable_building_charges"),
        "cam_cap_applied": results.get("cam_cap_applied"),
    }
    pdf_bytes = generate_cam_pdf_report(lease_data, recon_data, line_items, provisions)
    filename = cam_report_filename(lease_data, results["recon_year"])
    st.session_state["cam_report_pdf"] = pdf_bytes
    st.session_state["cam_report_filename"] = filename
    st.session_state["cam_report_context"] = {
        "lease_data": lease_data,
        "filename": filename,
    }
    return pdf_bytes, filename, lease_data

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
            # Handle both joined and non-joined data
            lease_info = recon.get('leases', {})
            if lease_info:
                property_address = lease_info.get('property_address', 'Unknown Property')
            else:
                # If join didn't work, fetch lease separately
                lease_id = recon.get('lease_id')
                try:
                    lease_res = sb.table("leases").select("property_address").eq("id", lease_id).execute()
                    property_address = lease_res.data[0].get('property_address', 'Unknown Property') if lease_res.data else f"Lease ID: {lease_id}"
                except:
                    property_address = f"Lease ID: {lease_id}"
            
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
    init_cam_form_state()
    parse_message = st.session_state.pop("cam_parse_message", None)
    if parse_message:
        st.success(parse_message)
    
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
            st.warning("⚠️ No CAM provisions extracted from lease. Extract them now for accurate calculations.")
            
            col_extract1, col_extract2 = st.columns([1, 2])
            
            with col_extract1:
                if st.button("🤖 Extract CAM Provisions with AI", use_container_width=True, type="primary"):
                    with st.spinner("Extracting CAM provisions using GPT-4o..."):
                        try:
                            from cam_gpt_extractor import extract_cam_provisions_with_gpt, save_cam_provisions_to_db
                            import openai
                            
                            # Get OpenAI API key
                            api_key = get_openai_api_key()
                            if not api_key:
                                st.error("OpenAI API key not configured. Add OPENAI_API_KEY to .env or config.py.")
                            else:
                                # Fetch lease text
                                lease_res = sb.table("leases").select("*").eq("id", selected_lease_id).execute()
                                if lease_res.data:
                                    lease_data = lease_res.data[0]
                                    
                                    # Get extracted fields text
                                    fields_res = sb.table("extracted_fields").select("*").eq("lease_id", selected_lease_id).execute()
                                    lease_text = f"Property: {lease_data.get('property_address')}\n"
                                    lease_text += f"Tenant: {lease_data.get('tenant_name')}\n\n"
                                    
                                    # Build lease text from extracted fields
                                    for field in fields_res.data:
                                        field_name = field.get('field_name', '')
                                        value = field.get('reviewed_value') or field.get('raw_value', '')
                                        lease_text += f"{field_name}: {value}\n"
                                    
                                    # Extract provisions
                                    provisions = extract_cam_provisions_with_gpt(lease_text, api_key)
                                    
                                    if provisions.get('error'):
                                        st.error(f"Extraction failed: {provisions['error']}")
                                    else:
                                        # Save to database
                                        if save_cam_provisions_to_db(selected_lease_id, provisions, sb):
                                            st.success("✅ CAM provisions extracted and saved!")
                                            st.balloons()
                                            st.info("Refresh the page to see the extracted provisions.")
                                            
                                            # Show extracted data
                                            with st.expander("📋 View Extracted Provisions"):
                                                st.json(provisions)
                                        else:
                                            st.error("Failed to save provisions to database")
                                else:
                                    st.error("Lease not found")
                        except Exception as e:
                            st.error(f"Extraction error: {str(e)}")
            
            with col_extract2:
                st.caption("Uses GPT-4o to analyze the lease and extract all CAM-related terms, caps, exclusions, and tenant share.")
        
        st.markdown("---")
        
        # Step 2: Upload CAM Statement — this fills the totals below
        st.markdown("#### Step 2: Upload Landlord CAM Statement")
        st.caption(
            "Upload the landlord's year-end CAM PDF and parse it. The app reads every numbered "
            "line, fills year / date / building total / tenant share, and reconciles against this lease."
        )
        
        uploaded_file = st.file_uploader(
            "Upload CAM Statement",
            type=['pdf', 'csv', 'xlsx'],
            help="We'll automatically extract and categorize line items",
            key="cam_statement_upload"
        )
        
        if uploaded_file:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            if st.button("🤖 Parse CAM Statement with AI", use_container_width=True, type="primary"):
                with st.spinner("Parsing CAM statement..."):
                    try:
                        from cam_gpt_extractor import parse_cam_statement_with_gpt, extract_text_from_pdf
                        from cam_engine import assemble_cam_statement
                        import tempfile
                        
                        api_key = get_openai_api_key()
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        statement_text = extract_text_from_pdf(tmp_path)
                        os.unlink(tmp_path)
                        
                        if not statement_text:
                            st.error("Failed to extract text from PDF")
                        else:
                            parsed_data = None
                            if api_key:
                                try:
                                    parsed_data = parse_cam_statement_with_gpt(statement_text, api_key)
                                except Exception:
                                    parsed_data = None
                            if not parsed_data or (parsed_data.get("error") and not parsed_data.get("line_items")):
                                parsed_data = assemble_cam_statement(statement_text)
                            
                            if parsed_data.get('error') and not parsed_data.get('line_items'):
                                st.error(f"Parsing failed: {parsed_data['error']}")
                            else:
                                store_parsed_statement(parsed_data)
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"Parsing error: {str(e)}")
        
        # Show parsed line items if available
        if 'parsed_cam_statement' in st.session_state:
            parsed_data = st.session_state['parsed_cam_statement']
            line_items = parsed_data.get('line_items', [])
            
            if line_items:
                st.markdown("### 📊 Extracted Line Items")
                analyzed_items = analyze_line_items(line_items, cam_provisions or {})
                challenged = [item for item in analyzed_items if item.get("should_challenge")]
                st.write(f"**Total items:** {len(analyzed_items)}")
                if challenged:
                    st.warning(
                        f"{len(challenged)} line item(s) look excluded under this lease "
                        f"(capital, structural, legal, depreciation, or debt service)."
                    )
                elif not cam_provisions:
                    st.caption("Extract CAM provisions on this lease to flag excluded rows here.")
                
                import pandas as pd
                rows = []
                for item in analyzed_items:
                    amount = item.get("amount", item.get("landlord_amount", 0)) or 0
                    rows.append({
                        "#": item.get("line_number"),
                        "Description": item.get("description"),
                        "Category": item.get("category"),
                        "Amount": f"${float(amount):,.2f}",
                        "Flag": "Challenge" if item.get("should_challenge") else "OK",
                        "Reason": item.get("dispute_reason") or "",
                    })
                df = pd.DataFrame(rows)
                if not df.empty:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    with st.expander("📈 Summary by Category"):
                        category_totals = {}
                        for item in analyzed_items:
                            cat = item.get('category', 'OTHER')
                            amt = float(item.get('amount', item.get('landlord_amount', 0)) or 0)
                            category_totals[cat] = category_totals.get(cat, 0) + amt
                        for cat, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                            st.write(f"**{cat}:** ${total:,.2f}")
        
        st.markdown("---")
        
        # Step 3: totals — auto-filled from the parsed statement
        st.markdown("#### Step 3: Reconciliation Details")
        if st.session_state.get("parsed_cam_statement"):
            st.success("Filled from the CAM statement. Change a value only if the PDF was read wrong.")
        else:
            st.caption("These fill automatically after you parse the statement. You should not need to type them.")
        
        col1, col2 = st.columns(2)
        max_year = max(datetime.now().year, int(st.session_state.get("cam_recon_year") or datetime.now().year))
        
        with col1:
            recon_year = st.number_input(
                "Reconciliation Year",
                min_value=2020,
                max_value=max_year,
                key="cam_recon_year",
            )
            
            statement_date = st.date_input(
                "CAM Statement Date",
                key="cam_statement_date",
            )
        
        with col2:
            landlord_total = st.number_input(
                "Total Landlord Charges (from CAM statement)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                key="cam_landlord_total",
            )
            
            tenant_share_billed = st.number_input(
                "Tenant Share Billed (your portion)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                key="cam_tenant_share_billed",
            )
        
        st.markdown("---")
        
        # Step 4: Calculate & Review
        st.markdown("#### Step 4: Calculate & Review")
        
        if st.session_state.pop("cam_run_calc_after_parse", False):
            if landlord_total > 0 and tenant_share_billed > 0:
                try:
                    run_cam_calculation(
                        selected_lease_id,
                        cam_provisions,
                        recon_year,
                        statement_date,
                        landlord_total,
                        tenant_share_billed,
                    )
                    st.success("Reconciliation calculated from this lease and the CAM statement.")
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")
            else:
                st.warning("The statement was parsed, but building total or tenant share billed is still 0. Check the PDF totals in Step 3.")

        if st.button("🧮 Calculate CAM Reconciliation", type="primary", use_container_width=True):
            if landlord_total > 0 and tenant_share_billed > 0:
                try:
                    run_cam_calculation(
                        selected_lease_id,
                        cam_provisions,
                        recon_year,
                        statement_date,
                        landlord_total,
                        tenant_share_billed,
                    )
                    st.success("✅ Calculation complete! Results shown below.")
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")
            else:
                st.warning("Parse the CAM statement, or enter both the landlord total charges and tenant share billed amounts.")
        
        # Show results if they exist in session state
        if 'cam_calc_results' in st.session_state:
            results = st.session_state['cam_calc_results']
            
            # Display results
            st.markdown("### 📊 Reconciliation Results")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Tenant share billed",
                    format_currency(results['tenant_share_billed'])
                )
            
            with col2:
                st.metric(
                    "Tenant share allowed by lease",
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

            steps = results.get("calculations") or []
            if steps:
                st.markdown("#### How this number was calculated")
                for step in steps:
                    st.write(
                        f"- **{step.get('step')}:** {step.get('formula')} = "
                        f"{format_currency(step.get('result'))}"
                    )
            
            st.markdown("---")
            
            # Line-by-line variance analysis (if line items available)
            if 'parsed_cam_statement' in st.session_state:
                parsed_data = st.session_state['parsed_cam_statement']
                line_items = parsed_data.get('line_items', [])
                
                if line_items:
                    st.markdown("### 🔍 Line-by-Line Variance Analysis")
                    
                    # Analyze each line item
                    import pandas as pd
                    from cam_engine import analyze_line_items
                    
                    # Get CAM provisions for exclusion checking
                    cam_prov_res = sb.table("cam_provisions").select("*").eq("lease_id", results['lease_id']).execute()
                    cam_prov = cam_prov_res.data[0] if cam_prov_res.data else {}
                    
                    analyzed_items = results.get("analyzed_line_items") or analyze_line_items(line_items, cam_prov)
                    df_items = pd.DataFrame(analyzed_items)

                    if df_items.empty:
                        st.dataframe(df_items, use_container_width=True, hide_index=True)
                    else:
                        def flag_label(row):
                            return "🚨 Challenge" if row.get("should_challenge") else "✅ Allow"

                        def reason_label(row):
                            if row.get("should_challenge"):
                                return row.get("dispute_reason") or row.get("notes") or "Excluded per lease"
                            return "Included in CAM"

                        df_items["Flag"] = df_items.apply(flag_label, axis=1)
                        df_items["Reason"] = df_items.apply(reason_label, axis=1)
                        if "amount" in df_items.columns:
                            df_items["Landlord amount"] = df_items["amount"].apply(
                                lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A"
                            )
                        display_cols = [
                            col for col in [
                                "line_number",
                                "description",
                                "category",
                                "Landlord amount",
                                "Flag",
                                "Reason",
                            ]
                            if col in df_items.columns
                        ]
                        st.dataframe(df_items[display_cols], use_container_width=True, hide_index=True)
                    
                    # Summary of flagged items
                    flagged = [item for item in analyzed_items if item.get('should_challenge', False)]
                    if flagged:
                        st.warning(f"🚨 **{len(flagged)} line items flagged for review:**")
                        for item in flagged[:5]:  # Show first 5
                            st.write(f"- {item.get('description', 'Unknown')} (${item.get('amount', 0):,.2f}) - {item.get('notes', 'No notes')}")
            
            st.markdown("---")
            
            # Action buttons row
            col_action1, col_action2, col_action3 = st.columns(3)
            
            with col_action1:
                if st.button("📄 Generate PDF Report", use_container_width=True, type="secondary"):
                    with st.spinner("Generating CAM workpaper..."):
                        try:
                            build_cam_report(results)
                            st.success("✅ CAM workpaper generated. Download it, or email it to the client.")
                        except Exception as e:
                            st.error(f"PDF generation error: {str(e)}")
            
            with col_action2:
                if st.button("📧 Generate Dispute Letter", use_container_width=True, type="secondary"):
                    if abs(results['variance']) > 100:
                        try:
                            from cam_engine import generate_cam_dispute_letter
                            
                            # Get lease data
                            lease_res = sb.table("leases").select("*").eq("id", results['lease_id']).execute()
                            lease_data = lease_res.data[0] if lease_res.data else {}
                            
                            # Get line items
                            line_items = []
                            if 'parsed_cam_statement' in st.session_state:
                                from cam_engine import analyze_line_items
                                cam_prov_res = sb.table("cam_provisions").select("*").eq("lease_id", results['lease_id']).execute()
                                cam_prov = cam_prov_res.data[0] if cam_prov_res.data else {}
                                
                                parsed_items = st.session_state['parsed_cam_statement'].get('line_items', [])
                                line_items = analyze_line_items(parsed_items, cam_prov)
                                
                                # Only disputed items
                                line_items = [item for item in line_items if item.get('should_challenge', False)]
                            
                            # Build recon dict
                            recon_data = {
                                'reconciliation_year': results['recon_year'],
                                'variance_amount': results['variance'],
                                'landlord_tenant_share': results['tenant_share_billed'],
                                'calculated_tenant_share': results['calculated_share']
                            }
                            
                            # Generate letter
                            letter_text = generate_cam_dispute_letter(lease_data, recon_data, line_items)
                            
                            # Display in expander
                            with st.expander("📧 View Dispute Letter", expanded=True):
                                st.text_area(
                                    "Dispute Letter (Copy & Paste)",
                                    value=letter_text,
                                    height=400,
                                    key="dispute_letter_text"
                                )
                                
                                st.download_button(
                                    label="⬇️ Download as .txt",
                                    data=letter_text,
                                    file_name=f"CAM_Dispute_Letter_{results['recon_year']}.txt",
                                    mime="text/plain"
                                )
                            
                            st.success("✅ Dispute letter generated!")
                        
                        except Exception as e:
                            st.error(f"Letter generation error: {str(e)}")
                    else:
                        st.info("💡 Variance is minor (< $100). Dispute letter not needed.")
            
            with col_action3:
                if st.button("✉️ Email Report to Client", use_container_width=True, type="secondary"):
                    st.session_state["show_cam_email"] = True

            if st.session_state.get("cam_report_pdf"):
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=st.session_state["cam_report_pdf"],
                    file_name=st.session_state.get("cam_report_filename") or "CAM_Reconciliation.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="download_cam_workpaper",
                )

            if st.session_state.get("show_cam_email"):
                st.markdown("#### Email the workpaper")
                default_email = st.session_state.get("user_email") or ""
                default_name = (
                    st.session_state.get("user_name")
                    or (st.session_state.get("cam_report_context") or {}).get("lease_data", {}).get("tenant_name")
                    or "Client"
                )
                col_email, col_name = st.columns(2)
                with col_email:
                    recipient_email = st.text_input(
                        "Client email",
                        value=default_email,
                        key="cam_report_email",
                    )
                with col_name:
                    recipient_name = st.text_input(
                        "Client name",
                        value=default_name,
                        key="cam_report_recipient_name",
                    )
                if st.button("Send CAM workpaper", type="primary", key="send_cam_report"):
                    if not recipient_email or "@" not in recipient_email:
                        st.error("Enter a valid client email address.")
                    else:
                        try:
                            pdf_bytes = st.session_state.get("cam_report_pdf")
                            filename = st.session_state.get("cam_report_filename")
                            lease_data = (st.session_state.get("cam_report_context") or {}).get("lease_data") or {}
                            if not pdf_bytes:
                                pdf_bytes, filename, lease_data = build_cam_report(results)
                            from email_delivery import send_cam_report_email
                            recommendation = "CHALLENGE" if abs(results["variance"]) >= 100 else "ACCEPT"
                            sent = send_cam_report_email(
                                recipient_email=recipient_email.strip(),
                                recipient_name=recipient_name.strip() or "Client",
                                property_address=lease_data.get("property_address") or "the leased premises",
                                tenant_name=lease_data.get("tenant_name") or recipient_name,
                                year=results["recon_year"],
                                pdf_bytes=pdf_bytes,
                                billed_share=results["tenant_share_billed"],
                                allowed_share=results["calculated_share"],
                                variance_amount=results["variance"],
                                recommendation=recommendation,
                            )
                            if sent:
                                st.success(f"CAM workpaper emailed to {recipient_email.strip()}.")
                                st.session_state["show_cam_email"] = False
                            else:
                                st.error(
                                    "SendGrid did not send the email. Check SENDGRID_API_KEY in "
                                    "the environment or .env, then try again. You can still download the PDF."
                                )
                        except Exception as e:
                            st.error(f"Email error: {str(e)}")
            
            st.markdown("---")
            
            # Save button (now outside the Calculate button's block!)
            if st.button("💾 Save Reconciliation to Database", use_container_width=True, type="primary", key="save_recon"):
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
                    
                    # Attempt insert
                    result = sb.table("cam_reconciliations").insert(recon_record).execute()
                    
                    if result.data:
                        st.success("✅ CAM reconciliation saved successfully!")
                        st.balloons()
                        st.info("💡 Switch to the 'Dashboard' or 'History' tab to view your saved reconciliation.")
                        
                        # Store success state to show on other tabs
                        st.session_state['last_reconciliation_saved'] = True
                        st.session_state['saved_reconciliation_id'] = result.data[0].get('id')
                        
                        # Clear calculation results
                        del st.session_state['cam_calc_results']
                    else:
                        st.warning("⚠️ Save completed but no confirmation returned. Please check the History tab.")
                    
                except Exception as e:
                    st.error(f"❌ Failed to save reconciliation: {str(e)}")
                    
                    # More helpful error messages for common issues
                    error_str = str(e).lower()
                    if 'does not exist' in error_str or 'relation' in error_str:
                        st.info("💡 Database tables may not be set up. Please run the database schema script.")
                    elif 'permission denied' in error_str:
                        st.info("💡 Permission issue. Please run the GRANT statements in Supabase SQL Editor.")
                    elif 'foreign key' in error_str or 'violates' in error_str:
                        st.info("💡 The selected lease may not exist in the database.")

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
                    if st.button("📝 Update Status", key=f"status_{recon['id']}", use_container_width=True):
                        # Show status update form
                        st.session_state[f'show_status_form_{recon["id"]}'] = True
                
                with col_b:
                    if st.button("📧 Dispute Letter", key=f"dispute_{recon['id']}", use_container_width=True):
                        try:
                            from cam_engine import generate_cam_dispute_letter
                            
                            # Get lease data
                            lease_res = sb.table("leases").select("*").eq("id", recon.get('lease_id')).execute()
                            lease_data = lease_res.data[0] if lease_res.data else {}
                            
                            # Generate letter
                            letter_text = generate_cam_dispute_letter(lease_data, recon, [])
                            
                            st.download_button(
                                label="⬇️ Download Dispute Letter",
                                data=letter_text,
                                file_name=f"Dispute_Letter_{recon.get('reconciliation_year')}.txt",
                                mime="text/plain",
                                key=f"dl_dispute_{recon['id']}"
                            )
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                
                with col_c:
                    if st.button("📄 PDF Report", key=f"report_{recon['id']}", use_container_width=True):
                        try:
                            from cam_pdf_report import generate_cam_pdf_report
                            
                            # Get all data
                            lease_res = sb.table("leases").select("*").eq("id", recon.get('lease_id')).execute()
                            lease_data = lease_res.data[0] if lease_res.data else {}
                            
                            cam_prov_res = sb.table("cam_provisions").select("*").eq("lease_id", recon.get('lease_id')).execute()
                            cam_prov = cam_prov_res.data[0] if cam_prov_res.data else {}
                            
                            # Get line items if available
                            line_items_res = sb.table("cam_line_items").select("*").eq("reconciliation_id", recon['id']).execute()
                            line_items = line_items_res.data if line_items_res.data else []
                            
                            # Generate PDF
                            pdf_bytes = generate_cam_pdf_report(lease_data, recon, line_items, cam_prov)
                            
                            property_name = lease_data.get('property_address', 'Property').replace(' ', '_')[:30]
                            filename = f"CAM_Report_{property_name}_{recon.get('reconciliation_year')}.pdf"
                            
                            st.download_button(
                                label="⬇️ Download PDF",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                key=f"dl_pdf_{recon['id']}"
                            )
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                
                # Status update form (if triggered)
                if st.session_state.get(f'show_status_form_{recon["id"]}', False):
                    st.markdown("---")
                    st.markdown("#### Update Reconciliation Status")
                    
                    new_status = st.selectbox(
                        "New Status",
                        options=["DRAFT", "UNDER_REVIEW", "DISCREPANCY_FOUND", "DISPUTE_FILED", "RESOLVED", "ACCEPTED"],
                        index=0,
                        key=f"status_select_{recon['id']}"
                    )
                    
                    new_dispute_status = st.selectbox(
                        "Dispute Status",
                        options=["NOT_DISPUTED", "CHALLENGE_DRAFTED", "CHALLENGE_SENT", "AWAITING_RESPONSE", "UNDER_NEGOTIATION", "RESOLVED", "ESCALATED"],
                        index=0,
                        key=f"dispute_select_{recon['id']}"
                    )
                    
                    notes = st.text_area(
                        "Add Notes (optional)",
                        key=f"notes_{recon['id']}",
                        placeholder="Record any updates, communications, or next steps..."
                    )
                    
                    col_save, col_cancel = st.columns(2)
                    
                    with col_save:
                        if st.button("💾 Save Update", key=f"save_update_{recon['id']}", use_container_width=True, type="primary"):
                            try:
                                # Update reconciliation
                                update_data = {
                                    'status': new_status,
                                    'dispute_status': new_dispute_status
                                }
                                
                                sb.table("cam_reconciliations").update(update_data).eq("id", recon['id']).execute()
                                
                                # Add to dispute history if notes provided
                                if notes:
                                    history_entry = {
                                        'reconciliation_id': recon['id'],
                                        'action': f"Status updated to {new_status}",
                                        'notes': notes,
                                        'performed_by': st.session_state.get('user_id', 'system'),
                                        'performed_at': datetime.now().isoformat()
                                    }
                                    sb.table("cam_dispute_history").insert(history_entry).execute()
                                
                                st.success("✅ Status updated successfully!")
                                st.balloons()
                                
                                # Clear form state
                                st.session_state[f'show_status_form_{recon["id"]}'] = False
                                
                                # Refresh
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"Update error: {str(e)}")
                    
                    with col_cancel:
                        if st.button("❌ Cancel", key=f"cancel_update_{recon['id']}", use_container_width=True):
                            st.session_state[f'show_status_form_{recon["id"]}'] = False
                            st.rerun()
                
                # Show dispute history
                history_res = sb.table("cam_dispute_history").select("*").eq("reconciliation_id", recon['id']).order("performed_at", desc=True).execute()
                
                if history_res.data:
                    st.markdown("---")
                    st.markdown("**📜 Communication History:**")
                    
                    for entry in history_res.data[:5]:  # Show latest 5
                        action_date = entry.get('performed_at', '')[:10] if entry.get('performed_at') else 'Unknown date'
                        st.markdown(f"- **{action_date}**: {entry.get('action', 'No action')} - {entry.get('notes', '')}")


st.markdown("---")
st.markdown('<span style="font-size:0.75rem; color:#555;">LeaseAI CAM Reconciliation v1.0 — Phase 2A</span>', unsafe_allow_html=True)
