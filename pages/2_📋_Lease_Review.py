import streamlit as st
import sys
import os
from datetime import datetime

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LeaseAI Review",
    page_icon="🏢",
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
    .badge-ready    { background:#1b4d2e; color:#4ade80; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-review   { background:#4a3800; color:#fbbf24; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-approved { background:#1a3a5c; color:#60a5fa; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-flagged  { background:#4a1515; color:#f87171; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .conf-high { color:#4ade80; font-weight:600; }
    .conf-med  { color:#fbbf24; font-weight:600; }
    .conf-low  { color:#f87171; font-weight:600; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_status_badge(status):
    status = (status or "").upper()
    if status == "READY FOR REVIEW":
        return '<span class="badge-ready">READY FOR REVIEW</span>'
    elif status == "APPROVED":
        return '<span class="badge-approved">APPROVED</span>'
    elif status == "FLAGGED":
        return '<span class="badge-flagged">FLAGGED</span>'
    else:
        return '<span class="badge-review">PENDING</span>'

def get_conf_badge(conf):
    conf = (conf or "").upper()
    if conf == "HIGH":
        return '<span class="conf-high">● HIGH</span>'
    elif conf == "MEDIUM":
        return '<span class="conf-med">● MEDIUM</span>'
    else:
        return '<span class="conf-low">● LOW</span>'

def format_date(dt_str):
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y  %I:%M %p")
    except Exception:
        return dt_str[:10]

def fetch_all_leases():
    res = sb.table("leases").select("*, clients(name)").order("created_at", desc=True).execute()
    return res.data or []

def fetch_lease(lease_id):
    res = sb.table("leases").select("*, clients(name)").eq("id", lease_id).single().execute()
    return res.data

def fetch_fields(lease_id):
    res = (
        sb.table("extracted_fields")
        .select("*")
        .eq("lease_id", lease_id)
        .order("field_number")
        .execute()
    )
    return res.data or []

def update_field_value(field_id, new_value):
    sb.table("extracted_fields").update({
        "reviewed_value": new_value,
        "reviewed": True,
        "reviewed_at": datetime.utcnow().isoformat(),
    }).eq("id", field_id).execute()

def update_lease_status(lease_id, status):
    sb.table("leases").update({
        "status": status,
        "reviewed_at": datetime.utcnow().isoformat(),
    }).eq("id", lease_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAV
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🏢 LeaseAI")
    st.markdown("---")
    
    # Default to the review page if coming from upload
    default_page = st.session_state.get("review_page", "📋 Lease Dashboard")
    default_index = ["📋 Lease Dashboard", "🔍 Review a Lease", "⬆️ Process New Lease"].index(default_page) if default_page in ["📋 Lease Dashboard", "🔍 Review a Lease", "⬆️ Process New Lease"] else 0
    
    page = st.radio(
        "Navigation",
        ["📋 Lease Dashboard", "🔍 Review a Lease", "⬆️ Process New Lease"],
        index=default_index,
        label_visibility="collapsed",
    )
    
    # Clear the session state after using it
    if "review_page" in st.session_state:
        del st.session_state["review_page"]
    
    st.markdown("---")
    st.markdown('<span style="font-size:0.75rem; color:#555;">LeaseAI v1.0 — Phase 4</span>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

if page == "📋 Lease Dashboard":
    st.markdown("""
    <div class="leaseai-header">
        <div>
            <h1>🏢 LeaseAI — Lease Dashboard</h1>
            <span>All processed leases and their extraction status</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    leases = fetch_all_leases()

    total    = len(leases)
    approved = sum(1 for l in leases if (l.get("status") or "").upper() == "APPROVED")
    flagged  = sum(1 for l in leases if (l.get("status") or "").upper() == "FLAGGED")
    pending  = total - approved - flagged

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, total,    "Total Leases"),
        (c2, pending,  "Pending Review"),
        (c3, approved, "Approved"),
        (c4, flagged,  "Flagged"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val">{val}</div>
                <div class="lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Bulk Export Actions
    if leases:
        st.markdown("### 📦 Bulk Export Actions")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("📊 Export All to Yardi CSV", use_container_width=True):
                try:
                    from bulk_export import export_all_leases_to_yardi
                    
                    # Fetch all fields for all leases
                    all_fields = {}
                    for lease in leases:
                        fields_response = sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
                        all_fields[lease['id']] = fields_response.data or []
                    
                    # Generate bulk CSV
                    csv_bytes = export_all_leases_to_yardi(leases, all_fields)
                    
                    # Log export
                    try:
                        sb.table("export_history").insert({
                            "user_id": st.session_state.get("user_id"),
                            "export_type": "YARDI_CSV_BULK",
                            "export_format": "CSV",
                            "file_size_bytes": len(csv_bytes),
                            "date_range": {"count": len(leases)}
                        }).execute()
                    except:
                        pass
                    
                    # Offer download
                    st.download_button(
                        label=f"⬇️ Download All {len(leases)} Leases (Yardi CSV)",
                        data=csv_bytes,
                        file_name=f"Yardi_All_Leases_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ Exported {len(leases)} leases to Yardi format!")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col2:
            if st.button("📊 Export All to MRI CSV", use_container_width=True):
                try:
                    from bulk_export import export_all_leases_to_mri
                    
                    # Fetch all fields for all leases
                    all_fields = {}
                    for lease in leases:
                        fields_response = sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
                        all_fields[lease['id']] = fields_response.data or []
                    
                    # Generate bulk CSV
                    csv_bytes = export_all_leases_to_mri(leases, all_fields)
                    
                    # Log export
                    try:
                        sb.table("export_history").insert({
                            "user_id": st.session_state.get("user_id"),
                            "export_type": "MRI_CSV_BULK",
                            "export_format": "CSV",
                            "file_size_bytes": len(csv_bytes),
                            "date_range": {"count": len(leases)}
                        }).execute()
                    except:
                        pass
                    
                    # Offer download
                    st.download_button(
                        label=f"⬇️ Download All {len(leases)} Leases (MRI CSV)",
                        data=csv_bytes,
                        file_name=f"MRI_All_Leases_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ Exported {len(leases)} leases to MRI format!")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col3:
            if st.button("📄 Export All to CSV", use_container_width=True):
                try:
                    from generic_export import export_all_leases_consolidated_csv
                    
                    # Fetch all fields for all leases
                    all_extracted = []
                    for lease in leases:
                        fields_response = sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
                        fields_data = fields_response.data or []
                        
                        # Convert to dict format
                        extracted_dict = {}
                        for field in fields_data:
                            field_name = field.get("field_name", "Unknown")
                            extracted_dict[field_name] = {
                                "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                                "confidence": field.get("confidence", "MEDIUM")
                            }
                        all_extracted.append(extracted_dict)
                    
                    # Generate consolidated CSV
                    csv_bytes = export_all_leases_consolidated_csv(leases, all_extracted)
                    
                    # Log export
                    try:
                        sb.table("export_history").insert({
                            "user_id": st.session_state.get("user_id"),
                            "export_type": "GENERIC_CSV_BULK",
                            "export_format": "CSV",
                            "file_size_bytes": len(csv_bytes),
                            "date_range": {"count": len(leases)}
                        }).execute()
                    except:
                        pass
                    
                    # Offer download
                    st.download_button(
                        label=f"⬇️ Download All {len(leases)} Leases (CSV)",
                        data=csv_bytes,
                        file_name=f"All_Leases_Consolidated_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ Exported {len(leases)} leases to consolidated CSV!")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col4:
            if st.button("📊 Export All to Excel", use_container_width=True):
                try:
                    from generic_export import export_all_leases_excel_zip
                    
                    # Fetch all fields for all leases
                    all_extracted = []
                    for lease in leases:
                        fields_response = sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
                        fields_data = fields_response.data or []
                        
                        # Convert to dict format
                        extracted_dict = {}
                        for field in fields_data:
                            field_name = field.get("field_name", "Unknown")
                            extracted_dict[field_name] = {
                                "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                                "confidence": field.get("confidence", "MEDIUM")
                            }
                        all_extracted.append(extracted_dict)
                    
                    # Generate ZIP of Excel files
                    zip_bytes = export_all_leases_excel_zip(leases, all_extracted)
                    
                    # Log export
                    try:
                        sb.table("export_history").insert({
                            "user_id": st.session_state.get("user_id"),
                            "export_type": "EXCEL_BULK",
                            "export_format": "ZIP",
                            "file_size_bytes": len(zip_bytes),
                            "date_range": {"count": len(leases)}
                        }).execute()
                    except:
                        pass
                    
                    # Offer download
                    st.download_button(
                        label=f"⬇️ Download All {len(leases)} Leases (Excel ZIP)",
                        data=zip_bytes,
                        file_name=f"All_Leases_Excel_{datetime.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    st.success(f"✅ Exported {len(leases)} leases to Excel format (ZIP)!")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col5:
            if st.button("📦 Bulk Upload", use_container_width=True):
                st.switch_page("pages/9_📦_Bulk_Upload.py")
        
        st.markdown("---")

    if not leases:
        st.info("No leases processed yet. Use **Process New Lease** to get started.")
    else:
        for lease in leases:
            client_name = (lease.get("clients") or {}).get("name", "Unknown Client")
            filename    = lease.get("filename") or lease.get("name") or "—"
            status      = lease.get("status") or "READY FOR REVIEW"
            created     = format_date(lease.get("created_at"))
            pages       = lease.get("page_count") or "—"
            lease_id    = lease["id"]

            col_a, col_b, col_c, col_d, col_e = st.columns([3, 2, 1, 2, 1])
            with col_a:
                st.markdown(f"**{filename}**  \n<span style='color:#8892b0;font-size:0.8rem;'>{client_name}</span>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"<span style='color:#8892b0;font-size:0.85rem;'>{created}</span>", unsafe_allow_html=True)
            with col_c:
                st.markdown(f"<span style='color:#8892b0;font-size:0.85rem;'>{pages} pages</span>", unsafe_allow_html=True)
            with col_d:
                st.markdown(get_status_badge(status), unsafe_allow_html=True)
            with col_e:
                if st.button("Review →", key=f"btn_{lease_id}"):
                    st.session_state["review_lease_id"] = lease_id
                    st.rerun()

            st.markdown("<hr style='margin:8px 0;border-color:#1e2333;'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — REVIEW A LEASE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🔍 Review a Lease":
    leases = fetch_all_leases()
    if not leases:
        st.warning("No leases found. Process a lease first.")
        st.stop()

    options = {
        f"{(l.get('filename') or l.get('name') or 'Lease')} — {(l.get('clients') or {}).get('name', '')}": l["id"]
        for l in leases
    }

    default_label = None
    if "review_lease_id" in st.session_state:
        for label, lid in options.items():
            if lid == st.session_state["review_lease_id"]:
                default_label = label
                break

    selected_label = st.selectbox(
        "Select a lease to review:",
        list(options.keys()),
        index=list(options.keys()).index(default_label) if default_label else 0,
    )
    
    lease_id = options[selected_label]
    
    # Only clear review_lease_id if user manually selected a different lease
    # (Don't clear it if we just auto-selected it - let it persist so the lease stays selected)
    if "review_lease_id" in st.session_state and st.session_state["review_lease_id"] != lease_id:
        del st.session_state["review_lease_id"]
    lease    = fetch_lease(lease_id)
    fields   = fetch_fields(lease_id)

    if not lease:
        st.error("Lease not found.")
        st.stop()

    client_name = (lease.get("clients") or {}).get("name", "Unknown Client")
    filename    = lease.get("filename") or lease.get("name") or "—"
    status      = lease.get("status") or "READY FOR REVIEW"
    created     = format_date(lease.get("created_at"))

    st.markdown(f"""
    <div class="leaseai-header">
        <div>
            <h1>🔍 {filename}</h1>
            <span>{client_name} &nbsp;·&nbsp; Processed {created} &nbsp;·&nbsp; {lease.get('page_count','—')} pages</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_status, col_approve, col_flag, col_reset = st.columns([3, 1, 1, 1])
    with col_status:
        st.markdown(f"**Current Status:** {get_status_badge(status)}", unsafe_allow_html=True)
    with col_approve:
        if st.button("✅ Approve Lease", use_container_width=True):
            update_lease_status(lease_id, "APPROVED")
            st.success("Lease approved!")
            st.rerun()
    with col_flag:
        if st.button("🚩 Flag for Review", use_container_width=True):
            update_lease_status(lease_id, "FLAGGED")
            st.warning("Lease flagged.")
            st.rerun()
    with col_reset:
        if st.button("↩ Reset Status", use_container_width=True):
            update_lease_status(lease_id, "READY FOR REVIEW")
            st.info("Status reset.")
            st.rerun()

    st.markdown("---")
    
    # Professional Report Actions
    st.subheader("📄 Professional Reports & Exports")
    
    col_pdf, col_email, col_yardi, col_mri, col_csv, col_excel = st.columns([1, 1, 1, 1, 1, 1])
    
    with col_pdf:
        if st.button("📥 Generate PDF Report", use_container_width=True, type="primary"):
            try:
                from lease_report import generate_lease_abstract_pdf
                
                # Prepare extracted fields dictionary
                extracted_dict = {}
                for field in fields:
                    field_name = field.get("field_name", "Unknown")
                    extracted_dict[field_name] = {
                        "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                        "confidence": field.get("confidence", "MEDIUM")
                    }
                
                # Generate PDF
                pdf_bytes = generate_lease_abstract_pdf(lease, extracted_dict)
                
                # Log export
                try:
                    sb.table("export_history").insert({
                        "lease_id": lease_id,
                        "user_id": st.session_state.get("user_id"),
                        "export_type": "PDF_REPORT",
                        "export_format": "PDF",
                        "file_size_bytes": len(pdf_bytes),
                        "fields_exported": list(extracted_dict.keys())
                    }).execute()
                except:
                    pass  # Don't fail export if logging fails
                
                # Offer download
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"LeaseAbstract_{lease_id}_{lease.get('property_address', 'lease').replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF report generated successfully!")
                
            except Exception as e:
                st.error(f"Failed to generate PDF: {str(e)}")
    
    with col_email:
        if st.button("📧 Email Report to Client", use_container_width=True):
            try:
                from email_delivery import trigger_delivery_email
                
                success, message = trigger_delivery_email(lease_id, sb)
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Failed to send email: {str(e)}")
    
    with col_yardi:
        if st.button("📊 Export to Yardi", use_container_width=True):
            try:
                from pms_export import export_to_yardi
                
                # Prepare extracted fields dictionary
                extracted_dict = {}
                for field in fields:
                    field_name = field.get("field_name", "Unknown")
                    extracted_dict[field_name] = {
                        "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                        "confidence": field.get("confidence", "MEDIUM")
                    }
                
                # Generate Yardi CSV
                csv_bytes = export_to_yardi(lease, extracted_dict)
                
                # Log export
                try:
                    sb.table("export_history").insert({
                        "lease_id": lease_id,
                        "user_id": st.session_state.get("user_id"),
                        "export_type": "YARDI_CSV",
                        "export_format": "CSV",
                        "file_size_bytes": len(csv_bytes),
                        "fields_exported": list(extracted_dict.keys())
                    }).execute()
                except:
                    pass
                
                # Offer download
                st.download_button(
                    label="⬇️ Download Yardi CSV",
                    data=csv_bytes,
                    file_name=f"Yardi_Lease_{lease_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.success("✅ Yardi CSV generated!")
                
            except Exception as e:
                st.error(f"Failed to generate Yardi export: {str(e)}")
    
    with col_mri:
        if st.button("📊 Export to MRI", use_container_width=True):
            try:
                from pms_export import export_to_mri
                
                # Prepare extracted fields dictionary
                extracted_dict = {}
                for field in fields:
                    field_name = field.get("field_name", "Unknown")
                    extracted_dict[field_name] = {
                        "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                        "confidence": field.get("confidence", "MEDIUM")
                    }
                
                # Generate MRI CSV
                csv_bytes = export_to_mri(lease, extracted_dict)
                
                # Log export
                try:
                    sb.table("export_history").insert({
                        "lease_id": lease_id,
                        "user_id": st.session_state.get("user_id"),
                        "export_type": "MRI_CSV",
                        "export_format": "CSV",
                        "file_size_bytes": len(csv_bytes),
                        "fields_exported": list(extracted_dict.keys())
                    }).execute()
                except:
                    pass
                
                # Offer download
                st.download_button(
                    label="⬇️ Download MRI CSV",
                    data=csv_bytes,
                    file_name=f"MRI_Lease_{lease_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.success("✅ MRI CSV generated!")
                
            except Exception as e:
                st.error(f"Failed to generate MRI export: {str(e)}")
    
    with col_csv:
        if st.button("📄 Export to CSV", use_container_width=True):
            try:
                from generic_export import export_lease_to_csv
                
                # Prepare extracted fields dictionary
                extracted_dict = {}
                for field in fields:
                    field_name = field.get("field_name", "Unknown")
                    extracted_dict[field_name] = {
                        "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                        "confidence": field.get("confidence", "MEDIUM")
                    }
                
                # Generate Generic CSV
                csv_bytes = export_lease_to_csv(lease, extracted_dict)
                
                # Log export
                try:
                    sb.table("export_history").insert({
                        "lease_id": lease_id,
                        "user_id": st.session_state.get("user_id"),
                        "export_type": "GENERIC_CSV",
                        "export_format": "CSV",
                        "file_size_bytes": len(csv_bytes),
                        "fields_exported": list(extracted_dict.keys())
                    }).execute()
                except:
                    pass
                
                # Offer download
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_bytes,
                    file_name=f"LeaseAbstract_{lease_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.success("✅ Generic CSV generated! All 84+ fields included.")
                
            except Exception as e:
                st.error(f"Failed to generate CSV export: {str(e)}")
    
    with col_excel:
        if st.button("📊 Export to Excel", use_container_width=True):
            try:
                from generic_export import export_lease_to_excel
                
                # Prepare extracted fields dictionary
                extracted_dict = {}
                for field in fields:
                    field_name = field.get("field_name", "Unknown")
                    extracted_dict[field_name] = {
                        "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                        "confidence": field.get("confidence", "MEDIUM")
                    }
                
                # Generate Excel workbook
                excel_bytes = export_lease_to_excel(lease, extracted_dict)
                
                # Log export
                try:
                    sb.table("export_history").insert({
                        "lease_id": lease_id,
                        "user_id": st.session_state.get("user_id"),
                        "export_type": "EXCEL",
                        "export_format": "XLSX",
                        "file_size_bytes": len(excel_bytes),
                        "fields_exported": list(extracted_dict.keys())
                    }).execute()
                except:
                    pass
                
                # Offer download
                st.download_button(
                    label="⬇️ Download Excel",
                    data=excel_bytes,
                    file_name=f"LeaseAbstract_{lease_id}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.success("✅ Excel workbook generated! Includes Summary, Fields, and Critical Dates sheets.")
                
            except Exception as e:
                st.error(f"Failed to generate Excel export: {str(e)}")

    st.markdown("---")

    high_count = sum(1 for f in fields if (f.get("confidence") or "").upper() == "HIGH")
    med_count  = sum(1 for f in fields if (f.get("confidence") or "").upper() == "MEDIUM")
    low_count  = sum(1 for f in fields if (f.get("confidence") or "").upper() == "LOW")

    st.markdown(f"**{len(fields)} Extracted Fields** &nbsp;·&nbsp; "
                f"<span class='conf-high'>HIGH: {high_count}</span> &nbsp; "
                f"<span class='conf-med'>MEDIUM: {med_count}</span> &nbsp; "
                f"<span class='conf-low'>LOW: {low_count}</span>",
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    for i in range(0, len(fields), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(fields):
                break
            f = fields[i + j]

            raw_name    = f.get("field_name", "")
            clean_name  = raw_name.lstrip("0123456789. *").strip("* ")
            display_val = f.get("reviewed_value") or f.get("raw_value") or "NOT FOUND"
            conf        = f.get("confidence") or "HIGH"
            field_id    = f["id"]
            reviewed    = f.get("reviewed", False)

            with col:
                with st.expander(
                    f"{'✏️ ' if reviewed else ''}{clean_name}  |  {display_val[:40]}{'…' if len(display_val) > 40 else ''}",
                    expanded=False
                ):
                    st.markdown(f"{get_conf_badge(conf)} &nbsp; {'<span style=\"color:#60a5fa;font-size:0.75rem;\">EDITED</span>' if reviewed else ''}",
                                unsafe_allow_html=True)
                    new_val = st.text_area(
                        "Value",
                        value=display_val,
                        key=f"field_{field_id}",
                        height=80,
                        label_visibility="collapsed",
                    )
                    if st.button("💾 Save Change", key=f"save_{field_id}"):
                        update_field_value(field_id, new_val)
                        st.success("Saved!")
                        st.rerun()

    st.markdown("---")
    st.markdown(f"<span style='color:#555;font-size:0.75rem;'>Lease ID: {lease_id}</span>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — PROCESS NEW LEASE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "⬆️ Process New Lease":
    st.markdown("""
    <div class="leaseai-header">
        <div>
            <h1>⬆️ Process New Lease</h1>
            <span>Upload a PDF lease to run the extraction pipeline</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    clients_res = sb.table("clients").select("id, name").execute()
    clients     = clients_res.data or []
    client_map  = {c["name"]: c["id"] for c in clients}

    if not clients:
        st.warning("No clients found in database.")
        st.stop()

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload a lease PDF", type=["pdf"])
    with col2:
        selected_client = st.selectbox("Client", list(client_map.keys()))
        client_id = client_map[selected_client]

    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} ready — {round(uploaded_file.size / 1024)} KB")

        if st.button("🚀 Run Extraction Pipeline", use_container_width=True, type="primary"):
            import tempfile, subprocess

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            with st.spinner("Pipeline running — GPT-4o step takes 20-40 seconds..."):
                pipeline_path = os.path.join(os.path.dirname(__file__), "pipeline.py")
                result = subprocess.run(
                    [sys.executable, pipeline_path, tmp_path, client_id],
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(__file__),
                )

            os.unlink(tmp_path)

            if result.returncode == 0:
                st.success("✅ Extraction complete!")
                st.code(result.stdout, language="text")
                st.info("Go to **Review a Lease** to inspect the extracted fields.")
            else:
                st.error("Pipeline encountered an error:")
                st.code(result.stderr or result.stdout, language="text")

    st.markdown("---")
    st.markdown("""
    **What happens when you run the pipeline:**
    1. **Extract text** — reads all pages of the PDF
    2. **Scan for PII** — checks for sensitive patterns before sending to OpenAI
    3. **Create lease record** — saves the lease to the database
    4. **GPT-4o extraction** — reads the full lease and extracts all 25 fields
    5. **Save fields** — stores every field with confidence scores
    """)
