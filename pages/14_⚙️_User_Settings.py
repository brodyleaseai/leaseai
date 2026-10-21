"""
LeaseAI - User Settings & Security
Page for managing user account settings including 2FA
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client
import config
from two_factor_auth import render_2fa_setup_page, TwoFactorAuth

# Page config
st.set_page_config(
    page_title="User Settings - LeaseAI",
    page_icon="⚙️",
    layout="wide"
)

# Authentication check
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Initialize Supabase
try:
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

# Get user info
user_id = st.session_state.get('user_id')
user_email = st.session_state.get('user_email')
user_name = st.session_state.get('user_name', 'User')
user_role = st.session_state.get('user_role', 'user')

# Header
st.title("⚙️ User Settings")
st.markdown(f"**User:** {user_name} ({user_email})")
st.markdown(f"**Role:** {user_role.title()}")
st.markdown("---")

# Tabs
tab1, tab2, tab3 = st.tabs(["🔐 Security", "👤 Profile", "🔔 Notifications"])

# ============================================================================
# TAB 1: Security Settings
# ============================================================================
with tab1:
    st.subheader("🔐 Security Settings")
    
    # Two-Factor Authentication Section
    st.markdown("### Two-Factor Authentication (2FA)")
    
    tfa = TwoFactorAuth(sb)
    is_2fa_enabled, _ = tfa.get_user_2fa_status(user_id)
    
    if is_2fa_enabled:
        st.success("✅ 2FA is **ENABLED** on your account")
    else:
        st.warning("⚠️ 2FA is **NOT ENABLED** on your account")
        if user_role == 'admin':
            st.error("🚨 **Admin accounts must have 2FA enabled for security compliance**")
    
    if st.button("Manage 2FA Settings", use_container_width=True):
        st.session_state.show_2fa_page = True
        st.rerun()
    
    if st.session_state.get("show_2fa_page", False):
        st.markdown("---")
        render_2fa_setup_page(sb, user_id, user_email)
    
    st.markdown("---")
    
    # Password Change Section
    st.markdown("### Change Password")
    st.info("ℹ️ Password changes coming soon. Contact admin to reset your password.")
    
    st.markdown("---")
    
    # Session Management
    st.markdown("### Active Sessions")
    st.info("ℹ️ Session management coming soon.")
    
    # Security Log
    st.markdown("---")
    st.markdown("### Recent Security Activity")
    
    try:
        # Fetch recent security-related audit logs for this user
        security_logs = sb.table("audit_log").select("*").eq("user_id", user_id).in_(
            "action_category", ["AUTH", "SECURITY"]
        ).order("created_at", desc=True).limit(10).execute()
        
        if security_logs.data:
            for log in security_logs.data:
                action_type = log.get("action_type", "Unknown")
                timestamp = log.get("created_at", "Unknown")
                ip = log.get("ip_address", "Unknown")
                
                st.markdown(f"- **{action_type}** at {timestamp} from IP {ip}")
        else:
            st.info("No recent security activity")
    
    except Exception as e:
        st.warning(f"Could not load security activity: {str(e)}")

# ============================================================================
# TAB 2: Profile Settings
# ============================================================================
with tab2:
    st.subheader("👤 Profile Settings")
    
    st.markdown("### Account Information")
    
    # Display current profile info
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Name", value=user_name, disabled=True)
        st.text_input("Email", value=user_email, disabled=True)
    
    with col2:
        st.text_input("Role", value=user_role.title(), disabled=True)
        st.text_input("User ID", value=str(user_id), disabled=True)
    
    st.markdown("---")
    st.info("ℹ️ Profile editing coming soon. Contact admin to update your profile.")

# ============================================================================
# TAB 3: Notification Settings
# ============================================================================
with tab3:
    st.subheader("🔔 Notification Settings")
    
    st.markdown("### Email Notifications")
    
    email_lease_uploaded = st.checkbox("Lease upload confirmations", value=True)
    email_lease_ready = st.checkbox("Lease ready for review", value=True)
    email_lease_approved = st.checkbox("Lease approved", value=True)
    email_weekly_summary = st.checkbox("Weekly portfolio summary", value=True)
    email_critical_dates = st.checkbox("Critical date reminders (30/60/90 days)", value=True)
    
    st.markdown("---")
    
    st.markdown("### In-App Notifications")
    
    inapp_lease_updates = st.checkbox("Lease status updates", value=True)
    inapp_system_alerts = st.checkbox("System alerts", value=True)
    
    st.markdown("---")
    
    st.info("ℹ️ Notification preferences coming soon.")
    
    # if st.button("Save Notification Settings", type="primary"):
    #     st.success("✅ Notification settings saved!")

# Footer
st.markdown("---")
st.caption("LeaseAI User Settings • For support, contact support@leaseai.com")
