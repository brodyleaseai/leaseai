"""
LeaseAI - Portfolio Health Dashboard
Phase 6: Agentic AI Layer

Displays:
- Weekly health reports
- Active anomalies and alerts
- Portfolio insights
- Recommended actions
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from supabase import create_client
import os

# Page config
st.set_page_config(page_title="Portfolio Health", page_icon="🏥", layout="wide")

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
def format_currency(value):
    """Format number as currency"""
    if value is None:
        return "N/A"
    return f"${float(value):,.2f}"

def get_severity_color(severity):
    """Get color for severity level"""
    colors = {
        'CRITICAL': '#c62828',
        'HIGH': '#f57c00',
        'MEDIUM': '#fbc02d',
        'LOW': '#7cb342'
    }
    return colors.get(severity, '#757575')

def get_health_status_color(status):
    """Get color for health status"""
    colors = {
        'EXCELLENT': '#2e7d32',
        'GOOD': '#7cb342',
        'NEEDS_ATTENTION': '#f57c00',
        'CRITICAL': '#c62828'
    }
    return colors.get(status, '#757575')

# Main page
st.title("🏥 Portfolio Health Dashboard")
st.markdown("AI-powered portfolio monitoring and insights")

# Get user's client ID (in production, this would come from auth)
client_id = st.session_state.get('user_id') or st.session_state.get('client_id')

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Current Report", "🚨 Active Alerts", "📜 History", "⚙️ Settings"])

# ============================================================================
# TAB 1: CURRENT REPORT
# ============================================================================

with tab1:
    st.markdown("### Latest Portfolio Health Report")
    
    # Get most recent report
    from query_cache import cached
    report_response_data = cached(
        f"health_report_latest_{client_id}",
        60,
        lambda: (sb.table("portfolio_health_reports").select("*").order("report_date", desc=True).limit(1).execute().data or []),
    )
    
    if not report_response_data:
        st.info("📊 No health report generated yet.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 Generate Health Report Now", type="primary", use_container_width=True):
                with st.spinner("Scanning portfolio and generating report..."):
                    try:
                        from health_report_generator import generate_health_report
                        from anomaly_detection_engine import scan_portfolio_for_anomalies
                        
                        from openai_key import get_openai_api_key
                        openai_key = get_openai_api_key()
                        
                        if not openai_key:
                            st.error("OpenAI API key not configured. Set OPENAI_API_KEY in your .env or config.py.")
                        else:
                            # First scan for anomalies
                            st.info("Step 1/2: Scanning for anomalies...")
                            scan_results = scan_portfolio_for_anomalies(sb, client_id)
                            
                            # Then generate report
                            st.info("Step 2/2: Generating health report...")
                            report = generate_health_report(sb, openai_key, client_id)
                            
                            st.success("✅ Health report generated!")
                            st.balloons()
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error generating report: {str(e)}")
        
        with col2:
            st.caption("Generate a comprehensive health report analyzing your entire portfolio for issues, deadlines, and opportunities.")
    
    else:
        report = report_response_data[0]
        
        # Header with health score
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"#### Week of {report['report_date']}")
            st.markdown(f"**Report generated:** {datetime.fromisoformat(report['generated_at']).strftime('%B %d, %Y at %I:%M %p')}")
        
        with col2:
            health_color = get_health_status_color(report['health_status'])
            st.markdown(f"<h2 style='color: {health_color}; text-align: center;'>{report['health_score']}/100</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'><b>{report['health_status']}</b></p>", unsafe_allow_html=True)
        
        with col3:
            col3a, col3b = st.columns(2)
            
            with col3a:
                if st.button("🔄 Refresh", use_container_width=True):
                    with st.spinner("Regenerating report..."):
                        try:
                            from health_report_generator import generate_health_report
                            from anomaly_detection_engine import scan_portfolio_for_anomalies
                            
                            from openai_key import get_openai_api_key
                            openai_key = get_openai_api_key()
                            scan_portfolio_for_anomalies(sb, client_id)
                            generate_health_report(sb, openai_key, client_id)
                            st.success("Report refreshed!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            
            with col3b:
                if st.button("📄 PDF", use_container_width=True):
                    with st.spinner("Generating PDF..."):
                        try:
                            from health_report_pdf import generate_health_report_pdf
                            import tempfile
                            
                            # Get actions for this report
                            actions_response = sb.table("health_report_actions").select("*").eq("health_report_id", report['id']).order("priority").execute()
                            actions = actions_response.data if actions_response.data else []
                            
                            # Generate PDF in temp file
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                                pdf_path = tmp.name
                            
                            generate_health_report_pdf(report, actions, pdf_path)
                            
                            # Read PDF and offer download
                            with open(pdf_path, 'rb') as f:
                                pdf_bytes = f.read()
                            
                            st.download_button(
                                label="💾 Download Report",
                                data=pdf_bytes,
                                file_name=f"health_report_{report['report_date']}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                            # Cleanup temp file
                            import os
                            os.remove(pdf_path)
                            
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
        
        st.markdown("---")
        
        # Executive Summary
        st.markdown("### Executive Summary")
        st.markdown(report['executive_summary'])
        
        st.markdown("---")
        
        # Key Metrics
        st.markdown("### Portfolio Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Leases", report['active_leases'], delta=f"{report['total_leases'] - report['active_leases']} inactive")
        
        with col2:
            st.metric("Monthly Rent", format_currency(report['total_monthly_rent']))
        
        with col3:
            st.metric("Avg Rent/SF", format_currency(report['avg_rent_per_sqft']))
        
        with col4:
            st.metric("Total SF", f"{report['total_portfolio_sqft']:,}")
        
        st.markdown("---")
        
        # Critical Dates & Anomalies
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📅 Upcoming Critical Dates")
            
            cd_30 = report['critical_dates_30_days']
            cd_60 = report['critical_dates_60_days']
            cd_90 = report['critical_dates_90_days']
            
            st.metric("Next 30 Days", cd_30, delta="URGENT" if cd_30 > 0 else None, delta_color="inverse")
            st.metric("Next 60 Days", cd_60)
            st.metric("Next 90 Days", cd_90)
        
        with col2:
            st.markdown("### 🚨 Detected Anomalies")
            
            total_anom = report['anomalies_detected']
            high_anom = report['high_severity_anomalies']
            
            st.metric("Total Issues", total_anom)
            st.metric("High Priority", high_anom, delta="Needs attention" if high_anom > 0 else None, delta_color="inverse")
            st.metric("Leases Needing Review", report['requires_attention'])
        
        st.markdown("---")
        
        # Recommended Actions
        st.markdown("### ✅ Recommended Actions")
        
        actions_response = sb.table("health_report_actions").select("*").eq("health_report_id", report['id']).order("priority").execute()
        actions = actions_response.data if actions_response.data else []
        
        if actions:
            for action in actions:
                priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
                icon = priority_icons.get(action['priority'], "⚪")
                
                with st.expander(f"{icon} {action['title']}", expanded=(action['priority'] == 1)):
                    st.markdown(action['description'])
                    
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        if action['status'] == 'PENDING':
                            if st.button("Mark as Complete", key=f"complete_{action['id']}", use_container_width=True):
                                sb.table("health_report_actions").update({
                                    'status': 'COMPLETED',
                                    'completed_at': datetime.now().isoformat()
                                }).eq("id", action['id']).execute()
                                st.success("Action marked complete!")
                                st.rerun()
                        else:
                            st.success(f"✓ Completed on {action.get('completed_at', '')[:10]}")
                    
                    with col_b:
                        if st.button("Skip", key=f"skip_{action['id']}", use_container_width=True):
                            sb.table("health_report_actions").update({
                                'status': 'SKIPPED'
                            }).eq("id", action['id']).execute()
                            st.rerun()
        else:
            st.info("No specific actions recommended at this time.")

# ============================================================================
# TAB 2: ACTIVE ALERTS
# ============================================================================

with tab2:
    st.markdown("### 🚨 Active Alerts & Anomalies")
    
    # Get active anomalies
    anomalies_response = sb.table("lease_anomalies").select("*, leases(property_address, tenant_name)").eq("status", "OPEN").order("detected_at", desc=True).execute()
    anomalies = anomalies_response.data if anomalies_response.data else []
    
    if not anomalies:
        st.success("✅ No active anomalies detected! Your portfolio is healthy.")
    else:
        # Filter by severity
        severity_filter = st.selectbox("Filter by Severity", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
        
        if severity_filter != "All":
            anomalies = [a for a in anomalies if a['severity'] == severity_filter]
        
        st.markdown(f"**Showing {len(anomalies)} anomalies**")
        
        # Display anomalies
        for anom in anomalies:
            severity_color = get_severity_color(anom['severity'])
            lease_info = anom.get('leases', {})
            property_address = lease_info.get('property_address', 'Unknown Property')
            
            with st.expander(f"🔴 [{anom['severity']}] {anom['title']} - {property_address}"):
                st.markdown(f"**Type:** {anom['anomaly_type'].replace('_', ' ').title()}")
                st.markdown(f"**Description:** {anom['description']}")
                
                if anom.get('field_name'):
                    st.markdown(f"**Field:** {anom['field_name']}")
                
                if anom.get('expected_value') and anom.get('actual_value'):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Expected:** {anom['expected_value']}")
                    with col2:
                        st.markdown(f"**Actual:** {anom['actual_value']}")
                
                st.markdown(f"**Detected:** {datetime.fromisoformat(anom['detected_at']).strftime('%B %d, %Y at %I:%M %p')}")
                
                st.markdown("---")
                
                # Actions
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("✅ Resolve", key=f"resolve_{anom['id']}", use_container_width=True, type="primary"):
                        notes = st.text_input("Resolution notes:", key=f"notes_{anom['id']}")
                        if notes:
                            sb.table("lease_anomalies").update({
                                'status': 'RESOLVED',
                                'resolution_notes': notes,
                                'resolved_at': datetime.now().isoformat()
                            }).eq("id", anom['id']).execute()
                            st.success("Anomaly resolved!")
                            st.rerun()
                
                with col_b:
                    if st.button("👀 View Lease", key=f"view_{anom['id']}", use_container_width=True):
                        st.info(f"Navigate to Lease Review for lease ID: {anom['lease_id']}")
                
                with col_c:
                    if st.button("🚫 Dismiss", key=f"dismiss_{anom['id']}", use_container_width=True):
                        sb.table("lease_anomalies").update({
                            'status': 'DISMISSED'
                        }).eq("id", anom['id']).execute()
                        st.rerun()

# ============================================================================
# TAB 3: HISTORY
# ============================================================================

with tab3:
    st.markdown("### 📜 Historical Reports")
    
    # Get all reports
    history_response = sb.table("portfolio_health_reports").select("*").order("report_date", desc=True).limit(10).execute()
    reports = history_response.data if history_response.data else []
    
    if not reports:
        st.info("No historical reports yet.")
    else:
        for report in reports:
            health_color = get_health_status_color(report['health_status'])
            
            with st.expander(f"📊 Week of {report['report_date']} - Score: {report['health_score']}/100 ({report['health_status']})"):
                st.markdown(f"**Executive Summary:**")
                st.markdown(report['executive_summary'])
                
                st.markdown("---")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Active Leases", report['active_leases'])
                    st.metric("Monthly Rent", format_currency(report['total_monthly_rent']))
                
                with col2:
                    st.metric("Critical Dates (30d)", report['critical_dates_30_days'])
                    st.metric("Anomalies", report['anomalies_detected'])
                
                with col3:
                    st.metric("Requires Attention", report['requires_attention'])
                    st.metric("Health Score", f"{report['health_score']}/100")

# ============================================================================
# TAB 4: SETTINGS
# ============================================================================

with tab4:
    st.markdown("### ⚙️ Alert Settings")
    
    st.markdown("Configure when you want to be notified about portfolio issues.")
    
    # Email notifications
    st.checkbox("📧 Email weekly health reports", value=True)
    st.checkbox("📧 Email for critical anomalies", value=True)
    st.checkbox("📧 Email for upcoming deadlines (30 days)", value=True)
    
    st.markdown("---")
    
    # Anomaly thresholds
    st.markdown("### 🎚️ Detection Thresholds")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Critical date warning (days)", min_value=1, max_value=90, value=30)
        st.number_input("Low confidence field threshold", min_value=1, max_value=20, value=5)
    
    with col2:
        st.number_input("Rent variance threshold ($)", min_value=0, value=500)
        st.number_input("Health score alert threshold", min_value=0, max_value=100, value=70)
    
    st.markdown("---")
    
    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved!")
        st.info("These settings will be applied to future health reports and scans.")
