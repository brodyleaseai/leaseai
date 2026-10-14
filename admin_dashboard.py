"""
Admin Dashboard for LeaseAI
Lease review, approval, and management interface for administrators.
"""
import streamlit as st
from datetime import datetime
from lease_report import generate_lease_abstract_pdf
from email_delivery import trigger_delivery_email
import config


def render_admin_dashboard(supabase, auth):
    """
    Render the admin dashboard interface.
    
    Args:
        supabase: Supabase client instance
        auth: AuthManager instance
    """
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"📊 {config.APP_NAME} Admin Dashboard")
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
            ["Dashboard", "Lease Review", "Critical Dates", "ASC 842 Compliance", "Client Management", "Analytics", "Audit Log"],
            label_visibility="collapsed"
        )
    
    # Route to selected page
    if page == "Dashboard":
        render_dashboard_overview(supabase)
    elif page == "Lease Review":
        render_lease_review_page(supabase)
    elif page == "Critical Dates":
        from critical_dates import render_critical_dates_page
        render_critical_dates_page(supabase)
    elif page == "ASC 842 Compliance":
        from asc842_dashboard import render_asc842_compliance_page
        render_asc842_compliance_page(supabase, auth)
    elif page == "Client Management":
        render_client_management_page(supabase)
    elif page == "Analytics":
        render_analytics_page(supabase)
    elif page == "Audit Log":
        render_audit_log_page(supabase)


def render_lease_review_page(supabase):
    """Render the lease review and approval interface."""
    
    st.header("📋 Lease Review Queue")
    
    # Status filter
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "UPLOADED", "PROCESSING", "REVIEW", "APPROVED", "FLAGGED"]
        )
    
    with col2:
        st.metric("Total Leases", "0")
    
    with col3:
        st.metric("Pending Review", "0")
    
    st.markdown("---")
    
    # Fetch leases
    try:
        query = supabase.table("leases").select("*")
        
        if status_filter != "All":
            query = query.eq("status", status_filter)
        
        response = query.order("uploaded_at", desc=True).execute()
        leases = response.data
        
        if not leases:
            st.info("No leases found matching the filter criteria.")
            return
        
        # Display leases
        for lease in leases:
            render_lease_card(lease, supabase)
            st.markdown("---")
    
    except Exception as e:
        st.error(f"Error loading leases: {str(e)}")


def render_lease_card(lease, supabase):
    """
    Render a single lease card with actions.
    
    Args:
        lease: Lease data dictionary
        supabase: Supabase client instance
    """
    lease_id = lease.get("id")
    
    # Lease header
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.subheader(f"🏢 {lease.get('property_address', 'N/A')}")
        st.caption(f"Tenant: {lease.get('tenant_name', 'N/A')} | ID: #{lease_id}")
    
    with col2:
        status = lease.get("status", "UNKNOWN")
        status_color = {
            "UPLOADED": "🔵",
            "PROCESSING": "🟡",
            "REVIEW": "🟠",
            "APPROVED": "🟢",
            "FLAGGED": "🔴"
        }.get(status, "⚪")
        st.write(f"{status_color} **{status}**")
    
    with col3:
        uploaded_at = lease.get("uploaded_at")
        if uploaded_at:
            st.caption(f"Uploaded: {uploaded_at[:10]}")
    
    # Lease details
    with st.expander("View Details"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Property Address:**")
            st.write(lease.get("property_address", "N/A"))
            
            st.write("**Tenant Name:**")
            st.write(lease.get("tenant_name", "N/A"))
        
        with col2:
            st.write("**Client ID:**")
            st.write(f"#{lease.get('client_id', 'N/A')}")
            
            st.write("**Document URL:**")
            doc_url = lease.get("document_url", "")
            if doc_url:
                st.markdown(f"[View Document]({doc_url})")
            else:
                st.write("N/A")
        
        # Extracted data
        extracted_data = lease.get("extracted_data", {})
        if extracted_data:
            st.write("**Extracted Fields:**")
            st.json(extracted_data)
    
    # Action buttons
    col_status, col_approve, col_flag, col_reset, col_deliver = st.columns(5)
    
    with col_status:
        if st.button("📊 View Abstract", key=f"view_{lease_id}"):
            show_pdf_preview(lease, supabase)
    
    with col_approve:
        if lease.get("status") != "APPROVED":
            if st.button("✅ Approve", key=f"approve_{lease_id}"):
                update_lease_status(lease_id, "APPROVED", supabase)
                
                # Automatically send email notification to client
                with st.spinner("Sending notification email..."):
                    success, message = trigger_delivery_email(lease_id, supabase)
                    if success:
                        st.success(f"✅ Lease approved and email sent!")
                    else:
                        st.warning(f"✅ Lease approved, but email failed: {message}")
                st.rerun()
    
    with col_flag:
        if lease.get("status") != "FLAGGED":
            if st.button("🚩 Flag", key=f"flag_{lease_id}"):
                update_lease_status(lease_id, "FLAGGED", supabase)
                st.warning("Lease flagged for review!")
                st.rerun()
    
    with col_reset:
        if st.button("🔄 Reset", key=f"reset_{lease_id}"):
            update_lease_status(lease_id, "REVIEW", supabase)
            st.info("Status reset to REVIEW")
            st.rerun()
    
    with col_deliver:
        if lease.get("status") == "APPROVED":
            if st.button("📧 Resend Email", key=f"deliver_{lease_id}"):
                with st.spinner("Resending email..."):
                    success, message = trigger_delivery_email(lease_id, supabase)
                    if success:
                        st.success(message)
                    else:
                        st.error(f"❌ Email delivery failed: {message}")


def show_pdf_preview(lease, supabase):
    """Generate and display PDF preview."""
    try:
        with st.spinner("Generating PDF..."):
            pdf_bytes = generate_lease_abstract_pdf(
                lease,
                lease.get("extracted_data", {})
            )
            
            st.download_button(
                label="📥 Download Abstract PDF",
                data=pdf_bytes,
                file_name=f"LeaseAbstract_{lease.get('id')}_{lease.get('property_address', 'lease').replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
            
            st.success("PDF generated successfully!")
    
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")


def update_lease_status(lease_id: int, new_status: str, supabase):
    """Update lease status in database."""
    try:
        supabase.table("leases").update({"status": new_status}).eq("id", lease_id).execute()
    except Exception as e:
        st.error(f"Error updating status: {str(e)}")


def render_client_management_page(supabase):
    """Render client management interface."""
    st.header("👥 Client Management")
    
    try:
        response = supabase.table("clients").select("*").execute()
        clients = response.data
        
        if not clients:
            st.info("No clients found.")
            return
        
        # Display clients in a table
        st.dataframe(
            clients,
            column_config={
                "id": "ID",
                "company_name": "Company",
                "email": "Email",
                "contact_name": "Contact",
                "phone": "Phone",
                "created_at": "Created"
            },
            use_container_width=True
        )
    
    except Exception as e:
        st.error(f"Error loading clients: {str(e)}")


def render_analytics_page(supabase):
    """Render analytics and reporting interface."""
    st.header("📈 Analytics & Reporting")
    
    try:
        # Fetch lease statistics
        all_leases = supabase.table("leases").select("*").execute()
        leases = all_leases.data
        
        # Calculate metrics
        total_leases = len(leases)
        
        status_counts = {}
        for lease in leases:
            status = lease.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Leases", total_leases)
        
        with col2:
            st.metric("Approved", status_counts.get("APPROVED", 0))
        
        with col3:
            st.metric("In Review", status_counts.get("REVIEW", 0))
        
        with col4:
            st.metric("Flagged", status_counts.get("FLAGGED", 0))
        
        st.markdown("---")
        
        # Status breakdown
        st.subheader("Status Breakdown")
        st.json(status_counts)
    
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")


def render_dashboard_overview(supabase):
    """Render the main dashboard overview page."""
    st.header("📊 Dashboard Overview")
    
    try:
        # Fetch all data
        leases_response = supabase.table("leases").select("*").execute()
        leases = leases_response.data if leases_response.data else []
        
        clients_response = supabase.table("clients").select("*").execute()
        clients = clients_response.data if clients_response.data else []
        
        # Calculate key metrics
        total_leases = len(leases)
        approved_leases = sum(1 for l in leases if l.get("status") == "APPROVED")
        review_pending = sum(1 for l in leases if l.get("status") in ["REVIEW", "PROCESSING"])
        flagged_leases = sum(1 for l in leases if l.get("status") == "FLAGGED")
        total_clients = len(clients)
        
        # Display key metrics
        st.subheader("Key Metrics")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Leases", total_leases)
        with col2:
            st.metric("Approved", approved_leases, delta=f"{(approved_leases/total_leases*100):.0f}%" if total_leases > 0 else "0%")
        with col3:
            st.metric("Pending Review", review_pending, delta=f"-{review_pending}" if review_pending > 0 else None, delta_color="inverse")
        with col4:
            st.metric("Flagged", flagged_leases, delta=f"-{flagged_leases}" if flagged_leases > 0 else None, delta_color="inverse")
        with col5:
            st.metric("Active Clients", total_clients)
        
        st.markdown("---")
        
        # Recent activity
        st.subheader("📋 Recent Leases")
        
        if leases:
            # Sort by created_at
            recent_leases = sorted(leases, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
            
            for lease in recent_leases:
                with st.expander(f"#{lease.get('id')} - {lease.get('property_address', 'N/A')} - {lease.get('status', 'UNKNOWN')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Property:** {lease.get('property_address', 'N/A')}")
                        st.markdown(f"**Tenant:** {lease.get('tenant_name', 'N/A')}")
                        st.markdown(f"**Status:** {lease.get('status', 'UNKNOWN')}")
                    with col2:
                        st.markdown(f"**Uploaded:** {lease.get('created_at', 'N/A')[:10]}")
                        st.markdown(f"**Pages:** {lease.get('page_count', 'N/A')}")
                        st.markdown(f"**Client ID:** {lease.get('client_id', 'N/A')}")
        else:
            st.info("No leases uploaded yet.")
        
        st.markdown("---")
        
        # Critical dates summary
        st.subheader("📅 Upcoming Critical Dates")
        
        try:
            from critical_dates import CriticalDatesManager
            from datetime import datetime, timedelta
            
            dates_manager = CriticalDatesManager(supabase)
            upcoming = dates_manager.get_upcoming_dates(days_ahead=30)
            
            if upcoming:
                col1, col2, col3 = st.columns(3)
                
                today = datetime.now().date()
                critical = sum(1 for d in upcoming if (datetime.strptime(d["date_value"], "%Y-%m-%d").date() - today).days < 14)
                high = sum(1 for d in upcoming if 14 <= (datetime.strptime(d["date_value"], "%Y-%m-%d").date() - today).days < 30)
                
                with col1:
                    st.metric("Next 30 Days", len(upcoming))
                with col2:
                    st.metric("Critical (< 14d)", critical, delta=f"-{critical}" if critical > 0 else None, delta_color="inverse")
                with col3:
                    st.metric("High (< 30d)", high)
                
                st.info(f"📌 View all critical dates in the **Critical Dates** page")
            else:
                st.success("✅ No critical dates in the next 30 days")
        except Exception as e:
            st.warning(f"Unable to load critical dates: {str(e)}")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")


def render_audit_log_page(supabase):
    """Render the audit log page."""
    st.header("📜 Audit Log")
    
    st.info("""
    **Audit Log Feature**
    
    Track all administrative actions and system events:
    - Lease approvals and status changes
    - Client account modifications
    - Critical date updates
    - Email notifications sent
    - User login/logout events
    - Configuration changes
    
    This feature will log and display all system activities for compliance and troubleshooting.
    """)
    
    st.markdown("---")
    
    st.subheader("Coming Soon")
    
    st.markdown("""
    The audit log feature is under development and will include:
    
    - **Full Activity Timeline**: Complete history of all admin actions
    - **User Attribution**: Track which admin performed each action
    - **Filtering & Search**: Find specific events quickly
    - **Export Capabilities**: Download audit logs for compliance
    - **Real-time Monitoring**: Live feed of system events
    - **Retention Policies**: Configurable log retention periods
    
    In the meantime, check application logs for detailed system activity.
    """)
