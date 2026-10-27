"""
LeaseAI - Home Dashboard
Main navigation and overview for the LeaseAI platform
"""

import streamlit as st
from datetime import datetime
from supabase import create_client
import config
from auth_module import AuthManager

try:
    from observability import init_observability
    init_observability()
except Exception:
    pass

# Page config
st.set_page_config(
    page_title="LeaseAI | Enterprise Lease Management",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Supabase
try:
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    auth = AuthManager(sb)
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

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
        color: #e5e7eb;
    }
    .feature-card h3 {
        color: #ffffff;
        margin-top: 0;
    }
    .feature-card p {
        color: #d1d5db;
        line-height: 1.6;
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
    
    /* Fix text input contrast for better readability */
    input[type="text"], input[type="password"], input[type="email"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #667eea !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
    }
    
    input[type="text"]::placeholder, 
    input[type="password"]::placeholder,
    input[type="email"]::placeholder {
        color: #9ca3af !important;
        opacity: 0.7 !important;
    }
    
    /* Make labels more visible */
    label {
        color: #ffffff !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Streamlit input widget styling */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #667eea !important;
    }
</style>
""", unsafe_allow_html=True)

# Check if user is authenticated
if not st.session_state.get("authenticated", False):
    # Show login page
    st.markdown("""
    <div class="main-header">
        <h1>🏢 LeaseAI</h1>
        <h2>Enterprise Lease Intelligence Platform</h2>
        <p style="font-size: 1.1rem; margin-top: 1rem; opacity: 0.9;">
            AI-powered lease abstraction • Amendment Resolution Graph™ • ASC 842 compliance
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Login Form
    st.markdown("### 🔐 Sign In")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        needs_2fa = st.session_state.get("needs_2fa_verification", False)
        pending_username = st.session_state.get("pending_2fa_username")
        pending_password = st.session_state.get("pending_2fa_password")

        if needs_2fa and pending_username and pending_password:
            st.info("Two-factor authentication required. Enter the 6-digit code from your authenticator app.")
            with st.form("home_2fa_form"):
                totp_code = st.text_input("Verification Code", max_chars=6, placeholder="000000")
                col_a, col_b = st.columns(2)
                with col_a:
                    verify = st.form_submit_button("Verify & Sign In", use_container_width=True, type="primary")
                with col_b:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)

                if cancel:
                    st.session_state.needs_2fa_verification = False
                    st.session_state.pending_2fa_username = None
                    st.session_state.pending_2fa_password = None
                    st.rerun()

                if verify:
                    if totp_code and len(totp_code) == 6:
                        success, role, message, _ = auth.login(pending_username, pending_password, totp_code)
                        if success:
                            st.session_state.needs_2fa_verification = False
                            st.session_state.pending_2fa_username = None
                            st.session_state.pending_2fa_password = None
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("Please enter a 6-digit code")
        else:
            with st.form("login_form"):
                username = st.text_input("Email", placeholder="your.email@company.com")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                
                if submit:
                    if username and password:
                        success, role, message, needs_2fa_next = auth.login(username, password)
                        
                        if needs_2fa_next:
                            st.session_state.needs_2fa_verification = True
                            st.session_state.pending_2fa_username = username
                            st.session_state.pending_2fa_password = password
                            st.rerun()
                        elif success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("Please enter both email and password")
    
    st.stop()

# User is authenticated - show dashboard
try:
    _payment = st.query_params.get("payment")
    if _payment == "success":
        st.success("Payment received. Open Billing to confirm your plan is active.")
    elif _payment == "cancelled":
        st.warning("Checkout cancelled. No charge was made.")
except Exception:
    pass

# Header with user info
col_header1, col_header2 = st.columns([4, 1])

with col_header1:
    st.markdown("""
    <div class="main-header">
        <h1>🏢 LeaseAI</h1>
        <h2>Enterprise Lease Intelligence Platform</h2>
        <p style="font-size: 1.1rem; margin-top: 1rem; opacity: 0.9;">
            AI-powered lease abstraction • Amendment Resolution Graph™ • ASC 842 compliance
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_header2:
    st.markdown("<br>", unsafe_allow_html=True)
    user_name = st.session_state.get('user_name', 'User')
    user_role = st.session_state.get('user_role', 'user').title()
    
    st.markdown(f"""
    <div style="text-align: right; padding: 1rem; background: #1a1f2e; border-radius: 10px; margin-top: 1rem;">
        <div style="color: #667eea; font-weight: 600;">{user_name}</div>
        <div style="color: #8892b0; font-size: 0.85rem;">{user_role}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Logout", use_container_width=True):
        auth.logout()
        st.rerun()

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

user_role = st.session_state.get('user_role', 'user')

if user_role == "admin":
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Upload New Lease", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📤_Upload_Lease.py")
    
    with col2:
        if st.button("🔗 Amendment Graph™", use_container_width=True):
            st.switch_page("pages/3_🔗_Amendment_Graph.py")
    
    with col3:
        if st.button("📊 Admin Dashboard", use_container_width=True):
            st.switch_page("pages/4_📊_Admin_Dashboard.py")
    
    with col4:
        if st.button("📈 ASC 842", use_container_width=True):
            st.switch_page("pages/5_📈_ASC842_Dashboard.py")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        if st.button("📋 Review Leases", use_container_width=True):
            st.switch_page("pages/2_📋_Lease_Review.py")
    
    with col6:
        if st.button("📅 Critical Dates", use_container_width=True):
            st.switch_page("pages/6_📅_Critical_Dates.py")
    
    with col7:
        if st.button("💳 Billing", use_container_width=True):
            st.switch_page("pages/15_💳_Billing.py")
    
    with col8:
        if st.button("🗑️ Delete Leases", use_container_width=True):
            st.switch_page("pages/2_📋_Lease_Review.py")

else:  # Client role
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Upload New Lease", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📤_Upload_Lease.py")
    
    with col2:
        if st.button("👥 My Portal", use_container_width=True):
            st.switch_page("pages/7_👥_Client_Portal.py")
    
    with col3:
        if st.button("📋 My Leases", use_container_width=True):
            st.switch_page("pages/2_📋_Lease_Review.py")

    if st.button("💳 Billing", use_container_width=True):
        st.switch_page("pages/15_💳_Billing.py")

st.markdown("<br><br>", unsafe_allow_html=True)

# Recent Activity
st.markdown("## 📈 Recent Activity")

try:
    from query_cache import cached
    recent_leases_data = cached(
        "home_recent_leases",
        30,
        lambda: (sb.table("leases").select("*").order("created_at", desc=True).limit(5).execute().data or []),
    )
    
    if recent_leases_data:
        for lease in recent_leases_data:
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
