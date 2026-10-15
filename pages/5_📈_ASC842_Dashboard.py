"""
ASC 842 Compliance Dashboard for LeaseAI
Full-featured interface for lease accounting compliance calculations.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="ASC 842 Compliance - LeaseAI",
    page_icon="📈",
    layout="wide",
)

# Load config
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    try:
        from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    except ImportError:
        st.error("No secrets configured. Add them to Streamlit Cloud or config.py.")
        st.stop()

from supabase import create_client
from auth_module import AuthManager
from asc842_engine import ASC842ComplianceEngine

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
auth = AuthManager(sb)
engine = ASC842ComplianceEngine()

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Header
st.title("📈 ASC 842 / IFRS 16 Compliance Engine")
st.markdown("Complete lease accounting compliance calculations and reporting")
st.markdown("---")

# Tab navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 New Calculation",
    "📈 View Calculations",
    "📑 Disclosures",
    "📚 Guidance"
])

with tab1:
    st.subheader("Create New ASC 842 Calculation")
    
    # Select lease
    leases_response = sb.table("leases").select("id, filename, clients(name)").execute()
    leases = leases_response.data or []
    
    if not leases:
        st.warning("No leases found. Upload a lease first.")
    else:
        lease_options = {
            f"{l.get('filename', 'Unknown')} - {(l.get('clients') or {}).get('name', 'Unknown')}": l['id']
            for l in leases
        }
        
        selected_lease_label = st.selectbox("Select Lease", list(lease_options.keys()))
        selected_lease_id = lease_options[selected_lease_label]
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Lease Parameters")
            
            lease_term_months = st.number_input("Lease Term (months)", min_value=1, max_value=1200, value=36)
            monthly_payment = st.number_input("Monthly Payment ($)", min_value=0.0, value=5000.0, step=100.0)
            discount_rate = st.number_input("Incremental Borrowing Rate (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1)
            initial_direct_costs = st.number_input("Initial Direct Costs ($)", min_value=0.0, value=0.0, step=100.0)
            
        with col2:
            st.subheader("Additional Details")
            
            lease_commencement_date = st.date_input("Lease Commencement Date")
            lease_classification = st.selectbox("Lease Classification", ["Operating", "Finance"])
            payment_frequency = st.selectbox("Payment Frequency", ["Monthly", "Quarterly", "Annual"])
            
        st.markdown("---")
        
        if st.button("🧮 Calculate ASC 842 Compliance", type="primary", use_container_width=True):
            with st.spinner("Calculating..."):
                try:
                    # Calculate present value of lease payments
                    monthly_rate = (discount_rate / 100) / 12
                    
                    if monthly_rate == 0:
                        pv = monthly_payment * lease_term_months
                    else:
                        pv = monthly_payment * ((1 - (1 + monthly_rate) ** -lease_term_months) / monthly_rate)
                    
                    rou_asset = pv + initial_direct_costs
                    lease_liability = pv
                    
                    # Save calculation
                    calculation_data = {
                        "lease_id": selected_lease_id,
                        "calculation_date": datetime.now().isoformat(),
                        "lease_term_months": lease_term_months,
                        "monthly_payment": monthly_payment,
                        "discount_rate": discount_rate,
                        "initial_direct_costs": initial_direct_costs,
                        "rou_asset": rou_asset,
                        "lease_liability": lease_liability,
                        "lease_classification": lease_classification,
                        "payment_frequency": payment_frequency,
                        "commencement_date": lease_commencement_date.isoformat()
                    }
                    
                    # Try to save to database (table may not exist yet)
                    try:
                        sb.table("asc842_calculations").insert(calculation_data).execute()
                    except:
                        pass
                    
                    st.success("✅ Calculation Complete!")
                    
                    # Display results
                    st.markdown("### Calculation Results")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Right-of-Use Asset", f"${rou_asset:,.2f}")
                    with col2:
                        st.metric("Lease Liability", f"${lease_liability:,.2f}")
                    with col3:
                        st.metric("Total Lease Payments", f"${monthly_payment * lease_term_months:,.2f}")
                    
                    # Generate amortization schedule
                    st.markdown("### Amortization Schedule (First 12 Months)")
                    
                    schedule = []
                    remaining_liability = lease_liability
                    
                    for month in range(1, min(13, lease_term_months + 1)):
                        interest = remaining_liability * monthly_rate
                        principal = monthly_payment - interest
                        remaining_liability -= principal
                        
                        schedule.append({
                            "Month": month,
                            "Payment": monthly_payment,
                            "Interest": interest,
                            "Principal": principal,
                            "Remaining Liability": remaining_liability
                        })
                    
                    df = pd.DataFrame(schedule)
                    
                    # Format currency columns
                    for col in ["Payment", "Interest", "Principal", "Remaining Liability"]:
                        df[col] = df[col].apply(lambda x: f"${x:,.2f}")
                    
                    st.dataframe(df, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")

with tab2:
    st.subheader("View Past Calculations")
    
    try:
        calculations_response = sb.table("asc842_calculations").select("*, leases(filename)").order("calculation_date", desc=True).execute()
        calculations = calculations_response.data or []
        
        if calculations:
            for calc in calculations:
                with st.expander(f"{(calc.get('leases') or {}).get('filename', 'Unknown')} - {calc.get('calculation_date', '')[:10]}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("ROU Asset", f"${calc.get('rou_asset', 0):,.2f}")
                    with col2:
                        st.metric("Lease Liability", f"${calc.get('lease_liability', 0):,.2f}")
                    with col3:
                        st.write(f"**Classification:** {calc.get('lease_classification', 'N/A')}")
        else:
            st.info("No calculations found. Create one in the 'New Calculation' tab.")
    except:
        st.info("ASC 842 calculations table not yet created. Perform a calculation first.")

with tab3:
    st.subheader("📑 Financial Statement Disclosures")
    st.info("ASC 842 requires specific disclosures in financial statements. This section will generate required disclosure templates.")
    
    st.markdown("""
    ### Required Disclosures:
    - Operating lease cost
    - Finance lease cost (amortization and interest)
    - Short-term lease cost
    - Variable lease cost
    - Weighted average remaining lease term
    - Weighted average discount rate
    - Maturity analysis of lease liabilities
    """)

with tab4:
    st.subheader("📚 ASC 842 Guidance")
    
    st.markdown("""
    ### Key Requirements
    
    **ASC 842** (Leases) requires lessees to recognize most leases on the balance sheet by recording:
    
    1. **Right-of-Use (ROU) Asset** - Represents the lessee's right to use the underlying asset
    2. **Lease Liability** - Present value of future lease payments
    
    ### Lease Classification
    
    **Finance Lease** if any of the following criteria are met:
    - Transfer of ownership at end of lease
    - Purchase option reasonably certain to be exercised
    - Lease term is major part of asset's economic life (≥75%)
    - PV of lease payments equals or exceeds substantially all (≥90%) of asset's fair value
    - Asset is specialized with no alternative use
    
    **Operating Lease** - All other leases
    
    ### Measurement
    
    **Initial Recognition:**
    - Lease Liability = PV of lease payments (discounted at incremental borrowing rate)
    - ROU Asset = Lease Liability + Initial Direct Costs + Prepayments - Lease Incentives
    
    **Subsequent Measurement:**
    - Finance Lease: Amortize ROU asset + Interest on liability
    - Operating Lease: Straight-line lease expense
    
    ### Disclosure Requirements
    
    Annual financial statements must disclose:
    - Lease cost components
    - Cash flows from leases
    - Weighted average lease terms and discount rates
    - Maturity analysis of lease liabilities
    """)
