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

# Sidebar - Lease Selection
with st.sidebar:
    st.markdown("### 📋 Select Lease")
    
    # Get all leases with amendments
    leases_response = sb.table("leases").select("id, property_address, tenant_name").execute()
    leases = leases_response.data or []
    
    if not leases:
        st.warning("No leases found. Upload a lease first.")
        st.stop()
    
    # Lease selector
    lease_options = {f"{lease['property_address']} - {lease['tenant_name']}": lease['id'] 
                     for lease in leases}
    
    selected_lease_label = st.selectbox(
        "Choose a lease:",
        options=list(lease_options.keys())
    )
    
    selected_lease_id = lease_options[selected_lease_label]
    
    st.markdown("---")
    st.markdown("### 🔍 Query Date")
    query_date = st.date_input(
        "View lease as of date:",
        value=date.today(),
        help="See controlling clause values as they were on this date"
    )

# Main content
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Amendment Chain", 
    "🔍 Clause History", 
    "⚖️ Query Engine",
    "📤 Upload Amendment"
])

# ============================================================================
# TAB 1: Amendment Chain View
# ============================================================================
with tab1:
    st.markdown("### 📊 Amendment Chain")
    st.markdown("Complete history of amendments for this lease, in chronological order.")
    
    # Get amendment chain
    chain_response = sb.rpc("get_amendment_chain", {"p_lease_id": selected_lease_id}).execute()
    amendments = chain_response.data or []
    
    if not amendments:
        st.info("📝 No amendments found for this lease. Upload an amendment to get started.")
    else:
        st.success(f"Found {len(amendments)} amendment(s) for this lease")
        
        # Display amendment chain
        for i, amendment in enumerate(amendments):
            with st.expander(
                f"**Amendment #{amendment['amendment_number']}** • {amendment['amendment_date']} • "
                f"{len(amendment['modified_clauses'] or [])} clause(s) modified",
                expanded=(i == 0)
            ):
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
                clauses_response = sb.table("amendment_clauses").select("*").eq(
                    "amendment_id", amendment['amendment_id']
                ).execute()
                
                clauses = clauses_response.data or []
                
                if clauses:
                    st.markdown("---")
                    st.markdown("**🔄 Detailed Changes:**")
                    
                    for clause in clauses:
                        st.markdown(f"""
                        <div class="amendment-card">
                            <h4>{clause['clause_type']}</h4>
                            <span class="version-badge">{clause['modification_type']}</span>
                            
                            <div class="value-comparison">
                                <div class="value-box value-original">
                                    <strong style="color: #ef4444;">Before:</strong><br>
                                    {clause['original_value'] or 'N/A'}
                                </div>
                                <div class="value-box value-new">
                                    <strong style="color: #10b981;">After:</strong><br>
                                    {clause['new_value']}
                                </div>
                            </div>
                            
                            {f"<p><strong>Section:</strong> {clause['clause_section']}</p>" if clause['clause_section'] else ""}
                            <p><strong>Confidence:</strong> {clause['confidence']}</p>
                        </div>
                        """, unsafe_allow_html=True)

# ============================================================================
# TAB 2: Clause History Timeline
# ============================================================================
with tab2:
    st.markdown("### 🔍 Clause History Timeline")
    st.markdown("Track how specific clauses evolved through amendments over time.")
    
    # Get all clause types for this lease
    history_response = sb.table("lease_clause_history").select(
        "clause_type"
    ).eq("lease_id", selected_lease_id).execute()
    
    clause_types = list(set([item['clause_type'] for item in (history_response.data or [])]))
    
    if not clause_types:
        st.info("📝 No clause history available yet. Upload amendments to track clause evolution.")
    else:
        # Clause selector
        selected_clause = st.selectbox(
            "Select clause to view history:",
            options=sorted(clause_types)
        )
        
        # Get full history for this clause
        clause_history = sb.table("lease_clause_history").select("*").eq(
            "lease_id", selected_lease_id
        ).eq("clause_type", selected_clause).order("version_number").execute()
        
        versions = clause_history.data or []
        
        st.markdown(f"### Timeline: {selected_clause}")
        st.markdown(f"**{len(versions)} version(s)** recorded")
        
        # Display timeline
        st.markdown('<div class="clause-timeline">', unsafe_allow_html=True)
        
        for version in versions:
            is_current = version['is_current']
            badge_html = '<span class="current-badge">CURRENT</span>' if is_current else '<span class="superseded-badge">SUPERSEDED</span>'
            
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <h4>Version {version['version_number']} {badge_html}</h4>
                <p><strong>Effective:</strong> {version['effective_from']} {f"to {version['effective_to']}" if version['effective_to'] else "onwards"}</p>
                <p><strong>Source:</strong> {version['source_document_type']}</p>
                <p><strong>Modification:</strong> {version['modification_type'] or 'Original'}</p>
                <div style="background: #0f1117; padding: 1rem; border-radius: 8px; margin-top: 0.5rem;">
                    <strong>Value:</strong><br>
                    {version['clause_value']}
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
    
    with col1:
        # Get available clause types
        history_response = sb.table("lease_clause_history").select(
            "clause_type"
        ).eq("lease_id", selected_lease_id).execute()
        
        clause_types = sorted(list(set([item['clause_type'] for item in (history_response.data or [])])))
        
        if not clause_types:
            st.warning("No clause history available. Upload amendments first.")
            st.stop()
        
        query_clause = st.selectbox(
            "Select clause to query:",
            options=clause_types
        )
    
    with col2:
        query_as_of = st.date_input(
            "As of date:",
            value=query_date,
            help="Find the controlling value of this clause on this specific date"
        )
    
    if st.button("🔍 Query Controlling Value", type="primary"):
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
                <h3>{query_clause}</h3>
                <p><strong>Version:</strong> {controlling['version_number']}</p>
                <p><strong>Source:</strong> {controlling['source_type']}</p>
                
                <div style="background: #10b981; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                            padding: 1.5rem; border-radius: 8px; margin-top: 1rem; color: white;">
                    <h4 style="margin: 0; color: white;">Controlling Value:</h4>
                    <p style="font-size: 1.1rem; margin-top: 0.5rem; color: white;">{controlling['clause_value']}</p>
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
# TAB 4: Upload Amendment
# ============================================================================
with tab4:
    st.markdown("### 📤 Upload Amendment")
    st.markdown("Upload a lease amendment to add it to the amendment chain and update clause history.")
    
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        "Upload Amendment PDF",
        type=['pdf'],
        help="Upload the amendment document (PDF format)"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        amendment_number = st.number_input(
            "Amendment Number",
            min_value=1,
            value=1,
            help="1st Amendment, 2nd Amendment, etc."
        )
    
    with col2:
        amendment_date = st.date_input(
            "Amendment Date",
            value=date.today(),
            help="Date the amendment was signed"
        )
    
    if st.button("🚀 Process Amendment", type="primary", disabled=(uploaded_file is None)):
        if uploaded_file:
            with st.spinner("Processing amendment with OCR and AI extraction..."):
                # Save uploaded file temporarily
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Process amendment with enhanced v2 processor
                    from amendment_processor_v2 import AmendmentProcessorV2
                    
                    processor = AmendmentProcessorV2()
                    amendment_id, extracted_fields = processor.process_amendment(
                        pdf_path=tmp_path,
                        lease_id=selected_lease_id,
                        supabase_client=sb,
                        filename=uploaded_file.name
                    )
                    
                    st.success(f"✅ Amendment processed successfully!")
                    st.success(f"Amendment ID: {amendment_id}")
                    
                    st.markdown("### 📊 Extraction Results")
                    st.json(extracted_fields)
                    
                    st.info("💡 Go to the **Amendment Chain** tab to see the updated amendment chain!")
                    
                except Exception as e:
                    st.error(f"❌ Error processing amendment: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                
                finally:
                    # Clean up temp file
                    os.unlink(tmp_path)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p><strong>Amendment Resolution Graph™</strong></p>
    <p>Proprietary IP asset • Patent-pending architecture • Enterprise-grade clause tracking</p>
    <p style="font-size: 0.85rem;">© 2026 LeaseAI • Built in Vancouver, BC</p>
</div>
""", unsafe_allow_html=True)
