"""
LeaseAI - Bulk Lease Upload
Upload and process multiple lease PDFs. Files are queued, then extracted
one at a time so a timeout or Streamlit rerun cannot drop the rest.
"""

import streamlit as st
from supabase import create_client
import config
from bulk_upload import (
    bulk_queue_finished,
    clear_bulk_queue,
    next_bulk_job,
    process_one_job,
    queue_bulk_jobs,
    record_bulk_result,
)

sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

st.set_page_config(
    page_title="Bulk Upload | LeaseAI",
    page_icon="📦",
    layout="wide",
)

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

st.markdown("""
<div class="bulk-header">
    <h1>📦 Bulk Lease Upload</h1>
    <p>Upload and process multiple lease PDFs. Each file is extracted in order.</p>
</div>
""", unsafe_allow_html=True)

if "bulk_upload_results" not in st.session_state:
    st.session_state.bulk_upload_results = []
if "bulk_jobs" not in st.session_state:
    st.session_state.bulk_jobs = []
if "bulk_job_index" not in st.session_state:
    st.session_state.bulk_job_index = 0


def _supabase_factory():
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


# Drain one queued lease per script run. Remaining files stay in session_state.
pending_job = next_bulk_job(st.session_state)
if pending_job:
    jobs = st.session_state.bulk_jobs
    index = st.session_state.bulk_job_index
    st.info(f"Processing {index + 1} of {len(jobs)}: **{pending_job['filename']}**")
    st.progress(index / len(jobs) if jobs else 0)
    with st.spinner(f"Extracting {pending_job['filename']}... this can take 30-60 seconds."):
        result = process_one_job(pending_job, supabase_factory=_supabase_factory)
    record_bulk_result(st.session_state, result)
    if result["status"] == "success":
        st.success(f"{pending_job['filename']}: {result['message']}")
    else:
        st.error(f"{pending_job['filename']}: {result['message']}")
    st.rerun()

if bulk_queue_finished(st.session_state):
    st.progress(1.0)
    results = st.session_state.bulk_upload_results
    success_count = sum(1 for row in results if row["status"] == "success")
    error_count = sum(1 for row in results if row["status"] == "error")
    st.success(f"Bulk upload complete. {success_count} successful, {error_count} failed.")
    clear_bulk_queue(st.session_state)

with st.expander("📖 How Bulk Upload Works", expanded=False):
    st.markdown("""
    ### Upload Multiple Leases at Once

    1. **Select PDFs** - Choose multiple lease PDF files (up to 10 at once)
    2. **Set Default Client** - All leases will be assigned to this client
    3. **Process** - Files are copied into a queue, then extracted one by one
    4. **Review Results** - See success/failure status for each lease

    Leases are processed **one after another** on purpose. Running three GPT
    extractions in the same Streamlit request dropped remaining files when a
    timeout, rate limit, or page rerun hit.
    """)

st.markdown("---")

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
        with st.expander(f"📋 Selected Files ({len(uploaded_files)})", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                size_mb = file.size / (1024 * 1024)
                st.markdown(f"{i}. **{file.name}** ({size_mb:.2f} MB)")

with col2:
    st.subheader("⚙️ Settings")

    try:
        from query_cache import cached
        clients = cached(
            "bulk_upload_clients",
            120,
            lambda: (sb.table("clients").select("id, name").execute().data or []),
        )

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

    st.caption("Files are extracted one at a time so every selected lease is attempted.")

st.markdown("---")

if uploaded_files and client_id:
    if len(uploaded_files) > 10:
        st.warning("⚠️ Maximum 10 files at once. Please select fewer files.")
    elif st.button("🚀 Process All Leases", type="primary", use_container_width=True):
        from usage_limits import check_can_upload
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
        jobs = queue_bulk_jobs(st.session_state, uploaded_files, client_id)
        st.info(f"Queued {len(jobs)} leases. Starting extraction...")
        st.rerun()

if st.session_state.bulk_upload_results:
    st.markdown("---")
    st.subheader("📊 Upload Results")

    results = st.session_state.bulk_upload_results

    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    total_fields = sum(r.get('field_count', 0) for r in results)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Processed", len(results))
    col2.metric("Successful", success_count)
    col3.metric("Failed", error_count)
    col4.metric("Total Fields", total_fields)

    st.markdown("---")

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

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 View All Leases", use_container_width=True):
            st.switch_page("pages/2_📋_Lease_Review.py")

    with col2:
        if st.button("📤 Upload More", use_container_width=True):
            st.session_state.bulk_upload_results = []
            clear_bulk_queue(st.session_state)
            st.rerun()

    with col3:
        if st.button("🏠 Go to Home", use_container_width=True):
            st.switch_page("Home.py")

elif not uploaded_files:
    st.info("💡 Select multiple PDF files above to get started with bulk upload")

st.markdown("---")
if st.button("← Back to Upload Lease"):
    st.switch_page("pages/1_📤_Upload_Lease.py")
