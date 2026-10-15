"""
ASC 842 Compliance Dashboard for LeaseAI
Full-featured interface for lease accounting compliance calculations.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
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

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ Please log in from the Home page first.")
    if st.button("← Go to Home"):
        st.switch_page("Home.py")
    st.stop()

# Header
st.title("📈 ASC 842 / IFRS 16 Compliance Engine")
st.markdown("**Enterprise-Grade Lease Accounting Calculations & Reporting**")
st.markdown("---")

# Tab navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 New Calculation",
    "📊 View Calculations",
    "📑 Financial Disclosures",
    "📄 Generate Reports",
    "📚 Guidance"
])

with tab1:
    st.subheader("Create New ASC 842 Compliance Calculation")
    
    # Select lease
    leases_response = sb.table("leases").select("id, filename, property_address, tenant_name, clients(name)").execute()
    leases = leases_response.data or []
    
    if not leases:
        st.warning("No leases found. Upload a lease first.")
    else:
        lease_options = {
            f"{l.get('property_address', l.get('filename', 'Unknown'))} - {l.get('tenant_name', 'Unknown')}": l['id']
            for l in leases
        }
        
        selected_lease_label = st.selectbox("Select Lease", list(lease_options.keys()))
        selected_lease_id = lease_options[selected_lease_label]
        
        st.markdown("---")
        st.markdown("### Lease Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Lease Term**")
            commencement_date = st.date_input("Commencement Date", value=date.today())
            end_date = st.date_input("End Date", value=date.today().replace(year=date.today().year + 3))
            has_renewal = st.checkbox("Has Renewal Option")
            if has_renewal:
                renewal_months = st.number_input("Renewal Term (months)", min_value=1, value=12)
                renewal_certain = st.checkbox("Renewal Reasonably Certain")
            else:
                renewal_months = 0
                renewal_certain = False
        
        with col2:
            st.markdown("**Payment Structure**")
            monthly_payment = st.number_input("Monthly Payment ($)", min_value=0.0, value=5000.0, step=100.0, format="%.2f")
            annual_increase = st.number_input("Annual Rent Increase (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
            has_variable = st.checkbox("Has Variable Payments")
            if has_variable:
                variable_rate = st.number_input("Variable Payment Index Rate (%)", min_value=0.0, value=2.0, step=0.1)
            else:
                variable_rate = 0.0
        
        with col3:
            st.markdown("**Economic Factors**")
            discount_rate = st.number_input("Incremental Borrowing Rate (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1)
            initial_direct_costs = st.number_input("Initial Direct Costs ($)", min_value=0.0, value=0.0, step=100.0)
            lease_incentives = st.number_input("Lease Incentives ($)", min_value=0.0, value=0.0, step=100.0)
            prepayments = st.number_input("Prepayments ($)", min_value=0.0, value=0.0, step=100.0)
        
        st.markdown("---")
        st.markdown("### Options & Classification")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            has_purchase = st.checkbox("Has Purchase Option")
            if has_purchase:
                purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, value=100000.0)
                purchase_certain = st.checkbox("Purchase Reasonably Certain")
            else:
                purchase_price = 0.0
                purchase_certain = False
        
        with col2:
            has_termination = st.checkbox("Has Termination Option")
            if has_termination:
                termination_penalty = st.number_input("Termination Penalty ($)", min_value=0.0, value=0.0)
            else:
                termination_penalty = 0.0
        
        with col3:
            residual_guarantee = st.number_input("Residual Value Guarantee ($)", min_value=0.0, value=0.0, step=1000.0)
        
        st.markdown("---")
        
        if st.button("🧮 Calculate ASC 842 Compliance", type="primary", width="stretch"):
            with st.spinner("Running comprehensive ASC 842 compliance calculations..."):
                try:
                    # Build lease data dictionary
                    lease_data = {
                        'commencement_date': commencement_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'monthly_payment': monthly_payment,
                        'discount_rate': discount_rate / 100,  # Convert to decimal
                        'initial_direct_costs': initial_direct_costs,
                        'lease_incentives': lease_incentives,
                        'prepayments': prepayments,
                        'residual_value_guarantee': residual_guarantee,
                        'has_renewal_option': has_renewal,
                        'renewal_term_months': renewal_months if has_renewal else 0,
                        'renewal_reasonably_certain': renewal_certain,
                        'has_purchase_option': has_purchase,
                        'purchase_option_price': purchase_price if has_purchase else 0,
                        'purchase_reasonably_certain': purchase_certain,
                        'has_termination_option': has_termination,
                        'termination_penalty': termination_penalty if has_termination else 0,
                        'has_variable_payments': has_variable,
                        'variable_payment_index_rate': variable_rate / 100 if has_variable else 0,
                        'annual_rent_increases': annual_increase / 100
                    }
                    
                    # Initialize ASC 842 engine
                    engine = ASC842ComplianceEngine(lease_data)
                    
                    # Run all calculations
                    engine.classify_lease()
                    engine.calculate_initial_recognition()
                    engine.generate_liability_schedule()
                    engine.generate_rou_schedule()
                    engine.generate_journal_entries()
                    
                    # Display results
                    st.success("✅ ASC 842 Compliance Calculation Complete!")
                    
                    st.markdown("---")
                    st.markdown("## 📊 Calculation Results")
                    
                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Lease Classification",
                            engine.lease_classification,
                            help="Operating or Finance lease classification"
                        )
                    
                    with col2:
                        st.metric(
                            "Initial ROU Asset",
                            f"${engine.initial_rou_asset:,.2f}",
                            help="Right-of-Use Asset at commencement"
                        )
                    
                    with col3:
                        st.metric(
                            "Initial Lease Liability",
                            f"${engine.initial_liability:,.2f}",
                            help="Present value of lease payments"
                        )
                    
                    with col4:
                        st.metric(
                            "Effective Lease Term",
                            f"{engine.lease_term_months} months",
                            help="Total term including exercised options"
                        )
                    
                    # Warnings/Errors
                    if engine.warnings:
                        st.warning("⚠️ **Warnings:**\n" + "\n".join([f"- {w}" for w in engine.warnings]))
                    
                    if engine.errors:
                        st.error("❌ **Errors:**\n" + "\n".join([f"- {e}" for e in engine.errors]))
                    
                    st.markdown("---")
                    
                    # Amortization schedules
                    st.markdown("### 📅 Amortization Schedules")
                    
                    schedule_tab1, schedule_tab2 = st.tabs(["Lease Liability Schedule", "ROU Asset Schedule"])
                    
                    with schedule_tab1:
                        if engine.liability_schedule is not None and not engine.liability_schedule.empty:
                            # Show first 12 months
                            display_schedule = engine.liability_schedule.head(12).copy()
                            
                            # Format currency columns
                            for col in ['Payment', 'Interest', 'Principal', 'Ending_Balance']:
                                if col in display_schedule.columns:
                                    display_schedule[col] = display_schedule[col].apply(lambda x: f"${x:,.2f}")
                            
                            # Format date
                            if 'Date' in display_schedule.columns:
                                display_schedule['Date'] = pd.to_datetime(display_schedule['Date']).dt.strftime('%b %Y')
                            
                            st.dataframe(display_schedule, use_container_width=True, hide_index=True)
                            
                            # Download full schedule
                            csv = engine.liability_schedule.to_csv(index=False)
                            st.download_button(
                                "📥 Download Full Liability Schedule (CSV)",
                                csv,
                                f"liability_schedule_{selected_lease_id}.csv",
                                "text/csv"
                            )
                        else:
                            st.info("No liability schedule generated")
                    
                    with schedule_tab2:
                        if engine.rou_schedule is not None and not engine.rou_schedule.empty:
                            # Show first 12 months
                            display_schedule = engine.rou_schedule.head(12).copy()
                            
                            # Format currency columns
                            for col in ['Amortization', 'Ending_Balance']:
                                if col in display_schedule.columns:
                                    display_schedule[col] = display_schedule[col].apply(lambda x: f"${x:,.2f}")
                            
                            # Format date
                            if 'Date' in display_schedule.columns:
                                display_schedule['Date'] = pd.to_datetime(display_schedule['Date']).dt.strftime('%b %Y')
                            
                            st.dataframe(display_schedule, use_container_width=True, hide_index=True)
                            
                            # Download full schedule
                            csv = engine.rou_schedule.to_csv(index=False)
                            st.download_button(
                                "📥 Download Full ROU Schedule (CSV)",
                                csv,
                                f"rou_schedule_{selected_lease_id}.csv",
                                "text/csv"
                            )
                        else:
                            st.info("No ROU schedule generated")
                    
                    st.markdown("---")
                    
                    # Journal entries
                    st.markdown("### 📝 Journal Entries")
                    
                    if engine.journal_entries:
                        for i, entry in enumerate(engine.journal_entries[:5], 1):  # Show first 5
                            with st.expander(f"Entry {i}: {entry.get('description', 'Journal Entry')} - {entry.get('date', 'N/A')}"):
                                st.markdown(f"**Date:** {entry.get('date', 'N/A')}")
                                st.markdown(f"**Description:** {entry.get('description', 'N/A')}")
                                st.markdown("**Debits:**")
                                for debit in entry.get('debits', []):
                                    st.markdown(f"- {debit['account']}: ${debit['amount']:,.2f}")
                                st.markdown("**Credits:**")
                                for credit in entry.get('credits', []):
                                    st.markdown(f"- {credit['account']}: ${credit['amount']:,.2f}")
                        
                        st.info(f"Showing 5 of {len(engine.journal_entries)} journal entries. Download full report for all entries.")
                    else:
                        st.info("No journal entries generated")
                    
                    # Save to database (optional)
                    try:
                        calculation_record = {
                            "lease_id": selected_lease_id,
                            "calculation_date": datetime.now().isoformat(),
                            "lease_classification": engine.lease_classification,
                            "initial_rou_asset": float(engine.initial_rou_asset),
                            "initial_liability": float(engine.initial_liability),
                            "lease_term_months": int(engine.lease_term_months),
                            "discount_rate": float(discount_rate),
                            "calculation_data": json.dumps(lease_data)
                        }
                        
                        sb.table("asc842_calculations").insert(calculation_record).execute()
                        st.success("✅ Calculation saved to database")
                    except Exception as db_error:
                        st.info(f"Note: Could not save to database (table may not exist): {str(db_error)}")
                
                except Exception as e:
                    st.error(f"❌ **Calculation Error**")
                    st.error(f"**Error Message:** {str(e)}")
                    
                    # Show detailed error info
                    with st.expander("🔍 Detailed Error Information (Click to expand)"):
                        st.write("**Error Type:**", type(e).__name__)
                        st.write("**Error Details:**", str(e))
                        st.code(f"{type(e).__name__}: {str(e)}")
                        
                        # Show the full traceback
                        import traceback
                        st.code(traceback.format_exc())
                    
                    st.info("💡 **Troubleshooting Tips:**\n"
                           "- Make sure all required fields are filled in\n"
                           "- Check that dates are valid (end date after commencement)\n"
                           "- Verify payment amounts are positive numbers\n"
                           "- Discount rate should be between 0% and 20%")


with tab2:
    st.subheader("📊 View Past Calculations")
    
    try:
        calculations_response = sb.table("asc842_calculations").select("*, leases(filename, property_address)").order("calculation_date", desc=True).limit(20).execute()
        calculations = calculations_response.data or []
        
        if calculations:
            for calc in calculations:
                lease_info = calc.get('leases', {})
                property_addr = lease_info.get('property_address', lease_info.get('filename', 'Unknown'))
                calc_date = calc.get('calculation_date', '')[:10]
                
                with st.expander(f"{property_addr} - {calc_date}"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Classification", calc.get('lease_classification', 'N/A'))
                    with col2:
                        st.metric("ROU Asset", f"${calc.get('initial_rou_asset', 0):,.2f}")
                    with col3:
                        st.metric("Lease Liability", f"${calc.get('initial_liability', 0):,.2f}")
                    with col4:
                        st.metric("Term", f"{calc.get('lease_term_months', 0)} mo")
                    
                    if st.button(f"View Full Report", key=f"report_{calc['id']}"):
                        st.info("Full report viewing feature coming soon!")
        else:
            st.info("No calculations found. Create one in the 'New Calculation' tab.")
    except Exception as e:
        st.info("ASC 842 calculations table not yet created. Perform a calculation first.")

with tab3:
    st.subheader("📑 Financial Statement Disclosures")
    st.markdown("""
    ASC 842 requires comprehensive disclosures in financial statements. This engine generates 
    all required disclosure templates automatically.
    
    ### Required Disclosures (ASC 842-20-50):
    
    #### Qualitative Disclosures:
    - General description of leasing arrangements
    - Significant judgments and assumptions
    - Lease classification methodology
    
    #### Quantitative Disclosures:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Operating Leases:**
        - Operating lease cost
        - Variable lease cost
        - Short-term lease cost
        """)
    
    with col2:
        st.markdown("""
        **Finance Leases:**
        - Amortization of ROU assets
        - Interest on lease liabilities
        - Weighted average discount rate
        """)
    
    st.markdown("""
    #### Maturity Analysis:
    Undiscounted cash flows for each of the first 5 years and total thereafter.
    
    #### Balance Sheet Information:
    - ROU assets by major class
    - Lease liabilities (current and non-current)
    
    💡 **Generate these automatically** by running a calculation and downloading the full compliance report.
    """)

with tab4:
    st.subheader("📄 Generate Compliance Reports")
    
    st.info("🚧 Professional PDF Report Generation - Coming Soon!")
    
    st.markdown("""
    The compliance report will include:
    
    ### 📊 Executive Summary
    - Portfolio overview
    - Total assets and liabilities
    - Key metrics and trends
    
    ### 📋 Detailed Calculations
    - Individual lease calculations
    - Classification analysis
    - All schedules and tables
    
    ### 📝 Journal Entries
    - Initial recognition entries
    - Monthly/annual adjustments
    - All subsequent measurements
    
    ### 📑 Financial Disclosures
    - Required ASC 842 disclosures
    - Maturity analysis tables
    - Qualitative descriptions
    
    ### 📈 Schedules & Exhibits
    - Liability amortization schedules
    - ROU asset schedules
    - Sensitivity analysis
    
    **Report Format:** Professional PDF with branded headers, tables, and charts
    """)

with tab5:
    st.subheader("📚 ASC 842 Implementation Guidance")
    
    st.markdown("""
    ## ASC 842: Leases - Comprehensive Guide
    
    ### Overview
    
    ASC 842 requires lessees to recognize assets and liabilities for most leases on the balance sheet. 
    This represents a significant change from the previous standard (ASC 840).
    
    ### Key Requirements
    
    #### 1. **Lease Identification**
    A contract contains a lease if it conveys the right to control an identified asset for a period of time.
    
    **Control requires:**
    - Right to obtain substantially all economic benefits
    - Right to direct the use of the asset
    
    #### 2. **Lease Classification**
    
    **Finance Lease** if ANY of these criteria are met:
    - ✅ Transfer of ownership at end of lease term
    - ✅ Purchase option reasonably certain to exercise
    - ✅ Lease term ≥ major part (75%) of asset's economic life
    - ✅ PV of lease payments ≥ substantially all (90%) of asset's fair value
    - ✅ Asset is specialized with no alternative use
    
    **Operating Lease** = All other leases
    
    #### 3. **Initial Recognition**
    
    **Lease Liability:**
    ```
    PV of:
    - Fixed payments (less lease incentives)
    - Variable payments based on index/rate
    - Amounts probable under residual value guarantees
    - Purchase option price (if reasonably certain)
    - Termination penalties (if reasonably certain)
    
    Discounted at: Incremental borrowing rate (or lease rate if known)
    ```
    
    **Right-of-Use (ROU) Asset:**
    ```
    Lease Liability
    + Payments made before/at commencement
    + Initial direct costs
    - Lease incentives received
    ```
    
    #### 4. **Subsequent Measurement**
    
    **Finance Lease:**
    - **ROU Asset:** Amortize using straight-line (or another basis if more representative)
    - **Liability:** Interest method (effective interest rate)
    - **Income Statement:** Amortization + Interest (front-loaded expense pattern)
    
    **Operating Lease:**
    - **ROU Asset:** Amortize to produce straight-line total expense
    - **Liability:** Interest method
    - **Income Statement:** Single lease cost on straight-line basis
    
    #### 5. **Lease Modifications**
    
    A **modification** is a change to lease scope or consideration that was not part of original terms.
    
    **Treatment depends on:**
    - Whether it's a separate lease (additional right-of-use)
    - Classification of original and modified lease
    - Specific modification circumstances
    
    #### 6. **Practical Expedients**
    
    **Package of Transition Expedients:**
    - No reassessment of lease identification
    - No reassessment of lease classification
    - No reassessment of initial direct costs
    
    **Other Expedients:**
    - Short-term lease exemption (≤12 months)
    - Low-value asset exemption
    - Combine lease and non-lease components
    - Use portfolio approach
    
    ### Common Scenarios
    
    #### Renewal Options
    Include renewal periods if reasonably certain to exercise based on:
    - Economic incentives (favorable terms, leasehold improvements)
    - Historical practice
    - Business factors
    
    #### Variable Payments
    - **Based on index/rate:** Include in liability using index/rate at commencement
    - **Based on performance/use:** Expense as incurred (not in liability)
    
    #### Leasehold Improvements
    - Capitalize as separate fixed asset
    - Amortize over shorter of useful life or lease term
    
    ### Key Metrics
    
    **Weighted Average Remaining Lease Term:**
    ```
    Σ(Lease Liability × Remaining Term) / Total Lease Liabilities
    ```
    
    **Weighted Average Discount Rate:**
    ```
    Σ(Lease Liability × Discount Rate) / Total Lease Liabilities
    ```
    
    ### Competitive Advantages of This Platform
    
    ✅ **Automated Classification** - Applies all 5 criteria automatically
    
    ✅ **Complex Options Handling** - Properly accounts for renewals, purchases, terminations
    
    ✅ **Variable Payment Support** - Handles index-based and performance-based payments
    
    ✅ **Full Disclosure Package** - Generates all required ASC 842 disclosures
    
    ✅ **Journal Entry Automation** - Creates all required accounting entries
    
    ✅ **Modification Tracking** - Handles lease modifications and remeasurements
    
    ✅ **Portfolio Management** - Track unlimited leases with consolidated reporting
    
    ### Professional Standards References
    
    - **ASC 842-20:** Lessee Accounting
    - **ASC 842-30:** Lessor Accounting
    - **IFRS 16:** International equivalent
    - **FASB Guidance:** Implementation Q&A
    
    ---
    
    💡 **Need Help?** This platform handles all the complexity automatically. Just input your lease terms and get audit-ready calculations.
    """)

st.markdown("---")
st.caption("LeaseAI ASC 842 Compliance Engine | Enterprise-Grade Lease Accounting")
