"""
LeaseAI - Home Dashboard
Main navigation and overview for the LeaseAI platform
"""

import streamlit as st
from datetime import datetime
from supabase import create_client
import config

# Initialize Supabase
try:
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

# Page config
st.set_page_config(
    page_title="LeaseAI | Enterprise Lease Management",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .feature-card {
        background: #1a1f2e;
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 2rem;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        border-color: #764ba2;
    }
    .stat-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3561 100%);
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
    }
    .stat-label {
        color: #8892b0;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    .ip-badge {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏢 LeaseAI</h1>
    <h2>Enterprise Lease Intelligence Platform</h2>
    <p style="font-size: 1.1rem; margin-top: 1rem; opacity: 0.9;">
        AI-powered lease abstraction • Amendment Resolution Graph™ • ASC 842 compliance
    </p>
</div>
""", unsafe_allow_html=True)

# Quick Stats
col1, col2, col3, col4 = st.columns(4)

try:
    # Get lease count
    leases_count = sb.table("leases").select("id", count="exact").execute()
    total_leases = leases_count.count if hasattr(leases_count, 'count') else 0
    
    # Get amendment count
    amendments_count = sb.table("amendments").select("id", count="exact").execute()
    total_amendments = amendments_count.count if hasattr(amendments_count, 'count') else 0
    
    # Get pending reviews
    pending_leases = sb.table("leases").select("id", count="exact").eq("status", "READY FOR REVIEW").execute()
    pending_count = pending_leases.count if hasattr(pending_leases, 'count') else 0
    
    # Get approved count
    approved_leases = sb.table("leases").select("id", count="exact").eq("status", "APPROVED").execute()
    approved_count = approved_leases.count if hasattr(approved_leases, 'count') else 0
    
except Exception as e:
    total_leases = 0
    total_amendments = 0
    pending_count = 0
    approved_count = 0

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{total_leases}</div>
        <div class="stat-label">Total Leases</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{total_amendments}</div>
        <div class="stat-label">Amendments Tracked</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{pending_count}</div>
        <div class="stat-label">Pending Review</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{approved_count}</div>
        <div class="stat-label">Approved</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Features Section
st.markdown("## 🚀 Platform Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>🔗 Amendment Resolution Graph™</h3>
        <span class="ip-badge">$5.6M IP ASSET</span>
        <p style="margin-top: 1rem;">
            Proprietary amendment tracking system. Map amendment chains, track clause-level 
            modifications, and query controlling values at any point in time.
        </p>
        <p style="color: #667eea; font-weight: 600;">
            ✓ Visual amendment timelines<br>
            ✓ Clause version control<br>
            ✓ Query engine for any date<br>
            ✓ Before/after comparisons
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h3>📊 ASC 842 Compliance</h3>
        <p>
            Automated compliance engine for ASC 842 and IFRS 16 lease accounting standards.
            Generate journal entries, calculate lease liabilities, and maintain audit trails.
        </p>
        <p style="color: #667eea; font-weight: 600;">
            ✓ Automated journal entries<br>
            ✓ Lease liability calculations<br>
            ✓ ROU asset tracking<br>
            ✓ Audit-ready reports
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>🤖 AI Lease Extraction</h3>
        <p>
            Extract 84+ lease fields with industry-leading accuracy. Supports both digital 
            and scanned PDFs with OCR fallback (AWS Textract + Tesseract).
        </p>
        <p style="color: #667eea; font-weight: 600;">
            ✓ 84 comprehensive fields<br>
            ✓ OCR for scanned documents<br>
            ✓ Confidence scoring<br>
            ✓ GPT-4o powered extraction
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h3>📅 Critical Dates</h3>
        <p>
            Never miss a renewal, rent escalation, or option deadline. Automated 
            date extraction and multi-interval notifications.
        </p>
        <p style="color: #667eea; font-weight: 600;">
            ✓ Auto-extracted from leases<br>
            ✓ Email notifications<br>
            ✓ Customizable intervals<br>
            ✓ Renewal tracking
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Quick Actions
st.markdown("## ⚡ Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📤 Upload New Lease", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📤_Upload_Lease.py")

with col2:
    if st.button("🔗 View Amendment Graph™", use_container_width=True):
        st.switch_page("pages/3_🔗_Amendment_Graph.py")

with col3:
    if st.button("📋 Review Leases", use_container_width=True):
        st.switch_page("pages/2_📋_Lease_Review.py")

st.markdown("<br><br>", unsafe_allow_html=True)

# Recent Activity
st.markdown("## 📈 Recent Activity")

try:
    recent_leases = sb.table("leases").select("*").order("created_at", desc=True).limit(5).execute()
    
    if recent_leases.data:
        for lease in recent_leases.data:
            status_emoji = {
                "READY FOR REVIEW": "🟡",
                "APPROVED": "🟢",
                "PROCESSING": "🔵",
                "FLAGGED": "🔴"
            }.get(lease.get('status', ''), "⚪")
            
            created = lease.get('created_at', '')
            try:
                created_date = datetime.fromisoformat(created.replace('Z', '+00:00')).strftime("%b %d, %Y %I:%M %p")
            except:
                created_date = created
            
            st.markdown(f"""
            **{lease.get('property_address', 'Unknown')}** • {lease.get('tenant_name', 'Unknown')}  
            {status_emoji} {lease.get('status', 'UNKNOWN')} • {created_date}
            """)
            st.markdown("---")
    else:
        st.info("No leases yet. Upload your first lease to get started!")
        
except Exception as e:
    st.error(f"Error loading recent activity: {e}")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem; border-top: 1px solid #2d3561;">
    <p><strong>LeaseAI Enterprise Platform</strong></p>
    <p>Amendment Resolution Graph™ • Proprietary IP • Enterprise-Grade Security</p>
    <p style="font-size: 0.85rem;">© 2026 LeaseAI • Built in Vancouver, BC</p>
</div>
""", unsafe_allow_html=True)
