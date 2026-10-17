"""
LeaseAI - Upload Lease
Upload and process new lease documents with OCR support
"""

import streamlit as st
import tempfile
import os
from datetime import datetime
from supabase import create_client
import config

# Initialize Supabase
sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

# Page config
st.set_page_config(
    page_title="Upload Lease | LeaseAI",
    page_icon="📤",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .upload-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .upload-card {
        background: #1a1f2e;
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 3rem;
        text-align: center;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="upload-header">
    <h1>📤 Upload New Lease</h1>
    <p>Upload a lease PDF for AI-powered extraction of 84+ fields</p>
    <p style="font-size: 0.9rem; opacity: 0.9;">Supports both digital and scanned PDFs with OCR fallback</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state for successful uploads
if "last_processed_lease" not in st.session_state:
    st.session_state.last_processed_lease = None

# Upload form
with st.form("upload_lease_form"):
    st.markdown("### 📄 Lease Document")
    
    uploaded_file = st.file_uploader(
        "Upload Lease PDF",
        type=['pdf'],
        help="Upload the base lease document (PDF format)"
    )
    
    st.markdown("### 📝 Basic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        property_address = st.text_input(
            "Property Address",
            placeholder="123 Main St, Vancouver, BC",
            help="Property civic address"
        )
        
        tenant_name = st.text_input(
            "Tenant Name",
            placeholder="Acme Corp",
            help="Tenant legal or trade name"
        )
    
    with col2:
        # Get clients for dropdown
        try:
            clients_response = sb.table("clients").select("id, name").execute()
            clients = clients_response.data or []
            
            if clients:
                client_options = {client['name']: client['id'] for client in clients}
                selected_client = st.selectbox(
                    "Client",
                    options=list(client_options.keys()),
                    help="Select the client who owns this lease"
                )
                client_id = client_options[selected_client]
            else:
                st.warning("No clients found. Please create a client first.")
                client_id = None
        except Exception as e:
            st.error(f"Error loading clients: {e}")
            client_id = None
    
    # Submit button
    submitted = st.form_submit_button("🚀 Process Lease", type="primary", use_container_width=True)

# Process form submission (OUTSIDE the form)
if submitted:
    if not uploaded_file:
        st.error("Please upload a PDF file")
    elif not property_address:
        st.error("Please enter property address")
    elif not tenant_name:
        st.error("Please enter tenant name")
    elif not client_id:
        st.error("Please select a client")
    else:
        with st.spinner("Processing lease with OCR and AI extraction... This may take 30-60 seconds..."):
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Process lease
                from extraction_pipeline import LeaseExtractionPipeline
                
                pipeline = LeaseExtractionPipeline()
                lease_id, extracted_fields = pipeline.process_lease(
                    pdf_path=tmp_path,
                    client_id=client_id,
                    supabase_client=sb,
                    property_address=property_address,
                    tenant_name=tenant_name,
                    filename=uploaded_file.name
                )
                
                # Store in session state for display after form
                st.session_state.last_processed_lease = {
                    "lease_id": lease_id,
                    "extracted_fields": extracted_fields
                }
                
                st.success(f"✅ Lease processed successfully!")
                st.success(f"Lease ID: {lease_id}")
                
            except Exception as e:
                st.error(f"❌ Error processing lease: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
            
            finally:
                # Clean up temp file
                os.unlink(tmp_path)

# Display results if available (OUTSIDE the form)
if st.session_state.last_processed_lease:
    lease_data = st.session_state.last_processed_lease
    extracted_fields = lease_data["extracted_fields"]
    
    st.markdown("---")
    st.markdown("### 📊 Extraction Summary")
    
    high_conf = sum(1 for f in extracted_fields.values() 
                       if isinstance(f, dict) and f.get('confidence') == 'HIGH')
    medium_conf = sum(1 for f in extracted_fields.values() 
                     if isinstance(f, dict) and f.get('confidence') == 'MEDIUM')
    low_conf = sum(1 for f in extracted_fields.values() 
                  if isinstance(f, dict) and f.get('confidence') == 'LOW')
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Fields", len(extracted_fields))
    col2.metric("High Confidence", high_conf)
    col3.metric("Medium Confidence", medium_conf)
    col4.metric("Low Confidence", low_conf)
    
    st.info("💡 Go to **Lease Review** to review and approve the extracted fields!")
    
    if st.button("📋 Review This Lease", type="primary"):
        # Store the lease ID so the review page can auto-select it
        st.session_state["review_lease_id"] = lease_data["lease_id"]
        st.session_state["review_page"] = "🔍 Review a Lease"  # Go directly to review page with buttons
        st.switch_page("pages/2_📋_Lease_Review.py")

st.markdown("---")

# Help section
with st.expander("ℹ️ Help & Information"):
    st.markdown("""
    ### How it works:
    
    1. **Upload PDF**: Upload your lease document (digital or scanned)
    2. **OCR Processing**: Automatic text extraction with OCR fallback for scanned docs
    3. **AI Extraction**: GPT-4 extracts 84+ comprehensive lease fields
    4. **Review**: Review and approve extracted fields before finalizing
    
    ### Supported formats:
    - ✅ Digital PDFs with embedded text
    - ✅ Scanned PDFs (uses AWS Textract or Tesseract OCR)
    - ✅ Multi-page documents
    - ✅ Files up to 50MB
    
    ### Extraction includes:
    - Party information (7 fields)
    - Property details (7 fields)  
    - Lease terms (6 fields)
    - Rent & escalations (12 fields)
    - Operating expenses (4 fields)
    - Renewal options (8 fields)
    - Legal clauses (11 fields)
    - And 29 more comprehensive fields!
    
    ### Processing time:
    - Digital PDFs: 15-30 seconds
    - Scanned PDFs: 30-60 seconds
    """)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 1rem;">
    <p style="font-size: 0.85rem;">Powered by GPT-4o • AWS Textract • Tesseract OCR</p>
</div>
""", unsafe_allow_html=True)
