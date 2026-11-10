"""
LeaseAI - Amendment Resolution Graph™
Visual interface for viewing and querying amendment chains and clause history
The proprietary $5.6M IP asset that differentiates LeaseAI
"""

import streamlit as st
import sys
from datetime import datetime, date
from supabase import create_client
import config
from amendment_graph_helpers import (
    clause_types_from_history,
    html_text,
    lease_client_name,
    lease_option_label,
    sync_prepared_for,
)
from asc842_amendment import enrich_lease_client
from amendment_report import (
    abstract_filename,
    build_amendment_resolution_model,
    generate_amendment_resolution_pdf,
)
from current_lease_position import (
    build_position_from_graph,
    generate_current_lease_position_pdf,
    position_filename,
)
from report_sources import clause_source, format_source_line

# Initialize Supabase
sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

# Page config
st.set_page_config(
    page_title="Amendment Resolution Graph™ | LeaseAI",
    page_icon="🔗",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .amendment-graph-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .amendment-card {
        background: #1a1f2e;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .clause-timeline {
        border-left: 3px solid #667eea;
        padding-left: 1.5rem;
        margin-left: 1rem;
    }
    .timeline-item {
        position: relative;
        padding-bottom: 2rem;
    }
    .timeline-dot {
        position: absolute;
        left: -1.85rem;
        width: 1rem;
        height: 1rem;
        background: #667eea;
        border-radius: 50%;
        border: 3px solid #1a1f2e;
    }
    .version-badge {
        background: #667eea;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .current-badge {
        background: #10b981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .superseded-badge {
        background: #6b7280;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .value-comparison {
        display: flex;
        gap: 2rem;
        margin: 1rem 0;
    }
    .value-box {
        flex: 1;
        padding: 1rem;
        border-radius: 8px;
        background: #0f1117;
    }
    .value-original {
        border-left: 4px solid #ef4444;
    }
    .value-new {
        border-left: 4px solid #10b981;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="amendment-graph-header">
    <h1>🔗 Amendment Resolution Graph™</h1>
    <p>Proprietary clause tracking and version control system</p>
    <p style="font-size: 0.9rem; opacity: 0.9;">Map amendment chains • Track clause evolution • Query controlling values at any date</p>
</div>
""", unsafe_allow_html=True)


def process_amendment_upload(uploaded_file, lease_id: str) -> None:
    """Extract and store one amendment PDF against the selected lease."""
    import os
    import tempfile

    with st.spinner("Processing amendment with OCR and AI extraction..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        try:
            from amendment_processor_v2 import AmendmentProcessorV2

            processor = AmendmentProcessorV2()
            amendment_id, extracted_fields = processor.process_amendment(
                pdf_path=tmp_path,
                lease_id=lease_id,
                supabase_client=sb,
                filename=uploaded_file.name,
            )
            st.success("✅ Amendment processed successfully!")
            st.success(f"Amendment ID: {amendment_id}")
            st.caption("If this amendment number was already on the lease, the previous extract was replaced.")
            st.markdown("### 📊 Extraction Results")
            st.json(extracted_fields)
            st.info("💡 Go to the **Amendment Chain** tab to see the updated amendment chain!")
        except Exception as e:
            st.error(f"❌ Error processing amendment: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            os.unlink(tmp_path)


def fetch_graph_report_inputs(lease_id: str):
    """Load clause history, amendment chain, and recorded clause changes."""
    errors = []
    history = []
    amendments = []
    clause_changes = []
    try:
        history = (
            sb.table("lease_clause_history")
            .select("*")
            .eq("lease_id", lease_id)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        errors.append(f"Could not load clause history for the report: {exc}")
    try:
        amendments = (
            sb.rpc("get_amendment_chain", {"p_lease_id": lease_id}).execute().data or []
        )
    except Exception as exc:
        errors.append(f"Could not load amendment chain for the report: {exc}")
    for amendment in amendments:
        amendment_id = amendment.get("amendment_id")
        if not amendment_id:
            continue
        try:
            clause_changes.extend(
                sb.table("amendment_clauses")
                .select("*")
                .eq("amendment_id", amendment_id)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            errors.append(f"Could not load recorded amendment clauses: {exc}")
        try:
            full = (
                sb.table("amendments")
                .select("extracted_data, effective_date")
                .eq("id", amendment_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if full:
                amendment["extracted_data"] = full[0].get("extracted_data")
                if full[0].get("effective_date") and not amendment.get("effective_date"):
                    amendment["effective_date"] = full[0]["effective_date"]
        except Exception:
            pass
    return history, amendments, clause_changes, errors


def render_amendment_upload(lease_id: str, key_prefix: str) -> None:
    """File picker for an addendum. Created before chain/history tabs so those cannot hide it."""
    uploaded_file = st.file_uploader(
        "Upload Amendment PDF",
        type=["pdf"],
        help="Upload the amendment or addendum document (PDF format)",
        key=f"{key_prefix}_amendment_pdf_{lease_id}",
    )
    col1, col2 = st.columns(2)
    with col1:
        st.number_input(
            "Amendment Number",
            min_value=1,
            value=1,
            help="1st Amendment, 2nd Amendment, etc.",
            key=f"{key_prefix}_amendment_number_{lease_id}",
        )
    with col2:
        st.date_input(
            "Amendment Date",
            value=date.today(),
            help="Date the amendment was signed",
            key=f"{key_prefix}_amendment_date_{lease_id}",
        )
    if st.button(
        "🚀 Process Amendment",
        type="primary",
        disabled=(uploaded_file is None),
        key=f"{key_prefix}_process_amendment_{lease_id}",
    ):
        if uploaded_file:
            process_amendment_upload(uploaded_file, lease_id)


# Sidebar - Lease Selection
with st.sidebar:
    st.markdown("### 📋 Select Lease")
    
    # Get all leases with amendments
    try:
        leases_response = sb.table("leases").select(
            "id, property_address, tenant_name, filename, client_id, clients(name, company_name)"
        ).execute()
        leases = leases_response.data or []
    except Exception:
        leases_response = sb.table("leases").select(
            "id, property_address, tenant_name, client_id"
        ).execute()
        leases = leases_response.data or []
    
    if not leases:
        st.warning("No leases found. Upload a lease first.")
        st.stop()
    
    # Lease selector — unique labels so two similar addresses cannot collapse.
    lease_options = {lease_option_label(lease): lease["id"] for lease in leases}
    
    selected_lease_label = st.selectbox(
        "Choose a lease:",
        options=list(lease_options.keys())
    )
    
    selected_lease_id = lease_options[selected_lease_label]
    selected_lease = enrich_lease_client(
        sb,
        next((lease for lease in leases if lease.get("id") == selected_lease_id), {}),
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Query Date")
    query_date = st.date_input(
        "View lease as of date:",
        value=date.today(),
        help="See controlling clause values as they were on this date"
    )

# Main content
tab1, tab2, tab3, tab5, tab6, tab4 = st.tabs([
    "📊 Amendment Chain",
    "🔍 Clause History",
    "⚖️ Query Engine",
    "📄 Resolution Abstract",
    "📍 Current Position",
    "📤 Upload Amendment",
])

# Upload tab first so a later chain/history crash cannot unmount the file picker.
# ============================================================================
# TAB 4: Upload Amendment
# ============================================================================
with tab4:
    st.markdown("### 📤 Upload Amendment")
    st.markdown("Upload a lease amendment or addendum to add it to the amendment chain.")
    st.markdown("---")
    render_amendment_upload(selected_lease_id, "tab")

# ============================================================================
# TAB 1: Amendment Chain View
# ============================================================================
with tab1:
    st.markdown("### 📊 Amendment Chain")
    st.markdown("Complete history of amendments for this lease, in chronological order.")
    
    # Get amendment chain. Never let a lease-specific RPC error hide the upload tab.
    try:
        chain_response = sb.rpc("get_amendment_chain", {"p_lease_id": selected_lease_id}).execute()
        amendments = chain_response.data or []
    except Exception as e:
        amendments = []
        st.error(f"Could not load amendment chain: {e}")
    
    if not amendments:
        st.info("📝 No amendments found for this lease. Upload an amendment to get started.")
    else:
        st.success(f"Found {len(amendments)} amendment(s) for this lease")
        
        # Display amendment chain
        for i, amendment in enumerate(amendments):
            try:
                clause_count = len(amendment.get("modified_clauses") or [])
                expander_label = (
                    f"**Amendment #{html_text(amendment.get('amendment_number'))}** • "
                    f"{html_text(amendment.get('amendment_date'))} • "
                    f"{clause_count} clause(s) modified"
                )
            except Exception:
                expander_label = f"Amendment {i + 1}"
            with st.expander(expander_label, expanded=(i == 0)):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Amendment Number", f"#{amendment['amendment_number']}")
                
                with col2:
                    st.metric("Date", amendment['amendment_date'])
                
                with col3:
                    status_color = {
                        "READY FOR REVIEW": "🟡",
                        "APPROVED": "🟢",
                        "PROCESSING": "🔵",
                        "FLAGGED": "🔴"
                    }.get(amendment['status'], "⚪")
                    st.metric("Status", f"{status_color} {amendment['status']}")
                
                st.markdown("---")
                
                # Modified clauses
                st.markdown("**📝 Modified Clauses:**")
                if amendment['modified_clauses']:
                    for clause in amendment['modified_clauses']:
                        st.markdown(f"- {clause}")
                else:
                    st.info("No clause modifications recorded")
                
                # Get detailed clause modifications
                try:
                    clauses_response = sb.table("amendment_clauses").select("*").eq(
                        "amendment_id", amendment.get("amendment_id")
                    ).execute()
                    clauses = clauses_response.data or []
                except Exception as clause_error:
                    clauses = []
                    st.error(f"Could not load clause details: {clause_error}")
                
                if clauses:
                    st.markdown("---")
                    st.markdown("**🔄 Detailed Changes:**")
                    
                    for clause in clauses:
                        section_html = (
                            f"<p><strong>Section:</strong> {html_text(clause['clause_section'])}</p>"
                            if clause.get("clause_section")
                            else ""
                        )
                        st.markdown(f"""
                        <div class="amendment-card">
                            <h4>{html_text(clause.get('clause_type'))}</h4>
                            <span class="version-badge">{html_text(clause.get('modification_type'))}</span>
                            
                            <div class="value-comparison">
                                <div class="value-box value-original">
                                    <strong style="color: #ef4444;">Before:</strong><br>
                                    {html_text(clause.get('original_value'))}
                                </div>
                                <div class="value-box value-new">
                                    <strong style="color: #10b981;">After:</strong><br>
                                    {html_text(clause.get('new_value'))}
                                </div>
                            </div>
                            
                            {section_html}
                            <p><strong>Confidence:</strong> {html_text(clause.get('confidence'))}</p>
                        </div>
                        """, unsafe_allow_html=True)

# ============================================================================
# TAB 2: Clause History Timeline
# ============================================================================
with tab2:
    st.markdown("### 🔍 Clause History Timeline")
    st.markdown("Track how specific clauses evolved through amendments over time.")
    
    # Get all clause types for this lease
    try:
        history_response = sb.table("lease_clause_history").select(
            "clause_type"
        ).eq("lease_id", selected_lease_id).execute()
        history_rows = history_response.data or []
    except Exception as e:
        history_rows = []
        st.error(f"Could not load clause history: {e}")

    clause_types = clause_types_from_history(history_rows)
    
    if not clause_types:
        st.info("📝 No clause history available yet. Upload an amendment to start tracking clause evolution.")
    else:
        # Clause selector
        selected_clause = st.selectbox(
            "Select clause to view history:",
            options=sorted(clause_types),
            key=f"history_clause_{selected_lease_id}",
        )
        
        # Get full history for this clause
        try:
            clause_history = sb.table("lease_clause_history").select("*").eq(
                "lease_id", selected_lease_id
            ).eq("clause_type", selected_clause).order("version_number").execute()
            versions = clause_history.data or []
        except Exception as e:
            versions = []
            st.error(f"Could not load clause versions: {e}")
        
        st.markdown(f"### Timeline: {selected_clause}")
        st.markdown(f"**{len(versions)} version(s)** recorded")
        
        # Display timeline
        st.markdown('<div class="clause-timeline">', unsafe_allow_html=True)
        
        for version in versions:
            is_current = version.get("is_current")
            badge_html = '<span class="current-badge">CURRENT</span>' if is_current else '<span class="superseded-badge">SUPERSEDED</span>'
            
            effective_to = (
                f"to {html_text(version['effective_to'])}"
                if version.get("effective_to")
                else "onwards"
            )
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <h4>Version {html_text(version.get('version_number'))} {badge_html}</h4>
                <p><strong>Effective:</strong> {html_text(version.get('effective_from'))} {effective_to}</p>
                <p><strong>Source:</strong> {html_text(version.get('source_document_type'))}</p>
                <p><strong>Modification:</strong> {html_text(version.get('modification_type') or 'Original')}</p>
                <div style="background: #0f1117; padding: 1rem; border-radius: 8px; margin-top: 0.5rem;">
                    <strong>Value:</strong><br>
                    {html_text(version.get('clause_value'))}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# TAB 3: Query Engine
# ============================================================================
with tab3:
    st.markdown("### ⚖️ Amendment Resolution Query Engine")
    st.markdown("**The core of the Amendment Resolution Graph™** - Query controlling clause values at any point in time.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)

    try:
        history_response = sb.table("lease_clause_history").select(
            "clause_type"
        ).eq("lease_id", selected_lease_id).execute()
        query_clause_types = clause_types_from_history(history_response.data)
    except Exception as e:
        query_clause_types = []
        st.error(f"Could not load clause history: {e}")
    
    with col1:
        if not query_clause_types:
            st.warning(
                "No clause history for this lease yet. You can still upload an "
                "amendment in the **Upload Amendment** tab — clause history is not required first."
            )
            query_clause = None
        else:
            query_clause = st.selectbox(
                "Select clause to query:",
                options=query_clause_types,
                key=f"query_clause_{selected_lease_id}",
            )
    
    with col2:
        query_as_of = st.date_input(
            "As of date:",
            value=query_date,
            help="Find the controlling value of this clause on this specific date",
            key=f"query_as_of_{selected_lease_id}",
        )
    
    if query_clause and st.button(
        "🔍 Query Controlling Value",
        type="primary",
        key=f"query_btn_{selected_lease_id}",
    ):
        # Execute query
        result = sb.rpc("get_controlling_clause", {
            "p_lease_id": selected_lease_id,
            "p_clause_type": query_clause,
            "p_as_of_date": query_as_of.isoformat()
        }).execute()
        
        if result.data:
            controlling = result.data[0]
            
            st.success(f"✅ Found controlling value for **{query_clause}** as of **{query_as_of}**")
            
            st.markdown(f"""
            <div class="amendment-card">
                <h3>{html_text(query_clause)}</h3>
                <p><strong>Version:</strong> {html_text(controlling.get('version_number'))}</p>
                <p><strong>Source:</strong> {html_text(controlling.get('source_type'))}</p>
                
                <div style="background: #10b981; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                            padding: 1.5rem; border-radius: 8px; margin-top: 1rem; color: white;">
                    <h4 style="margin: 0; color: white;">Controlling Value:</h4>
                    <p style="font-size: 1.1rem; margin-top: 0.5rem; color: white;">{html_text(controlling.get('clause_value'))}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**💡 What this means:**")
            st.info(f"""
            On {query_as_of}, the controlling value for **{query_clause}** was determined by 
            **{controlling['source_type']} Version {controlling['version_number']}**.
            
            This is the legally binding value that was in effect at that time, automatically
            resolved through the amendment chain by the Amendment Resolution Graph™.
            """)
        else:
            st.error(f"❌ No controlling value found for {query_clause} on {query_as_of}")
            st.info("This clause may not have been effective on that date, or no history is recorded.")

# ============================================================================
# TAB 5: Client Amendment Report
# ============================================================================
with tab5:
    st.markdown("### 📄 Amendment Resolution Abstract")
    st.markdown(
        "The value of Amendment Resolution Graph™ is **controlling-language certainty**: "
        "what governs as of a stated date, after every amendment is applied, and what "
        "original language it replaced. This is the exhibit the client files with "
        "estoppels, lender packages, billing, and audit workpapers."
    )
    st.markdown("---")

    sync_prepared_for(
        st.session_state,
        lease_id=selected_lease_id,
        client_name=lease_client_name(selected_lease),
        value_key="abstract_prepared_for",
        lease_key="abstract_prepared_lease_id",
    )
    prepared_for = st.text_input(
        "Prepared for (client / customer)",
        help="Always the client on the selected lease. Switching leases replaces this name.",
        key="abstract_prepared_for",
    )

    report_history, report_amendments, report_clause_changes, report_errors = fetch_graph_report_inputs(
        selected_lease_id
    )
    for message in report_errors:
        st.error(message)

    report_model = build_amendment_resolution_model(
        selected_lease,
        report_amendments,
        report_history,
        as_of=query_date.isoformat(),
        prepared_for=prepared_for,
        amendment_clauses=report_clause_changes,
    )
    value = report_model["value"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Amendments resolved", value["amendments_resolved"])
    c2.metric("Clauses superseded", value["clauses_superseded"])
    c3.metric("Still original", value["clauses_still_original"])
    c4.metric("Clauses tracked", value["clauses_tracked"])
    st.caption(f"Controlling as of {value['as_of']} · Prepared for {value['prepared_for']}")

    if report_model["changed_clauses"]:
        st.markdown("#### Schedule A — Controlling language vs original")
        for clause in report_model["changed_clauses"]:
            title = (
                f"{clause.get('change_number')}. {clause['clause_type']} — "
                f"{clause.get('governing_label')} — {clause.get('change_summary')}"
            )
            with st.expander(title, expanded=True):
                st.caption(
                    f"{clause.get('modification_type')}, effective {clause.get('effective_from')}"
                )
                st.markdown(f"**Changed:** {clause.get('change_summary')}")
                st.markdown("**Original lease**")
                st.write(clause["original_value"])
                st.caption(format_source_line(clause_source(clause, "original")))
                st.markdown(f"**Now governed by {clause.get('governing_label')}**")
                st.write(clause["governing_value"])
                st.caption(format_source_line(clause_source(clause, "governing")))
    else:
        st.info("No clause has been superseded yet. The original lease language still governs.")

    if report_model["unchanged_clauses"]:
        with st.expander(
            f"Schedule B — Still governed by the original lease ({len(report_model['unchanged_clauses'])})",
            expanded=False,
        ):
            for clause in report_model["unchanged_clauses"]:
                st.markdown(f"**{clause['clause_type']}**")
                st.write(clause["governing_value"])
                st.caption(format_source_line(clause_source(clause, "governing")))

    try:
        report_pdf = generate_amendment_resolution_pdf(report_model)
        st.download_button(
            "⬇️ Download Amendment Resolution Abstract (PDF)",
            data=report_pdf,
            file_name=abstract_filename(report_model),
            mime="application/pdf",
            key=f"amendment_report_pdf_{selected_lease_id}",
        )

        default_email = ""
        client_id = selected_lease.get("client_id")
        if client_id:
            try:
                client_row = (
                    sb.table("clients")
                    .select("email")
                    .eq("id", client_id)
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if client_row:
                    default_email = client_row[0].get("email") or ""
            except Exception:
                default_email = ""

        st.markdown("#### Email this abstract to the client")
        recipient_email = st.text_input(
            "Client email",
            value=default_email,
            placeholder="client@company.com",
            key=f"abstract_email_{selected_lease_id}",
        )
        if st.button(
            "📧 Email Amendment Resolution Abstract",
            key=f"abstract_email_send_{selected_lease_id}",
        ):
            from email_delivery import send_amendment_abstract_email

            sent = send_amendment_abstract_email(
                recipient_email=recipient_email.strip(),
                recipient_name=prepared_for or report_model["tenant_name"],
                property_address=report_model["property_address"],
                tenant_name=report_model["tenant_name"],
                pdf_bytes=report_pdf,
                filename=abstract_filename(report_model),
                as_of=report_model["as_of"],
                amendments_resolved=value["amendments_resolved"],
                clauses_superseded=value["clauses_superseded"],
            )
            if sent:
                st.success(f"Abstract emailed to {recipient_email.strip()}")
            else:
                st.error(
                    "Could not send the email. Check the address and that SendGrid is configured."
                )
    except Exception as e:
        st.error(f"Could not build the amendment report PDF: {e}")

# ============================================================================
# TAB 6: Current Lease Position
# ============================================================================
with tab6:
    st.markdown("### 📍 Current Lease Position")
    st.markdown(
        "The Amendment Resolution Abstract says **which language governs**. "
        "This report says **what those terms mean in money and dates**. "
        "Calculated totals are labeled Calculated — they are not amounts the "
        "parties wrote into the amendment unless Status is Extracted or Amended."
    )
    st.markdown("---")

    sync_prepared_for(
        st.session_state,
        lease_id=selected_lease_id,
        client_name=lease_client_name(selected_lease),
        value_key="position_prepared_for",
        lease_key="position_prepared_lease_id",
    )
    position_prepared_for = st.text_input(
        "Prepared for (client / customer)",
        help="Always the client on the selected lease. Switching leases replaces this name.",
        key="position_prepared_for",
    )

    history, amendments, clause_changes, position_errors = fetch_graph_report_inputs(
        selected_lease_id
    )
    for message in position_errors:
        st.error(message)

    position_model = build_position_from_graph(
        selected_lease,
        amendments,
        history,
        as_of=query_date.isoformat(),
        prepared_for=position_prepared_for,
        amendment_clauses=clause_changes,
    )
    position_value = position_model["value"]

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Amendments applied", position_value["amendments_resolved"])
    p2.metric("Fields reported", position_value["fields_reported"])
    p3.metric("Calculated fields", position_value["calculated_fields"])
    p4.metric("Review required", position_value["review_required"])
    st.caption(
        f"Position as of {position_value['as_of']} · Prepared for {position_value['prepared_for']}"
    )

    if position_model["review_flags"]:
        st.warning("Review required before relying on a calculated total:")
        for flag in position_model["review_flags"]:
            st.write(f"- {flag}")

    if position_model["rows"]:
        st.dataframe(
            [
                {
                    "Field": row["field"],
                    "Current": row["current_value"],
                    "Previous": row["previous_value"],
                    "Effective": row["effective_date"],
                    "Status": row["status"],
                    "Calculation": row["calculation"],
                }
                for row in position_model["rows"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("Source citations", expanded=False):
            for row in position_model["rows"]:
                st.markdown(f"**{row['field']}** — {row['status']}")
                st.caption(row["source"])
    else:
        st.info("No governing terms are on file yet. Process the lease and any amendments first.")

    try:
        position_pdf = generate_current_lease_position_pdf(position_model)
        st.download_button(
            "⬇️ Download Current Lease Position (PDF)",
            data=position_pdf,
            file_name=position_filename(position_model),
            mime="application/pdf",
            key=f"position_report_pdf_{selected_lease_id}",
        )

        default_email = ""
        client_id = selected_lease.get("client_id")
        if client_id:
            try:
                client_row = (
                    sb.table("clients")
                    .select("email")
                    .eq("id", client_id)
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if client_row:
                    default_email = client_row[0].get("email") or ""
            except Exception:
                default_email = ""

        st.markdown("#### Email this position report to the client")
        position_email = st.text_input(
            "Client email",
            value=default_email,
            placeholder="client@company.com",
            key=f"position_email_{selected_lease_id}",
        )
        if st.button(
            "📧 Email Current Lease Position",
            key=f"position_email_send_{selected_lease_id}",
        ):
            from email_delivery import send_current_position_email

            sent = send_current_position_email(
                recipient_email=position_email.strip(),
                recipient_name=position_prepared_for or position_model["tenant_name"],
                property_address=position_model["property_address"],
                tenant_name=position_model["tenant_name"],
                pdf_bytes=position_pdf,
                filename=position_filename(position_model),
                as_of=position_model["as_of"],
                calculated_fields=position_value["calculated_fields"],
                review_required=position_value["review_required"],
            )
            if sent:
                st.success(f"Current Lease Position emailed to {position_email.strip()}")
            else:
                st.error(
                    "Could not send the email. Check the address and that SendGrid is configured."
                )
    except Exception as e:
        st.error(f"Could not build the Current Lease Position PDF: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p><strong>Amendment Resolution Graph™</strong></p>
    <p>Proprietary IP asset • Patent-pending architecture • Enterprise-grade clause tracking</p>
    <p style="font-size: 0.85rem;">© 2026 LeaseAI • Built in Vancouver, BC</p>
</div>
""", unsafe_allow_html=True)
