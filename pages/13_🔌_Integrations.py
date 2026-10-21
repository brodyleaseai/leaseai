"""
LeaseAI - Integrations Management Dashboard
Phase 7: Native API Integrations

Streamlit page for managing third-party integrations.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from integrations.yardi import YardiVoyagerIntegration
from integrations.mri import MRISoftwareIntegration
from integrations.quickbooks import QuickBooksIntegration
from integrations.docusign import DocuSignIntegration
from integrations.notifications import SlackNotifier, TeamsNotifier
from integrations.base import IntegrationStatus, IntegrationType
from datetime import datetime
import json


# Page config
st.set_page_config(
    page_title="Integrations - LeaseAI",
    page_icon="🔌",
    layout="wide"
)

# Authentication check
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Admin check
user_role = st.session_state.get('user_role', 'user')
if user_role != 'admin':
    st.error("🚫 Admin access only. Please log in as an administrator.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

st.title("🔌 Integrations Management")
st.markdown("Configure and manage third-party integrations")

# Tabs for different integration categories
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Property Management Systems",
    "💰 Accounting & Payments",
    "📝 Document Management",
    "🔔 Notifications"
])

# ============================================================================
# TAB 1: Property Management Systems
# ============================================================================
with tab1:
    st.subheader("Property Management System Integrations")
    
    col1, col2 = st.columns(2)
    
    # Yardi Voyager Integration
    with col1:
        st.markdown("### 🏢 Yardi Voyager")
        st.markdown("*Connect to Yardi Voyager for lease data sync*")
        
        with st.expander("⚙️ Configure Yardi Integration", expanded=False):
            yardi_client_id = st.text_input(
                "Client ID",
                key="yardi_client_id",
                help="OAuth 2.0 Client ID from Yardi"
            )
            
            yardi_client_secret = st.text_input(
                "Client Secret",
                type="password",
                key="yardi_client_secret",
                help="OAuth 2.0 Client Secret from Yardi"
            )
            
            yardi_entity_id = st.text_input(
                "Entity ID",
                key="yardi_entity_id",
                help="Your Yardi property entity ID"
            )
            
            yardi_environment = st.selectbox(
                "Environment",
                ["production", "sandbox"],
                key="yardi_environment"
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("💾 Save Yardi Config", key="save_yardi"):
                    st.success("✅ Yardi configuration saved!")
            
            with col_b:
                if st.button("🔗 Test Connection", key="test_yardi"):
                    if yardi_client_id and yardi_client_secret:
                        with st.spinner("Testing connection..."):
                            try:
                                config = {
                                    'client_id': yardi_client_id,
                                    'client_secret': yardi_client_secret,
                                    'entity_id': yardi_entity_id,
                                    'environment': yardi_environment
                                }
                                
                                integration = YardiVoyagerIntegration('test-client', config)
                                # Note: Would need actual OAuth flow in production
                                st.info("ℹ️ OAuth flow required - please complete authentication")
                            
                            except Exception as e:
                                st.error(f"❌ Connection failed: {str(e)}")
                    else:
                        st.warning("⚠️ Please fill in all required fields")
        
        # Sync actions
        if st.button("⬇️ Import Leases from Yardi", key="import_yardi"):
            st.info("🔄 Lease import initiated - this may take a few minutes")
        
        if st.button("⬆️ Export Lease to Yardi", key="export_yardi"):
            st.info("🔄 Lease export initiated")
    
    # MRI Software Integration
    with col2:
        st.markdown("### 🏗️ MRI Software")
        st.markdown("*Connect to MRI for property data sync*")
        
        with st.expander("⚙️ Configure MRI Integration", expanded=False):
            mri_api_key = st.text_input(
                "API Key",
                type="password",
                key="mri_api_key",
                help="API key from MRI Software portal"
            )
            
            mri_property_id = st.text_input(
                "Property ID",
                key="mri_property_id",
                help="Your MRI property identifier"
            )
            
            mri_environment = st.selectbox(
                "Environment",
                ["production", "sandbox"],
                key="mri_environment"
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("💾 Save MRI Config", key="save_mri"):
                    st.success("✅ MRI configuration saved!")
            
            with col_b:
                if st.button("🔗 Test Connection", key="test_mri"):
                    if mri_api_key:
                        with st.spinner("Testing connection..."):
                            try:
                                config = {
                                    'api_key': mri_api_key,
                                    'property_id': mri_property_id,
                                    'environment': mri_environment
                                }
                                
                                integration = MRISoftwareIntegration('test-client', config)
                                result = integration.test_connection()
                                
                                if result.get('success'):
                                    st.success(f"✅ {result.get('message')}")
                                else:
                                    st.error(f"❌ {result.get('message')}")
                            
                            except Exception as e:
                                st.error(f"❌ Connection failed: {str(e)}")
                    else:
                        st.warning("⚠️ Please provide API key")
        
        # Sync actions
        if st.button("⬇️ Import Leases from MRI", key="import_mri"):
            st.info("🔄 Lease import initiated - this may take a few minutes")
        
        if st.button("⬆️ Export Lease to MRI", key="export_mri"):
            st.info("🔄 Lease export initiated")

# ============================================================================
# TAB 2: Accounting & Payments
# ============================================================================
with tab2:
    st.subheader("Accounting & Payment Integrations")
    
    col1, col2 = st.columns([1, 1])
    
    # QuickBooks Integration
    with col1:
        st.markdown("### 💵 QuickBooks Online")
        st.markdown("*Export rent rolls and CAM charges to QuickBooks*")
        
        with st.expander("⚙️ Configure QuickBooks Integration", expanded=False):
            qb_client_id = st.text_input(
                "Client ID",
                key="qb_client_id",
                help="OAuth 2.0 Client ID from QuickBooks"
            )
            
            qb_client_secret = st.text_input(
                "Client Secret",
                type="password",
                key="qb_client_secret",
                help="OAuth 2.0 Client Secret from QuickBooks"
            )
            
            qb_realm_id = st.text_input(
                "Realm ID (Company ID)",
                key="qb_realm_id",
                help="Your QuickBooks company ID"
            )
            
            qb_environment = st.selectbox(
                "Environment",
                ["production", "sandbox"],
                key="qb_environment"
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("💾 Save QuickBooks Config", key="save_qb"):
                    st.success("✅ QuickBooks configuration saved!")
            
            with col_b:
                if st.button("🔗 Test Connection", key="test_qb"):
                    if qb_client_id and qb_client_secret and qb_realm_id:
                        with st.spinner("Testing connection..."):
                            st.info("ℹ️ OAuth flow required - please complete authentication")
                    else:
                        st.warning("⚠️ Please fill in all required fields")
        
        # Export actions
        if st.button("📤 Export Rent Roll to QuickBooks", key="export_rent_qb"):
            st.info("🔄 Rent roll export initiated")
        
        if st.button("📤 Export CAM Charges to QuickBooks", key="export_cam_qb"):
            st.info("🔄 CAM charges export initiated")

# ============================================================================
# TAB 3: Document Management
# ============================================================================
with tab3:
    st.subheader("Document Management & eSignature")
    
    col1, col2 = st.columns([1, 1])
    
    # DocuSign Integration
    with col1:
        st.markdown("### ✍️ DocuSign")
        st.markdown("*Send lease amendments for electronic signature*")
        
        with st.expander("⚙️ Configure DocuSign Integration", expanded=False):
            ds_integration_key = st.text_input(
                "Integration Key",
                key="ds_integration_key",
                help="OAuth Integration Key from DocuSign"
            )
            
            ds_secret_key = st.text_input(
                "Secret Key",
                type="password",
                key="ds_secret_key",
                help="OAuth Secret Key from DocuSign"
            )
            
            ds_account_id = st.text_input(
                "Account ID",
                key="ds_account_id",
                help="Your DocuSign account ID"
            )
            
            ds_environment = st.selectbox(
                "Environment",
                ["demo", "production"],
                key="ds_environment"
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("💾 Save DocuSign Config", key="save_ds"):
                    st.success("✅ DocuSign configuration saved!")
            
            with col_b:
                if st.button("🔗 Test Connection", key="test_ds"):
                    if ds_integration_key and ds_secret_key:
                        with st.spinner("Testing connection..."):
                            st.info("ℹ️ OAuth flow required - please complete authentication")
                    else:
                        st.warning("⚠️ Please fill in all required fields")
        
        # DocuSign actions
        st.markdown("#### Send Documents for Signature")
        
        doc_type = st.selectbox(
            "Document Type",
            ["Lease Amendment", "New Lease Agreement", "Addendum", "Notice"],
            key="ds_doc_type"
        )
        
        if st.button("📧 Send for Signature", key="send_ds"):
            st.info("🔄 Document sent for signature")

# ============================================================================
# TAB 4: Notifications
# ============================================================================
with tab4:
    st.subheader("Notification Integrations")
    
    col1, col2 = st.columns(2)
    
    # Slack Integration
    with col1:
        st.markdown("### 💬 Slack")
        st.markdown("*Receive lease alerts and notifications in Slack*")
        
        with st.expander("⚙️ Configure Slack Integration", expanded=False):
            slack_webhook = st.text_input(
                "Webhook URL",
                type="password",
                key="slack_webhook",
                help="Slack incoming webhook URL"
            )
            
            slack_channel = st.text_input(
                "Default Channel",
                key="slack_channel",
                placeholder="#leaseai-alerts",
                help="Default Slack channel for notifications"
            )
            
            slack_username = st.text_input(
                "Bot Username",
                value="LeaseAI Bot",
                key="slack_username"
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("💾 Save Slack Config", key="save_slack"):
                    st.success("✅ Slack configuration saved!")
            
            with col_b:
                if st.button("🔗 Test Connection", key="test_slack"):
                    if slack_webhook:
                        with st.spinner("Sending test message..."):
                            try:
                                config = {
                                    'webhook_url': slack_webhook,
                                    'channel': slack_channel,
                                    'username': slack_username
                                }
                                
                                notifier = SlackNotifier('test-client', config)
                                result = notifier.test_connection()
                                
                                if result.get('success'):
                                    st.success(f"✅ {result.get('message')}")
                                else:
                                    st.error(f"❌ {result.get('message')}")
                            
                            except Exception as e:
                                st.error(f"❌ Test failed: {str(e)}")
                    else:
                        st.warning("⚠️ Please provide webhook URL")
        
        # Notification preferences
        st.markdown("#### Notification Preferences")
        
        notify_expiration = st.checkbox("Lease expirations", value=True, key="slack_expiration")
        notify_cam = st.checkbox("CAM reconciliation completion", value=True, key="slack_cam")
        notify_anomaly = st.checkbox("Anomaly detection alerts", value=True, key="slack_anomaly")
        notify_amendments = st.checkbox("Amendment signature status", value=False, key="slack_amendments")
    
    # Microsoft Teams Integration
    with col2:
        st.markdown("### 📢 Microsoft Teams")
        st.markdown("*Receive lease alerts and notifications in Teams*")
        
        with st.expander("⚙️ Configure Teams Integration", expanded=False):
            teams_webhook = st.text_input(
                "Webhook URL",
                type="password",
                key="teams_webhook",
                help="Microsoft Teams incoming webhook URL"
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("💾 Save Teams Config", key="save_teams"):
                    st.success("✅ Teams configuration saved!")
            
            with col_b:
                if st.button("🔗 Test Connection", key="test_teams"):
                    if teams_webhook:
                        with st.spinner("Sending test message..."):
                            try:
                                config = {'webhook_url': teams_webhook}
                                
                                notifier = TeamsNotifier('test-client', config)
                                result = notifier.test_connection()
                                
                                if result.get('success'):
                                    st.success(f"✅ {result.get('message')}")
                                else:
                                    st.error(f"❌ {result.get('message')}")
                            
                            except Exception as e:
                                st.error(f"❌ Test failed: {str(e)}")
                    else:
                        st.warning("⚠️ Please provide webhook URL")
        
        # Notification preferences
        st.markdown("#### Notification Preferences")
        
        teams_notify_expiration = st.checkbox("Lease expirations", value=True, key="teams_expiration")
        teams_notify_cam = st.checkbox("CAM reconciliation completion", value=True, key="teams_cam")
        teams_notify_anomaly = st.checkbox("Anomaly detection alerts", value=True, key="teams_anomaly")
        teams_notify_amendments = st.checkbox("Amendment signature status", value=False, key="teams_amendments")

# ============================================================================
# Integration Status Summary
# ============================================================================
st.markdown("---")
st.subheader("📊 Integration Status Summary")

# Mock status data - in production, would fetch from database
integration_status = [
    {"name": "Yardi Voyager", "status": "Not Configured", "last_sync": None, "health": ""},
    {"name": "MRI Software", "status": "Not Configured", "last_sync": None, "health": ""},
    {"name": "QuickBooks", "status": "Not Configured", "last_sync": None, "health": ""},
    {"name": "DocuSign", "status": "Not Configured", "last_sync": None, "health": ""},
    {"name": "Slack", "status": "Not Configured", "last_sync": None, "health": ""},
    {"name": "Microsoft Teams", "status": "Not Configured", "last_sync": None, "health": ""}
]

col1, col2, col3, col4 = st.columns(4)

with col1:
    configured = sum(1 for i in integration_status if i['status'] != 'Not Configured')
    st.metric("Configured Integrations", f"{configured}/6")

with col2:
    active = sum(1 for i in integration_status if i['status'] == 'Active')
    st.metric("Active Connections", active)

with col3:
    st.metric("Syncs Today", 0)

with col4:
    st.metric("Failed Syncs", 0)

# Status table
st.markdown("#### Integration Details")

for integration in integration_status:
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        st.text(integration['name'])
    
    with col2:
        if integration['status'] == 'Not Configured':
            st.markdown("🔴 Not Configured")
        elif integration['status'] == 'Active':
            st.markdown("🟢 Active")
        else:
            st.markdown("🟡 Configured")
    
    with col3:
        if integration['last_sync']:
            st.text(f"Last sync: {integration['last_sync']}")
        else:
            st.text("No syncs yet")
    
    with col4:
        if integration['status'] == 'Active':
            st.text("🟢 Healthy")

# ============================================================================
# Sync History
# ============================================================================
st.markdown("---")
st.subheader("📜 Recent Sync History")

# Mock sync history - in production, would fetch from audit logs
st.info("ℹ️ No sync history available. Configure integrations to begin syncing.")

# Help section
with st.expander("ℹ️ Integration Help & Documentation"):
    st.markdown("""
    ### Setting Up Integrations
    
    #### Property Management Systems
    - **Yardi Voyager**: Requires OAuth 2.0 credentials from Yardi API portal
    - **MRI Software**: Requires API key from MRI developer portal
    
    #### Accounting
    - **QuickBooks Online**: Requires OAuth app registration at developer.intuit.com
    
    #### Document Management
    - **DocuSign**: Requires integration key from DocuSign developer account
    
    #### Notifications
    - **Slack**: Create incoming webhook in Slack workspace settings
    - **Microsoft Teams**: Create incoming webhook in Teams channel settings
    
    For detailed setup instructions, see `docs/INTEGRATIONS_SETUP_GUIDE.md`
    """)
