"""
Critical Dates Management System for LeaseAI
Tracks and sends notifications for important lease dates.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import config


class CriticalDatesManager:
    """Manages critical dates and notifications for leases."""
    
    # Standard notification intervals (days before the date)
    DEFAULT_NOTIFICATION_INTERVALS = [90, 60, 30, 14, 7, 1]
    
    # Critical date types
    DATE_TYPES = [
        "Lease Expiration",
        "Renewal Option Deadline",
        "Renewal Notice Deadline",
        "Option Exercise Deadline",
        "Termination Notice Deadline",
        "Rent Escalation Date",
        "CAM Reconciliation Due",
        "Insurance Renewal",
        "Property Tax Due",
        "Security Deposit Review",
        "Right of First Refusal Deadline",
        "Expansion Option Deadline",
        "Other"
    ]
    
    def __init__(self, supabase_client):
        """Initialize the critical dates manager."""
        self.supabase = supabase_client
    
    def add_critical_date(
        self,
        lease_id: str,  # UUID as string
        date_type: str,
        date_value: str,
        description: str = None,
        notification_intervals: List[int] = None
    ) -> bool:
        """
        Add a critical date for a lease.
        
        Args:
            lease_id: Lease ID
            date_type: Type of date (from DATE_TYPES)
            date_value: Date in YYYY-MM-DD format
            description: Optional description
            notification_intervals: List of days before to send notifications
            
        Returns:
            True if successful
        """
        try:
            if notification_intervals is None:
                notification_intervals = self.DEFAULT_NOTIFICATION_INTERVALS
            
            date_record = {
                "lease_id": lease_id,
                "date_type": date_type,
                "date_value": date_value,
                "description": description or f"{date_type} for lease #{lease_id}",
                "notification_intervals": notification_intervals,
                "notifications_sent": [],
                "is_active": True
            }
            
            self.supabase.table("critical_dates").insert(date_record).execute()
            return True
            
        except Exception as e:
            print(f"Error adding critical date: {e}")
            return False
    
    def get_upcoming_dates(self, days_ahead: int = 90) -> List[Dict]:
        """
        Get all critical dates within the next N days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of critical dates with lease info
        """
        try:
            today = datetime.now().date()
            cutoff_date = today + timedelta(days=days_ahead)
            
            # Fetch critical dates
            response = self.supabase.table("critical_dates").select(
                "*, leases(id, property_address, tenant_name, client_id)"
            ).eq("is_active", True).lte("date_value", cutoff_date.isoformat()).gte(
                "date_value", today.isoformat()
            ).order("date_value").execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            print(f"Error fetching upcoming dates: {e}")
            return []
    
    def get_dates_by_lease(self, lease_id: str) -> List[Dict]:
        """Get all critical dates for a specific lease."""
        try:
            response = self.supabase.table("critical_dates").select(
                "*"
            ).eq("lease_id", lease_id).eq("is_active", True).order("date_value").execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            print(f"Error fetching dates for lease: {e}")
            return []
    
    def check_and_send_notifications(self) -> Dict:
        """
        Check all critical dates and send notifications if needed.
        This should be run daily via a scheduled job.
        
        Returns:
            Dictionary with notification results
        """
        from email_delivery import send_critical_date_reminder
        
        today = datetime.now().date()
        notifications_sent = 0
        errors = 0
        
        try:
            # Get all active critical dates
            response = self.supabase.table("critical_dates").select(
                "*, leases(id, property_address, tenant_name, client_id, clients(email, company_name))"
            ).eq("is_active", True).execute()
            
            dates = response.data if response.data else []
            
            for date_record in dates:
                date_value = datetime.strptime(date_record["date_value"], "%Y-%m-%d").date()
                days_until = (date_value - today).days
                
                # Check if we should send a notification
                notification_intervals = date_record.get("notification_intervals", self.DEFAULT_NOTIFICATION_INTERVALS)
                notifications_sent_list = date_record.get("notifications_sent", [])
                
                for interval in notification_intervals:
                    if days_until == interval and interval not in notifications_sent_list:
                        # Send notification
                        lease = date_record.get("leases", {})
                        client = lease.get("clients", {})
                        
                        if client and client.get("email"):
                            success = send_critical_date_reminder(
                                client_email=client["email"],
                                client_name=client.get("company_name", "Valued Client"),
                                date_type=date_record["date_type"],
                                date_value=date_record["date_value"],
                                days_until=days_until,
                                property_address=lease.get("property_address"),
                                lease_id=lease.get("id"),
                                description=date_record.get("description")
                            )
                            
                            if success:
                                # Update notifications_sent list
                                notifications_sent_list.append(interval)
                                self.supabase.table("critical_dates").update({
                                    "notifications_sent": notifications_sent_list
                                }).eq("id", date_record["id"]).execute()
                                
                                notifications_sent += 1
                            else:
                                errors += 1
            
            return {
                "success": True,
                "notifications_sent": notifications_sent,
                "errors": errors,
                "checked_dates": len(dates)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def mark_date_inactive(self, date_id: int) -> bool:
        """Mark a critical date as inactive (no longer send notifications)."""
        try:
            self.supabase.table("critical_dates").update({
                "is_active": False
            }).eq("id", date_id).execute()
            return True
        except Exception as e:
            print(f"Error marking date inactive: {e}")
            return False


def render_critical_dates_page(supabase):
    """Render the critical dates management page."""
    
    st.header("📅 Critical Dates & Notifications")
    
    dates_manager = CriticalDatesManager(supabase)
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Upcoming Dates", "➕ Add Date", "⚙️ Notification Settings"])
    
    with tab1:
        render_upcoming_dates_tab(supabase, dates_manager)
    
    with tab2:
        render_add_date_tab(supabase, dates_manager)
    
    with tab3:
        render_notification_settings_tab(supabase, dates_manager)


def render_upcoming_dates_tab(supabase, dates_manager):
    """Render the upcoming dates view."""
    
    st.subheader("Upcoming Critical Dates")
    
    # Filter options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        days_ahead = st.selectbox("Show dates within:", [30, 60, 90, 180, 365], index=2)
    
    with col2:
        date_type_filter = st.selectbox("Filter by type:", ["All"] + dates_manager.DATE_TYPES)
    
    with col3:
        urgency_filter = st.selectbox("Urgency:", ["All", "Critical (< 14 days)", "High (< 30 days)", "Medium (< 90 days)"])
    
    with col4:
        # Get unique leases for filtering
        try:
            leases_response = supabase.table("leases").select("id, property_address").eq("status", "APPROVED").execute()
            lease_options = ["All Leases"] + [f"{l['property_address']}" for l in (leases_response.data or [])]
            lease_filter = st.selectbox("Filter by lease:", lease_options)
        except:
            lease_filter = "All Leases"
    
    st.markdown("---")
    
    # Fetch upcoming dates
    upcoming_dates = dates_manager.get_upcoming_dates(days_ahead=days_ahead)
    
    if not upcoming_dates:
        st.info("📭 No upcoming critical dates within the selected timeframe.")
        return
    
    # Apply filters
    today = datetime.now().date()
    
    filtered_dates = []
    for date_record in upcoming_dates:
        lease = date_record.get("leases", {})
        
        # Type filter
        if date_type_filter != "All" and date_record["date_type"] != date_type_filter:
            continue
        
        # Lease filter
        if lease_filter != "All Leases":
            if lease.get("property_address") != lease_filter:
                continue
        
        # Urgency filter
        date_value = datetime.strptime(date_record["date_value"], "%Y-%m-%d").date()
        days_until = (date_value - today).days
        
        if urgency_filter == "Critical (< 14 days)" and days_until >= 14:
            continue
        elif urgency_filter == "High (< 30 days)" and days_until >= 30:
            continue
        elif urgency_filter == "Medium (< 90 days)" and days_until >= 90:
            continue
        
        filtered_dates.append(date_record)
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    critical_count = sum(1 for d in filtered_dates if (datetime.strptime(d["date_value"], "%Y-%m-%d").date() - today).days < 14)
    high_count = sum(1 for d in filtered_dates if 14 <= (datetime.strptime(d["date_value"], "%Y-%m-%d").date() - today).days < 30)
    medium_count = sum(1 for d in filtered_dates if 30 <= (datetime.strptime(d["date_value"], "%Y-%m-%d").date() - today).days < 90)
    
    with col1:
        st.metric("Total Upcoming", len(filtered_dates))
    with col2:
        st.metric("Critical (< 14d)", critical_count, delta=f"-{critical_count}" if critical_count > 0 else None, delta_color="inverse")
    with col3:
        st.metric("High (< 30d)", high_count)
    with col4:
        st.metric("Medium (< 90d)", medium_count)
    
    st.markdown("---")
    
    # Display dates
    for date_record in filtered_dates:
        lease = date_record.get("leases", {})
        date_value = datetime.strptime(date_record["date_value"], "%Y-%m-%d").date()
        days_until = (date_value - today).days
        
        # Determine urgency color
        if days_until < 14:
            urgency_color = "🔴"
            urgency_label = "CRITICAL"
        elif days_until < 30:
            urgency_color = "🟠"
            urgency_label = "HIGH"
        elif days_until < 90:
            urgency_color = "🟡"
            urgency_label = "MEDIUM"
        else:
            urgency_color = "🟢"
            urgency_label = "LOW"
        
        with st.expander(f"{urgency_color} **Lease #{lease.get('id', 'N/A')}** - {lease.get('property_address', 'N/A')} | {date_record['date_type']} - {date_value.strftime('%b %d, %Y')} ({days_until} days)"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Lease ID:** #{lease.get('id', 'N/A')}")
                st.markdown(f"**Property:** {lease.get('property_address', 'N/A')}")
                st.markdown(f"**Tenant:** {lease.get('tenant_name', 'N/A')}")
                st.markdown(f"**Date Type:** {date_record['date_type']}")
                st.markdown(f"**Date:** {date_value.strftime('%B %d, %Y')}")
                st.markdown(f"**Days Until:** {days_until} days ({urgency_label})")
                
                if date_record.get("description"):
                    st.markdown(f"**Description:** {date_record['description']}")
                
                # Show notification status
                notifications_sent = date_record.get("notifications_sent", [])
                if notifications_sent:
                    st.markdown(f"**Notifications Sent:** {len(notifications_sent)} ({', '.join(map(str, sorted(notifications_sent, reverse=True)))} days before)")
                else:
                    st.markdown(f"**Notifications Sent:** None yet")
            
            with col2:
                st.markdown(f"**Lease #{lease.get('id', 'N/A')}**")
                if st.button("🔕 Disable", key=f"disable_{date_record['id']}"):
                    if dates_manager.mark_date_inactive(date_record["id"]):
                        st.success("Date disabled")
                        st.rerun()
                    else:
                        st.error("Failed to disable")


def render_add_date_tab(supabase, dates_manager):
    """Render the add critical date form."""
    
    st.subheader("Add New Critical Date")
    
    with st.form("add_critical_date_form"):
        # Select lease
        leases_response = supabase.table("leases").select("id, property_address, tenant_name").eq("status", "APPROVED").execute()
        leases = leases_response.data if leases_response.data else []
        
        if not leases:
            st.warning("No approved leases available. Please approve leases first.")
            st.form_submit_button("Add Date", disabled=True)
            return
        
        lease_options = {f"#{lease['id']} - {lease['property_address']} ({lease['tenant_name']})": lease['id'] for lease in leases}
        selected_lease = st.selectbox("Select Lease", list(lease_options.keys()))
        
        col1, col2 = st.columns(2)
        
        with col1:
            date_type = st.selectbox("Date Type", dates_manager.DATE_TYPES)
        
        with col2:
            date_value = st.date_input("Date", min_value=datetime.now().date())
        
        description = st.text_area("Description (optional)", placeholder="Additional notes about this date...")
        
        st.markdown("**Notification Intervals (days before):**")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        intervals = []
        with col1:
            if st.checkbox("90 days", value=True):
                intervals.append(90)
        with col2:
            if st.checkbox("60 days", value=True):
                intervals.append(60)
        with col3:
            if st.checkbox("30 days", value=True):
                intervals.append(30)
        with col4:
            if st.checkbox("14 days", value=True):
                intervals.append(14)
        with col5:
            if st.checkbox("7 days", value=True):
                intervals.append(7)
        with col6:
            if st.checkbox("1 day", value=True):
                intervals.append(1)
        
        submitted = st.form_submit_button("Add Critical Date", use_container_width=True, type="primary")
        
        if submitted:
            lease_id = lease_options[selected_lease]
            
            if dates_manager.add_critical_date(
                lease_id=lease_id,
                date_type=date_type,
                date_value=date_value.isoformat(),
                description=description if description else None,
                notification_intervals=intervals if intervals else None
            ):
                st.success(f"✅ Critical date added successfully!")
                st.balloons()
            else:
                st.error("Failed to add critical date. Please try again.")


def render_notification_settings_tab(supabase, dates_manager):
    """Render notification settings and manual trigger."""
    
    st.subheader("Notification Settings")
    
    st.info("""
    **📧 Automatic Email Notifications**
    
    The system automatically checks for upcoming critical dates daily and sends email reminders to clients at the configured intervals.
    
    **Default Notification Intervals:**
    - 90 days before
    - 60 days before
    - 30 days before
    - 14 days before
    - 7 days before
    - 1 day before
    """)
    
    st.markdown("---")
    
    st.subheader("Manual Notification Check")
    
    if st.button("🔔 Check & Send Notifications Now", use_container_width=True, type="primary"):
        with st.spinner("Checking critical dates and sending notifications..."):
            result = dates_manager.check_and_send_notifications()
            
            if result.get("success"):
                st.success(f"""
                ✅ Notification check complete!
                
                - **Dates Checked:** {result['checked_dates']}
                - **Notifications Sent:** {result['notifications_sent']}
                - **Errors:** {result['errors']}
                """)
            else:
                st.error(f"❌ Notification check failed: {result.get('error')}")
    
    st.markdown("---")
    
    st.subheader("📊 Notification History")
    
    # Show recent notifications (this would require a notifications_log table)
    st.info("Notification history tracking coming soon...")
