"""
LeaseAI - Bulk Lease Upload
Upload and process multiple lease PDFs simultaneously
"""

import streamlit as st
import tempfile
import os
from datetime import datetime
from supabase import create_client
import config
import concurrent.futures
from typing import List, Dict

sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

st.set_page_config(
    page_title="Bulk Upload | LeaseAI",
    page_icon="📦",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .bulk-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .upload-status {
        background: #1a1f2e;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .status-success { border-left: 4px solid #10b981; }
    .status-processing { border-left: 4px solid #3b82f6; }
    .status-error { border-left: 4px solid #ef4444; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="bulk-header">
    <h1>📦 Bulk Lease Upload</h1>
    <p>Upload and process multiple lease PDFs simultaneously</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "bulk_upload_results" not in st.session_state:
    st.session_state.bulk_upload_results = []

# Instructions
with st.expander("📖 How Bulk Upload Works", expanded=False):
    st.markdown("""
    ### Upload Multiple Leases at Once
    
    1. **Select PDFs** - Choose multiple lease PDF files (up to 10 at once)
    2. **Set Default Client** - All leases will be assigned to this client
    3. **Process** - Leases are extracted in parallel for faster processing
    4. **Review Results** - See success/failure status for each lease
    
    ### Processing Time
    - Single lease: ~30-60 seconds
    - 5 leases in parallel: ~60-90 seconds (not 5x!)
    - 10 leases in parallel: ~90-120 seconds
    
    ### Best Practices
    - Name your files clearly (property address or tenant name)
    - Keep file sizes reasonable (< 10MB each)
    - Upload in batches of 5-10 for best performance
    """)

st.markdown("---")

# Upload form
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📄 Select Lease PDFs")
    uploaded_files = st.file_uploader(
        "Upload multiple lease PDFs",
        type=['pdf'],
        accept_multiple_files=True,
        help="Select up to 10 PDF files to upload"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} files selected")
        
        # Show file list
        with st.expander(f"📋 Selected Files ({len(uploaded_files)})", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                size_mb = file.size / (1024 * 1024)
                st.markdown(f"{i}. **{file.name}** ({size_mb:.2f} MB)")

with col2:
    st.subheader("⚙️ Settings")
    
    # Get clients for dropdown
    try:
        clients_response = sb.table("clients").select("id, name").execute()
        clients = clients_response.data or []
        
        if clients:
            client_options = {client['name']: client['id'] for client in clients}
            selected_client = st.selectbox(
                "Default Client",
                options=list(client_options.keys()),
                help="All leases will be assigned to this client"
            )
            client_id = client_options[selected_client]
        else:
            st.warning("No clients found. Create a client first.")
            client_id = None
    except Exception as e:
        st.error(f"Error loading clients: {e}")
        client_id = None
    
    # Processing options
    parallel_processing = st.checkbox(
        "Parallel Processing",
        value=True,
        help="Process multiple leases simultaneously (faster)"
    )
    
    max_workers = st.slider(
        "Max Parallel Leases",
        min_value=1,
        max_value=5,
        value=3,
        help="Number of leases to process at once"
    ) if parallel_processing else 1

st.markdown("---")

# Process button
if uploaded_files and client_id:
    if len(uploaded_files) > 10:
        st.warning("⚠️ Maximum 10 files at once. Please select fewer files.")
    else:
        if st.button("🚀 Process All Leases", type="primary", use_container_width=True):
            from usage_limits import check_can_upload, increment_usage
            can_upload, limit_message, usage_info = check_can_upload(
                sb, client_id, st.session_state.get("user_role")
            )
            remaining = usage_info.get("remaining")
            if not can_upload:
                st.error(limit_message)
                st.stop()
            if remaining is not None and len(uploaded_files) > remaining:
                st.error(
                    f"This batch has {len(uploaded_files)} files but only {remaining} "
                    "abstractions remain this month. Remove files or upgrade on Billing."
                )
                st.stop()
            st.session_state.bulk_upload_results = []
            
            # Create progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            def process_single_lease(file_data, filename, client_id):
                """Process a single lease and return result"""
                try:
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(file_data)
                        tmp_path = tmp_file.name
                    
                    try:
                        # Import and run extraction
                        from extraction_pipeline import LeaseExtractionPipeline
                        
                        pipeline = LeaseExtractionPipeline()
                        
                        # Extract property address and tenant from filename if possible
                        property_address = filename.replace('.pdf', '').replace('_', ' ')
                        tenant_name = "To be reviewed"
                        
                        lease_id, extracted_fields = pipeline.process_lease(
                            pdf_path=tmp_path,
                            client_id=client_id,
                            supabase_client=sb,
                            property_address=property_address,
                            tenant_name=tenant_name,
                            filename=filename
                        )
                        
                        increment_usage(sb, client_id)
                        return {
                            "filename": filename,
                            "status": "success",
                            "lease_id": lease_id,
                            "field_count": len(extracted_fields),
                            "message": f"Extracted {len(extracted_fields)} fields"
                        }
                    
                    finally:
                        # Clean up temp file
                        os.unlink(tmp_path)
                
                except Exception as e:
                    return {
                        "filename": filename,
                        "status": "error",
                        "lease_id": None,
                        "field_count": 0,
                        "message": str(e)
                    }
            
            # Process leases
            total_files = len(uploaded_files)
            results = []
            
            if parallel_processing and max_workers > 1:
                # Parallel processing
                status_text.write(f"🔄 Processing {total_files} leases in parallel (max {max_workers} at once)...")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all tasks
                    future_to_file = {
                        executor.submit(
                            process_single_lease,
                            file.getvalue(),
                            file.name,
                            client_id
                        ): file.name
                        for file in uploaded_files
                    }
                    
                    # Collect results as they complete
                    completed = 0
                    for future in concurrent.futures.as_completed(future_to_file):
                        result = future.result()
                        results.append(result)
                        completed += 1
                        
                        # Update progress
                        progress = completed / total_files
                        progress_bar.progress(progress)
                        status_text.write(f"🔄 Processed {completed}/{total_files} leases...")
            
            else:
                # Sequential processing
                status_text.write(f"🔄 Processing {total_files} leases sequentially...")
                
                for i, file in enumerate(uploaded_files, 1):
                    result = process_single_lease(file.getvalue(), file.name, client_id)
                    results.append(result)
                    
                    # Update progress
                    progress = i / total_files
                    progress_bar.progress(progress)
                    status_text.write(f"🔄 Processed {i}/{total_files} leases...")
            
            # Store results
            st.session_state.bulk_upload_results = results
            
            # Summary
            progress_bar.progress(1.0)
            
            success_count = sum(1 for r in results if r['status'] == 'success')
            error_count = sum(1 for r in results if r['status'] == 'error')
            
            st.success(f"✅ Bulk upload complete! {success_count} successful, {error_count} failed")

# Display results
if st.session_state.bulk_upload_results:
    st.markdown("---")
    st.subheader("📊 Upload Results")
    
    results = st.session_state.bulk_upload_results
    
    # Summary metrics
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    total_fields = sum(r.get('field_count', 0) for r in results)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Processed", len(results))
    col2.metric("Successful", success_count)
    col3.metric("Failed", error_count)
    col4.metric("Total Fields", total_fields)
    
    st.markdown("---")
    
    # Detailed results
    for result in results:
        status = result['status']
        filename = result['filename']
        
        status_class = f"status-{status}"
        status_icon = "✅" if status == "success" else "❌"
        
        st.markdown(f"""
        <div class="upload-status {status_class}">
            <h4>{status_icon} {filename}</h4>
            <p>{result['message']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if status == "success":
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"Lease ID: {result['lease_id']}")
            with col2:
                if st.button("View Lease", key=f"view_{result['lease_id']}"):
                    st.session_state["review_lease_id"] = result['lease_id']
                    st.session_state["review_page"] = "🔍 Review a Lease"
                    st.switch_page("pages/2_📋_Lease_Review.py")
    
    # Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 View All Leases", use_container_width=True):
            st.switch_page("pages/2_📋_Lease_Review.py")
    
    with col2:
        if st.button("📤 Upload More", use_container_width=True):
            st.session_state.bulk_upload_results = []
            st.rerun()
    
    with col3:
        if st.button("🏠 Go to Home", use_container_width=True):
            st.switch_page("Home.py")

elif not uploaded_files:
    st.info("💡 Select multiple PDF files above to get started with bulk upload")

# Back button
st.markdown("---")
if st.button("← Back to Upload Lease"):
    st.switch_page("pages/1_📤_Upload_Lease.py")
