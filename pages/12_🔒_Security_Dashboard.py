"""
LeaseAI - Security Dashboard
Phase 5: Security Hardening & Enterprise Readiness

Admin dashboard for viewing audit logs, security events, and system security status.
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from supabase import create_client
import json

# Page config
st.set_page_config(page_title="Security Dashboard", page_icon="🔒", layout="wide")

# Load config
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    try:
        from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    except ImportError:
        st.error("⚠️ No secrets configured. Add them to Streamlit secrets or config.py.")
        st.stop()

# Initialize Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

sb = init_supabase()

# Helper functions
def get_severity_color(severity):
    """Get color for severity level"""
    colors = {
        'CRITICAL': '#c62828',
        'HIGH': '#f57c00',
        'MEDIUM': '#fbc02d',
        'LOW': '#7cb342'
    }
    return colors.get(severity, '#757575')

def format_timestamp(ts):
    """Format timestamp for display"""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ts

# Main page
st.title("🔒 Security Dashboard")
st.markdown("Monitor audit logs, security events, and system security status")

# Get user context
user_id = st.session_state.get('user_id')

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📜 Audit Logs", "🚨 Security Events", "🔐 Security Status"])

# ============================================================================
# TAB 1: OVERVIEW
# ============================================================================

with tab1:
    st.markdown("### Security Overview")
    
    # Time range selector
    time_range = st.selectbox("Time Range", ["Last 24 hours", "Last 7 days", "Last 30 days", "Last 90 days"])
    
    days_map = {
        "Last 24 hours": 1,
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 90 days": 90
    }
    days = days_map[time_range]
    
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Get statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Total audit logs
        audit_count_response = sb.table("audit_log").select("id", count="exact").gte("performed_at", cutoff_date).execute()
        total_audits = audit_count_response.count if audit_count_response.count else 0
        st.metric("Total Actions", total_audits)
    
    with col2:
        # Failed actions
        failed_response = sb.table("audit_log").select("id", count="exact").eq("status", "FAILED").gte("performed_at", cutoff_date).execute()
        failed_count = failed_response.count if failed_response.count else 0
        st.metric("Failed Actions", failed_count, delta="⚠️" if failed_count > 0 else None)
    
    with col3:
        # Security events
        security_response = sb.table("security_events").select("id", count="exact").gte("occurred_at", cutoff_date).execute()
        security_count = security_response.count if security_response.count else 0
        st.metric("Security Events", security_count, delta="⚠️" if security_count > 0 else None)
    
    with col4:
        # Unresolved security events
        unresolved_response = sb.table("security_events").select("id", count="exact").eq("resolved", False).gte("occurred_at", cutoff_date).execute()
        unresolved_count = unresolved_response.count if unresolved_response.count else 0
        st.metric("Unresolved Events", unresolved_count, delta="🔴" if unresolved_count > 0 else "✅")
    
    st.markdown("---")
    
    # Action breakdown by category
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Actions by Category")
        
        category_response = sb.table("audit_log").select("action_category").gte("performed_at", cutoff_date).execute()
        
        if category_response.data:
            categories = {}
            for row in category_response.data:
                cat = row.get('action_category', 'UNKNOWN')
                categories[cat] = categories.get(cat, 0) + 1
            
            if categories:
                df = pd.DataFrame(list(categories.items()), columns=['Category', 'Count'])
                df = df.sort_values('Count', ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No actions recorded in this time period")
        else:
            st.info("No audit data available")
    
    with col2:
        st.markdown("### Recent Security Events")
        
        recent_security = sb.table("security_events").select("*").order("occurred_at", desc=True).limit(5).execute()
        
        if recent_security.data:
            for event in recent_security.data:
                severity = event.get('severity', 'UNKNOWN')
                severity_color = get_severity_color(severity)
                
                with st.expander(f"[{severity}] {event.get('event_type', 'Unknown')}"):
                    st.markdown(f"**Description:** {event.get('description', 'N/A')}")
                    st.markdown(f"**Occurred:** {format_timestamp(event.get('occurred_at'))}")
                    st.markdown(f"**User:** {event.get('user_email', 'Unknown')}")
                    st.markdown(f"**IP:** {event.get('ip_address', 'N/A')}")
                    st.markdown(f"**Resolved:** {'✅ Yes' if event.get('resolved') else '❌ No'}")
        else:
            st.success("✅ No security events recorded")
    
    st.markdown("---")
    
    # Recent activity timeline
    st.markdown("### Recent Activity Timeline")
    
    recent_activity = sb.table("audit_log").select("*").order("performed_at", desc=True).limit(20).execute()
    
    if recent_activity.data:
        for log in recent_activity.data:
            col_time, col_user, col_action = st.columns([2, 2, 4])
            
            with col_time:
                st.caption(format_timestamp(log.get('performed_at')))
            
            with col_user:
                st.caption(log.get('user_email', 'System'))
            
            with col_action:
                status_icon = "✅" if log.get('status') == 'SUCCESS' else "❌"
                st.caption(f"{status_icon} {log.get('action_description', 'N/A')}")
    else:
        st.info("No recent activity")

# ============================================================================
# TAB 2: AUDIT LOGS
# ============================================================================

with tab2:
    st.markdown("### Audit Logs")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_user = st.text_input("Filter by User Email")
    
    with col2:
        filter_action = st.selectbox("Filter by Action Category", ["All", "AUTH", "DATA", "ADMIN", "EXPORT", "SECURITY"])
    
    with col3:
        filter_status = st.selectbox("Filter by Status", ["All", "SUCCESS", "FAILED", "PARTIAL"])
    
    # Build query
    query = sb.table("audit_log").select("*")
    
    if filter_user:
        query = query.ilike("user_email", f"%{filter_user}%")
    
    if filter_action != "All":
        query = query.eq("action_category", filter_action)
    
    if filter_status != "All":
        query = query.eq("status", filter_status)
    
    query = query.order("performed_at", desc=True).limit(100)
    
    logs_response = query.execute()
    
    if logs_response.data:
        st.markdown(f"**Showing {len(logs_response.data)} audit logs** (max 100)")
        
        for log in logs_response.data:
            status_icon = "✅" if log.get('status') == 'SUCCESS' else "❌"
            
            with st.expander(f"{status_icon} {format_timestamp(log.get('performed_at'))} - {log.get('action_description', 'N/A')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**User:** {log.get('user_email', 'Unknown')}")
                    st.markdown(f"**User ID:** {log.get('user_id', 'N/A')}")
                    st.markdown(f"**Role:** {log.get('user_role', 'N/A')}")
                    st.markdown(f"**Action Type:** {log.get('action_type', 'N/A')}")
                    st.markdown(f"**Category:** {log.get('action_category', 'N/A')}")
                
                with col2:
                    st.markdown(f"**Resource Type:** {log.get('resource_type', 'N/A')}")
                    st.markdown(f"**Resource ID:** {log.get('resource_id', 'N/A')}")
                    st.markdown(f"**Status:** {log.get('status', 'N/A')}")
                    st.markdown(f"**IP Address:** {log.get('ip_address', 'N/A')}")
                    st.markdown(f"**Session ID:** {log.get('session_id', 'N/A')}")
                
                if log.get('old_values'):
                    st.markdown("**Previous Values:**")
                    try:
                        st.json(json.loads(log['old_values']))
                    except:
                        st.code(log['old_values'])
                
                if log.get('new_values'):
                    st.markdown("**New Values:**")
                    try:
                        st.json(json.loads(log['new_values']))
                    except:
                        st.code(log['new_values'])
                
                if log.get('error_message'):
                    st.error(f"**Error:** {log['error_message']}")
    else:
        st.info("No audit logs found matching the filters")

# ============================================================================
# TAB 3: SECURITY EVENTS
# ============================================================================

with tab3:
    st.markdown("### Security Events")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        event_severity = st.selectbox("Filter by Severity", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
    
    with col2:
        event_resolved = st.selectbox("Filter by Status", ["All", "Unresolved", "Resolved"])
    
    # Build query
    query = sb.table("security_events").select("*")
    
    if event_severity != "All":
        query = query.eq("severity", event_severity)
    
    if event_resolved == "Unresolved":
        query = query.eq("resolved", False)
    elif event_resolved == "Resolved":
        query = query.eq("resolved", True)
    
    query = query.order("occurred_at", desc=True).limit(50)
    
    events_response = query.execute()
    
    if events_response.data:
        st.markdown(f"**Showing {len(events_response.data)} security events** (max 50)")
        
        for event in events_response.data:
            severity = event.get('severity', 'UNKNOWN')
            severity_color = get_severity_color(severity)
            resolved_icon = "✅" if event.get('resolved') else "🔴"
            
            with st.expander(f"{resolved_icon} [{severity}] {event.get('event_type', 'Unknown')} - {format_timestamp(event.get('occurred_at'))}"):
                st.markdown(f"**Description:** {event.get('description', 'N/A')}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Severity:** {severity}")
                    st.markdown(f"**User:** {event.get('user_email', 'Unknown')}")
                    st.markdown(f"**User ID:** {event.get('user_id', 'N/A')}")
                    st.markdown(f"**IP Address:** {event.get('ip_address', 'N/A')}")
                
                with col2:
                    st.markdown(f"**Occurred:** {format_timestamp(event.get('occurred_at'))}")
                    st.markdown(f"**Resolved:** {'Yes' if event.get('resolved') else 'No'}")
                    if event.get('resolved'):
                        st.markdown(f"**Resolved At:** {format_timestamp(event.get('resolved_at'))}")
                        st.markdown(f"**Resolved By:** {event.get('resolved_by', 'N/A')}")
                
                if event.get('details'):
                    st.markdown("**Details:**")
                    try:
                        st.json(json.loads(event['details']))
                    except:
                        st.code(event['details'])
                
                if event.get('resolution_notes'):
                    st.info(f"**Resolution Notes:** {event['resolution_notes']}")
                
                # Resolution action (if unresolved)
                if not event.get('resolved'):
                    with st.form(key=f"resolve_{event['id']}"):
                        resolution_notes = st.text_area("Resolution Notes")
                        if st.form_submit_button("Mark as Resolved"):
                            try:
                                sb.table("security_events").update({
                                    'resolved': True,
                                    'resolved_at': datetime.now().isoformat(),
                                    'resolved_by': user_id,
                                    'resolution_notes': resolution_notes
                                }).eq("id", event['id']).execute()
                                
                                st.success("Security event marked as resolved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
    else:
        st.success("✅ No security events found")

# ============================================================================
# TAB 4: SECURITY STATUS
# ============================================================================

with tab4:
    st.markdown("### System Security Status")
    
    # Security checklist
    st.markdown("### 🔐 Security Checklist")
    
    checklist = {
        "Audit Logging Enabled": True,
        "Supabase RLS Enabled": True,
        "HTTPS/TLS Enabled": True,
        "Database Backups Configured": True,
        "2FA Available": True,
        "Static Code Analysis": False,  # Will be enabled after setup
        "SOC 2 Compliance In Progress": False
    }
    
    for item, status in checklist.items():
        status_icon = "✅" if status else "⏸️"
        st.markdown(f"{status_icon} {item}")
    
    st.markdown("---")
    
    # Backup status
    st.markdown("### 💾 Backup Status")
    
    backup_verifications = sb.table("backup_verifications").select("*").order("verification_date", desc=True).limit(5).execute()
    
    if backup_verifications.data:
        st.success(f"✅ Last backup verified: {format_timestamp(backup_verifications.data[0].get('verification_date'))}")
        
        for backup in backup_verifications.data:
            with st.expander(f"Backup from {backup.get('backup_date')} - {backup.get('status')}"):
                st.markdown(f"**Type:** {backup.get('backup_type')}")
                st.markdown(f"**Verified:** {format_timestamp(backup.get('verification_date'))}")
                st.markdown(f"**Records Restored:** {backup.get('records_restored', 'N/A')}")
                st.markdown(f"**Restore Time:** {backup.get('restore_time_seconds', 'N/A')} seconds")
                if backup.get('notes'):
                    st.info(backup['notes'])
    else:
        st.warning("⚠️ No backup verifications recorded. Run a backup test.")
    
    st.markdown("---")
    
    # Data retention policy
    st.markdown("### 📅 Data Retention Policy")
    
    st.info("""
    **Current Retention Periods:**
    - Audit Logs: 1 year (active), 7 years (archive)
    - Security Events: 1 year
    - Lease Documents: Indefinite (until customer deletion)
    - User Data: Indefinite (GDPR deletion on request)
    - Backups: 30 days (point-in-time recovery)
    """)
    
    st.markdown("---")
    
    # Security recommendations
    st.markdown("### 💡 Security Recommendations")
    
    st.warning("""
    **Next Steps to Improve Security:**
    1. ✅ Enable 2FA for all admin users
    2. ✅ Review and resolve open security events
    3. ⏸️ Set up static code analysis (bandit)
    4. ⏸️ Begin SOC 2 compliance preparation
    5. ⏸️ Purchase cyber liability insurance
    6. ⏸️ Conduct security training for team members
    7. ⏸️ Perform penetration testing
    """)
