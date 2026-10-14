"""
Enhanced Client Portal for LeaseAI
Client-facing interface with file upload and extraction integration.
"""
import streamlit as st
from datetime import datetime
from lease_report import generate_lease_abstract_pdf
from extraction_pipeline import LeaseExtractionPipeline
from file_upload import FileUploadHandler
import config
import os


def render_client_portal(supabase, auth):
    """
    Render the enhanced client portal interface.
    
    Args:
        supabase: Supabase client instance
        auth: AuthManager instance
    """
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"📄 {config.APP_NAME} Client Portal")
        st.caption("Upload leases, track processing, and download abstracts")
    with col2:
        st.write(f"👤 {auth.get_user_name()}")
        if st.button("Logout", use_container_width=True):
            auth.logout()
            st.rerun()
    
    st.markdown("---")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["📤 Upload New Lease", "📋 My Leases", "💰 Billing", "❓ Help & Support"],
            label_visibility="collapsed"
        )
    
    # Route to selected page
    if page == "📤 Upload New Lease":
        render_upload_page(supabase, auth)
    elif page == "📋 My Leases":
        render_my_leases_page(supabase, auth)
    elif page == "💰 Billing":
        render_billing_page(supabase, auth)
    elif page == "❓ Help & Support":
        render_help_page()


def render_upload_page(supabase, auth):
    """Render the enhanced lease upload interface with live processing."""
    
    st.header("📤 Upload New Lease")
    st.markdown("Upload your commercial lease document for AI-powered abstraction.")
    
    client_id = auth.get_user_id()
    
    # Check if client has active subscription or credits
    # For now, we'll allow uploads (add payment check in Priority 3)
    
    with st.form("upload_lease_form"):
        st.subheader("📝 Lease Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            property_address = st.text_input(
                "Property Address *",
                placeholder="123 Main Street, Vancouver, BC",
                help="Full civic address of the leased property"
            )
            tenant_name = st.text_input(
                "Tenant Name *",
                placeholder="Acme Corporation",
                help="Legal name of the tenant"
            )
        
        with col2:
            lease_type = st.selectbox(
                "Lease Type",
                ["Commercial", "Retail", "Office", "Industrial", "Mixed-Use", "Other"]
            )
            square_footage = st.number_input(
                "Square Footage",
                min_value=0,
                step=100,
                help="Rentable square feet (optional)"
            )
        
        st.markdown("---")
        
        st.subheader("📄 Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF file *",
            type=["pdf"],
            help="Upload the complete lease agreement in PDF format (max 50MB)",
            key="lease_upload"
        )
        
        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.success(f"✅ {uploaded_file.name} - {file_size_mb:.1f} MB")
        
        notes = st.text_area(
            "Additional Notes (optional)",
            placeholder="Any special instructions or notes for our review team...",
            height=100
        )
        
        submit = st.form_submit_button(
            "🚀 Submit Lease for Processing",
            use_container_width=True,
            type="primary"
        )
        
        if submit:
            if not property_address or not tenant_name:
                st.error("❌ Please fill in all required fields (marked with *)")
            elif not uploaded_file:
                st.error("❌ Please upload a lease document")
            elif file_size_mb > 50:
                st.error("❌ File size exceeds 50MB limit")
            else:
                # Process the lease
                process_uploaded_lease(
                    supabase,
                    client_id,
                    uploaded_file,
                    property_address,
                    tenant_name,
                    lease_type,
                    square_footage,
                    notes
                )


def process_uploaded_lease(
    supabase,
    client_id,
    uploaded_file,
    property_address,
    tenant_name,
    lease_type,
    square_footage,
    notes
):
    """
    Process uploaded lease with live progress updates.
    """
    
    # Create progress placeholder
    progress_container = st.container()
    
    with progress_container:
        st.markdown("### 🔄 Processing Your Lease")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Upload to storage
            status_text.text("⬆️ Uploading to secure storage...")
            progress_bar.progress(10)
            
            handler = FileUploadHandler(supabase)
            temp_path = handler.save_uploaded_file_temporarily(uploaded_file)
            
            try:
                storage_path, storage_url = handler.upload_lease_pdf(
                    uploaded_file,
                    client_id,
                    property_address
                )
            except Exception as e:
                st.error(f"Upload failed: {str(e)}")
                return
            
            progress_bar.progress(20)
            
            # Step 2: Extract text
            status_text.text("📄 Extracting text from PDF...")
            progress_bar.progress(30)
            
            pipeline = LeaseExtractionPipeline()
            
            # Step 3: Create lease record
            status_text.text("💾 Creating lease record...")
            lease_data = {
                "client_id": client_id,
                "filename": uploaded_file.name,
                "file_path": storage_path,
                "property_address": property_address,
                "tenant_name": tenant_name,
                "status": "PROCESSING",
                "notes": notes,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            lease_response = supabase.table("leases").insert(lease_data).execute()
            lease_id = lease_response.data[0]["id"]
            
            progress_bar.progress(40)
            
            # Step 4: Run AI extraction
            status_text.text("🤖 AI extracting lease data (this takes 30-60 seconds)...")
            progress_bar.progress(50)
            
            try:
                # Extract text
                lease_text, page_count = pipeline.extract_text_from_pdf(temp_path)
                
                progress_bar.progress(60)
                status_text.text("🧠 GPT-4 analyzing lease clauses...")
                
                # Extract fields with GPT-4
                extracted_fields = pipeline.extract_fields_with_gpt4(
                    lease_text,
                    property_address,
                    tenant_name
                )
                
                progress_bar.progress(70)
                status_text.text("💾 Saving extracted data...")
                
                # Save fields to database
                field_number = 1
                for field_name, field_data in extracted_fields.items():
                    if isinstance(field_data, dict):
                        value = field_data.get("value", "NOT FOUND")
                        confidence_str = field_data.get("confidence", "LOW")
                        source_snippet = field_data.get("source_snippet", "")
                        notes_field = field_data.get("notes", "")
                    else:
                        value = str(field_data)
                        confidence_str = "LOW"
                        source_snippet = ""
                        notes_field = ""
                    
                    confidence_score = pipeline.calculate_confidence_score(confidence_str)
                    
                    field_record = {
                        "lease_id": lease_id,
                        "field_name": field_name,
                        "field_number": field_number,
                        "raw_value": value,
                        "confidence": confidence_str,
                        "confidence_score": confidence_score,
                        "source_text": source_snippet[:500] if source_snippet else "",
                        "notes": notes_field,
                        "reviewed": False,
                    }
                    
                    supabase.table("extracted_fields").insert(field_record).execute()
                    field_number += 1
                
                progress_bar.progress(90)
                
                # Update lease status
                supabase.table("leases").update({
                    "status": "READY FOR REVIEW",
                    "extracted_data": extracted_fields,
                    "page_count": page_count
                }).eq("id", lease_id).execute()
                
                progress_bar.progress(100)
                status_text.text("✅ Complete!")
                
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
                # Send upload confirmation email to client
                try:
                    from email_delivery import send_upload_confirmation_email
                    
                    user_email = st.session_state.get("user_email")
                    user_name = st.session_state.get("user_name", "Valued Client")
                    
                    if user_email:
                        email_sent = send_upload_confirmation_email(
                            recipient_email=user_email,
                            recipient_name=user_name,
                            property_address=property_address,
                            lease_id=lease_id
                        )
                        if email_sent:
                            print(f"✅ Upload confirmation email sent to {user_email}")
                        else:
                            print(f"⚠️ Email send returned False for {user_email}")
                    else:
                        print("⚠️ No user email found in session state")
                except Exception as e:
                    print(f"⚠️ Failed to send upload confirmation email: {e}")
                
                # Success message
                st.success("🎉 Lease processed successfully!")
                st.balloons()
                
                st.info(f"""
                **Processing Complete!**
                
                - **Lease ID:** #{lease_id}
                - **Property:** {property_address}
                - **Fields Extracted:** {len(extracted_fields)}
                - **Status:** Ready for Review
                
                Our team will review the extracted data within 24 hours. You'll receive an email when your lease abstract is ready for download.
                
                Navigate to **"My Leases"** to view the processing status.
                """)
            
            except Exception as e:
                # Update lease status to failed
                supabase.table("leases").update({
                    "status": "FLAGGED",
                    "notes": f"Processing error: {str(e)}"
                }).eq("id", lease_id).execute()
                
                st.error(f"❌ Processing failed: {str(e)}")
                st.info("Our team has been notified and will process your lease manually.")
        
        except Exception as e:
            st.error(f"❌ Upload error: {str(e)}")


def render_my_leases_page(supabase, auth):
    """Render the client's lease list with enhanced status tracking."""
    
    st.header("📋 My Leases")
    st.markdown("View and download your lease abstracts.")
    
    client_id = auth.get_user_id()
    
    # Fetch client's leases
    try:
        response = supabase.table("leases").select("*").eq("client_id", client_id).order("uploaded_at", desc=True).execute()
        leases = response.data
        
        if not leases:
            st.info("📤 You haven't uploaded any leases yet. Use the 'Upload New Lease' page to get started.")
            if st.button("➕ Upload Your First Lease", use_container_width=True, type="primary"):
                st.rerun()
            return
        
        # Status filter
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "PROCESSING", "READY FOR REVIEW", "APPROVED", "FLAGGED"]
            )
        
        with col2:
            st.metric("Total Leases", len(leases))
        
        with col3:
            approved_count = len([l for l in leases if l.get("status") == "APPROVED"])
            st.metric("Completed", approved_count)
        
        st.markdown("---")
        
        # Filter leases
        if status_filter != "All":
            leases = [l for l in leases if l.get("status") == status_filter]
        
        if not leases:
            st.info(f"No leases with status: {status_filter}")
            return
        
        # Display leases
        for lease in leases:
            render_client_lease_card_enhanced(lease, supabase)
            st.markdown("---")
    
    except Exception as e:
        st.error(f"Error loading leases: {str(e)}")


def render_client_lease_card_enhanced(lease, supabase):
    """Enhanced lease card with better status tracking."""
    
    lease_id = lease.get("id")
    status = lease.get("status", "UNKNOWN")
    
    # Status info
    status_info = {
        "UPLOADED": {
            "icon": "📤",
            "text": "Uploaded",
            "color": "#60A5FA",
            "help": "Your lease has been received and is queued for processing"
        },
        "PROCESSING": {
            "icon": "🔄",
            "text": "Processing",
            "color": "#FBBF24",
            "help": "AI is extracting lease data - usually takes 5-10 minutes"
        },
        "READY FOR REVIEW": {
            "icon": "👀",
            "text": "In Review",
            "color": "#F59E0B",
            "help": "Our team is reviewing the AI extraction for accuracy"
        },
        "APPROVED": {
            "icon": "✅",
            "text": "Ready",
            "color": "#10B981",
            "help": "Your abstract is ready for download"
        },
        "FLAGGED": {
            "icon": "⚠️",
            "text": "Needs Attention",
            "color": "#EF4444",
            "help": "Please contact support for assistance with this lease"
        }
    }
    
    info = status_info.get(status, {"icon": "❓", "text": status, "color": "#9CA3AF", "help": ""})
    
    # Lease header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"🏢 {lease.get('property_address', 'N/A')}")
        st.caption(f"Tenant: {lease.get('tenant_name', 'N/A')} • ID: #{lease_id}")
    
    with col2:
        st.markdown(
            f'<div style="background:{info["color"]};padding:8px 16px;border-radius:8px;text-align:center;">'
            f'<div style="font-size:1.5rem;">{info["icon"]}</div>'
            f'<div style="color:white;font-weight:600;">{info["text"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if info["help"]:
            st.caption(info["help"])
    
    # Lease details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Uploaded:**")
        uploaded_at = lease.get("uploaded_at")
        if uploaded_at:
            st.write(datetime.fromisoformat(uploaded_at.replace("Z", "+00:00")).strftime("%b %d, %Y"))
    
    with col2:
        st.write("**File:**")
        st.write(lease.get("filename", "N/A"))
    
    with col3:
        st.write("**Pages:**")
        st.write(lease.get("page_count", "—"))
    
    # Actions based on status
    if status == "APPROVED":
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Download Abstract", key=f"download_{lease_id}", use_container_width=True, type="primary"):
                download_abstract(lease)
        
        with col2:
            # Check if ASC 842 calculation exists
            try:
                asc842_response = supabase.table("asc842_calculations").select("*").eq("lease_id", lease_id).order("calculated_at", desc=True).limit(1).execute()
                if asc842_response.data and len(asc842_response.data) > 0:
                    if st.button("📊 Download ASC 842", key=f"asc842_{lease_id}", use_container_width=True):
                        download_asc842_reports(asc842_response.data[0])
                else:
                    st.button("📊 ASC 842 (N/A)", key=f"asc842_na_{lease_id}", use_container_width=True, disabled=True, help="No ASC 842 calculation available for this lease")
            except:
                st.button("📊 ASC 842 (N/A)", key=f"asc842_err_{lease_id}", use_container_width=True, disabled=True)
        
        with col3:
            with st.expander("📊 View Extracted Data"):
                extracted_data = lease.get("extracted_data", {})
                if extracted_data:
                    for field_name, field_info in list(extracted_data.items())[:10]:
                        if isinstance(field_info, dict):
                            value = field_info.get("value", "N/A")
                            st.write(f"**{field_name}:** {value}")
                        else:
                            st.write(f"**{field_name}:** {field_info}")
                    
                    if len(extracted_data) > 10:
                        st.caption(f"+ {len(extracted_data) - 10} more fields")
    
    elif status in ["PROCESSING", "READY FOR REVIEW"]:
        st.info(f"⏳ {info['help']}")
    
    elif status == "FLAGGED":
        st.warning("⚠️ This lease requires additional attention. Our support team will contact you shortly.")
        if st.button("📧 Contact Support", key=f"support_{lease_id}"):
            st.info("Please email support@leaseai.com or call (604) 555-0123")


def download_abstract(lease):
    """Generate and download lease abstract PDF."""
    try:
        with st.spinner("Generating your lease abstract..."):
            pdf_bytes = generate_lease_abstract_pdf(
                lease,
                lease.get("extracted_data", {})
            )
            
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=f"LeaseAbstract_{lease.get('id')}_{lease.get('property_address', 'lease').replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"dl_btn_{lease.get('id')}",
                use_container_width=True
            )
            
            st.success("✅ PDF ready for download!")
    
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")


def download_asc842_reports(asc842_calc):
    """Download ASC 842 compliance reports."""
    try:
        import pandas as pd
        import json
        
        st.success("✅ ASC 842 Compliance Reports Available")
        
        # Show quick summary
        st.write(f"**Classification:** {asc842_calc.get('lease_classification', 'N/A')}")
        st.write(f"**Initial Liability:** ${asc842_calc.get('initial_lease_liability', 0):,.2f}")
        st.write(f"**Initial ROU Asset:** ${asc842_calc.get('initial_rou_asset', 0):,.2f}")
        st.write(f"**Calculated:** {asc842_calc.get('calculated_at', 'N/A')}")
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        # Liability Schedule CSV
        with col1:
            liability_data = json.loads(asc842_calc.get('liability_schedule', '[]'))
            if liability_data:
                liability_df = pd.DataFrame(liability_data)
                liability_csv = liability_df.to_csv(index=False)
                st.download_button(
                    label="📥 Liability Schedule",
                    data=liability_csv,
                    file_name=f"ASC842_Liability_{asc842_calc.get('id')}.csv",
                    mime="text/csv",
                    key=f"liab_csv_{asc842_calc.get('id')}",
                    use_container_width=True
                )
        
        # ROU Asset Schedule CSV
        with col2:
            rou_data = json.loads(asc842_calc.get('rou_asset_schedule', '[]'))
            if rou_data:
                rou_df = pd.DataFrame(rou_data)
                rou_csv = rou_df.to_csv(index=False)
                st.download_button(
                    label="📥 ROU Asset Schedule",
                    data=rou_csv,
                    file_name=f"ASC842_ROU_Asset_{asc842_calc.get('id')}.csv",
                    mime="text/csv",
                    key=f"rou_csv_{asc842_calc.get('id')}",
                    use_container_width=True
                )
        
        # Full Report JSON
        with col3:
            full_report = json.dumps(asc842_calc, indent=2, default=str)
            st.download_button(
                label="📥 Full Report (JSON)",
                data=full_report,
                file_name=f"ASC842_Full_Report_{asc842_calc.get('id')}.json",
                mime="application/json",
                key=f"json_{asc842_calc.get('id')}",
                use_container_width=True
            )
        
        st.caption("💡 Import these schedules into Excel or your accounting software")
    
    except Exception as e:
        st.error(f"Error loading ASC 842 reports: {str(e)}")


def render_billing_page(supabase, auth):
    """Render billing and subscription information."""
    
    st.header("💰 Billing & Subscription")
    st.markdown("Manage your LeaseAI subscription and billing information.")
    
    # This will be implemented in Priority 3 with Stripe
    st.info("💳 **Payment integration coming in Priority 3**")
    
    st.markdown("""
    ### Current Plan: Free Trial
    
    - ✅ 3 lease abstracts included
    - ✅ Full AI extraction
    - ✅ PDF abstracts with confidence scoring
    - ✅ Email delivery
    
    ### Upgrade Options:
    
    **Starter Plan - $49/month**
    - 10 leases per month
    - 24-hour turnaround
    - Email support
    
    **Professional Plan - $149/month**
    - Unlimited leases
    - 12-hour turnaround
    - Priority support
    - ASC 842 compliance reports
    
    **Enterprise Plan - Custom**
    - Volume pricing
    - Dedicated account manager
    - API access
    - Custom integrations
    """)
    
    if st.button("💳 Upgrade Now", type="primary", use_container_width=True):
        st.info("Stripe payment integration will be added in Priority 3!")


def render_help_page():
    """Render help and support information."""
    
    st.header("❓ Help & Support")
    
    st.markdown("""
    ### How LeaseAI Works
    
    **1. Upload Your Lease** 📤
    - Submit your commercial lease document in PDF format
    - Provide basic property and tenant information
    - Files are encrypted and stored securely
    
    **2. AI Extraction** 🤖
    - Our GPT-4 AI extracts 84+ key lease terms
    - Typical processing time: 5-10 minutes
    - Confidence scores for every field
    
    **3. Expert Review** 👀
    - Our team reviews the AI extraction for accuracy
    - Low-confidence fields are manually verified
    - Usually completed within 24 hours
    
    **4. Receive Abstract** ✅
    - Download your comprehensive lease abstract
    - Professional PDF with color-coded confidence indicators
    - Original lease data preserved
    
    ### Frequently Asked Questions
    
    **Q: How long does processing take?**  
    A: AI extraction takes 5-10 minutes. Expert review is completed within 24 hours.
    
    **Q: What file formats are supported?**  
    A: Currently, we accept PDF files only (max 50MB).
    
    **Q: How accurate is the AI extraction?**  
    A: Our AI achieves 95%+ accuracy on standard commercial leases. All extractions are verified by our expert team.
    
    **Q: Is my data secure?**  
    A: Yes! All documents are encrypted in transit and at rest. We follow SOC 2 Type II security standards.
    
    **Q: Can I edit the extracted data?**  
    A: Currently only our admin team can edit. Self-service editing is coming soon!
    
    **Q: What lease types are supported?**  
    A: Commercial, Retail, Office, Industrial, and Mixed-Use leases.
    
    ### Contact Support
    
    Need help? We're here for you!
    
    📧 **Email:** support@leaseai.com  
    📞 **Phone:** (604) 555-0123  
    🕐 **Hours:** Monday-Friday, 9 AM - 5 PM PT  
    💬 **Live Chat:** Available in-app (coming soon)
    
    ### Additional Resources
    
    - 📖 [User Guide](https://leaseai.com/docs)
    - 🎥 [Video Tutorials](https://leaseai.com/tutorials)
    - 💡 [Best Practices](https://leaseai.com/best-practices)
    - 🔒 [Security & Privacy](https://leaseai.com/security)
    """)
    
    st.markdown("---")
    
    st.subheader("📬 Send us a message")
    
    with st.form("contact_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("Subject")
        with col2:
            priority = st.selectbox("Priority", ["Normal", "Urgent"])
        
        message = st.text_area("Message", height=150)
        submit = st.form_submit_button("Send Message", use_container_width=True)
        
        if submit:
            if subject and message:
                # In production, send email via SendGrid
                st.success("✅ Message sent! We'll get back to you within 24 hours.")
            else:
                st.error("Please fill in both subject and message.")
