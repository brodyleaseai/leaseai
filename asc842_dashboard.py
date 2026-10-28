"""
ASC 842 Compliance Dashboard for LeaseAI Admin
Full-featured interface for lease accounting compliance calculations.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
from asc842_engine import ASC842ComplianceEngine
from asc842_params import fields_from_rows, params_from_extracted_fields, source_labels, widget_key


def render_asc842_compliance_page(supabase, auth):
    """
    Render the ASC 842 / IFRS 16 compliance calculation interface.
    
    Args:
        supabase: Supabase client instance
        auth: AuthManager instance
    """
    st.header("📊 ASC 842 / IFRS 16 Compliance Engine")
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
        render_new_calculation_tab(supabase, auth)
    
    with tab2:
        render_view_calculations_tab(supabase)
    
    with tab3:
        render_disclosures_tab(supabase)
    
    with tab4:
        render_guidance_tab()


def render_new_calculation_tab(supabase, auth):
    """Render the new calculation form."""
    st.subheader("Create New ASC 842 Calculation")
    
    # Select lease
    try:
        leases_response = supabase.table("leases").select("id, property_address, tenant_name, status").eq("status", "APPROVED").execute()
        leases = leases_response.data
        
        if not leases:
            st.warning("No approved leases available. Please approve a lease first.")
            return
        
        lease_options = {f"#{l['id']} - {l['property_address']} ({l['tenant_name']})": l['id'] for l in leases}
        selected_lease_label = st.selectbox("Select Lease", list(lease_options.keys()), key="asc842_admin_selected_lease")
        selected_lease_id = lease_options[selected_lease_label]
        
        try:
            fields_response = supabase.table("extracted_fields").select("*").eq("lease_id", selected_lease_id).execute()
            field_rows = fields_response.data or []
        except Exception:
            field_rows = []
        
        params = params_from_extracted_fields(fields_from_rows(field_rows))
        loaded_terms = source_labels(params)
        if loaded_terms:
            st.info("Loaded from this lease: " + ", ".join(loaded_terms) + ". You can still edit any value before calculating.")
        elif field_rows:
            st.warning("This lease has extracted fields, but commencement, expiration, or rent could not be parsed. Enter those terms below.")
        else:
            st.warning("No extracted terms found for this lease. Review the lease first, or enter the terms below.")
        
        st.markdown("---")
        
        with st.form(widget_key(selected_lease_id, "calculation_form")):
            st.subheader("Lease Terms")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                commencement_date = st.date_input(
                    "Lease Commencement Date",
                    params["commencement_date"],
                    key=widget_key(selected_lease_id, "admin_commencement"),
                )
                end_date = st.date_input(
                    "Lease End Date",
                    params["end_date"],
                    key=widget_key(selected_lease_id, "admin_end"),
                )
                monthly_payment = st.number_input(
                    "Monthly Base Rent ($)",
                    min_value=0.0,
                    value=float(params["monthly_payment"]),
                    step=100.0,
                    key=widget_key(selected_lease_id, "admin_monthly"),
                )
            
            with col2:
                discount_rate = st.number_input(
                    "Discount Rate (Annual %)",
                    min_value=0.0,
                    max_value=20.0,
                    value=6.0,
                    step=0.1,
                    key=widget_key(selected_lease_id, "admin_ibr"),
                ) / 100
                annual_increase = st.number_input(
                    "Annual Rent Increase (%)",
                    min_value=0.0,
                    max_value=10.0,
                    value=float(params["annual_increase"]),
                    step=0.5,
                    key=widget_key(selected_lease_id, "admin_increase"),
                ) / 100
                initial_direct_costs = st.number_input(
                    "Initial Direct Costs ($)",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=widget_key(selected_lease_id, "admin_idc"),
                )
            
            with col3:
                lease_incentives = st.number_input(
                    "Lease Incentives Received ($)",
                    min_value=0.0,
                    value=float(params["lease_incentives"]),
                    step=100.0,
                    key=widget_key(selected_lease_id, "admin_incentives"),
                )
                prepayments = st.number_input(
                    "Prepayments ($)",
                    min_value=0.0,
                    value=float(params.get("prepayments", 0.0)),
                    step=100.0,
                    key=widget_key(selected_lease_id, "admin_prepayments"),
                )
                residual_guarantee = st.number_input(
                    "Residual Value Guarantee ($)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    key=widget_key(selected_lease_id, "admin_residual"),
                )
            
            st.markdown("---")
            st.subheader("Lease Options & Complex Terms")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Renewal Option**")
                has_renewal = st.checkbox(
                    "Has Renewal Option",
                    value=params["has_renewal"],
                    key=widget_key(selected_lease_id, "admin_has_renewal"),
                )
                if has_renewal:
                    renewal_months = st.number_input(
                        "Renewal Term (months)",
                        min_value=1,
                        value=int(params["renewal_months"] or 12),
                        step=1,
                        key=widget_key(selected_lease_id, "admin_renewal_months"),
                    )
                    renewal_certain = st.checkbox(
                        "Reasonably Certain to Exercise",
                        key=widget_key(selected_lease_id, "admin_renewal_certain"),
                    )
                else:
                    renewal_months = 0
                    renewal_certain = False
            
            with col2:
                st.markdown("**Purchase Option**")
                has_purchase = st.checkbox("Has Purchase Option", key=widget_key(selected_lease_id, "admin_has_purchase"))
                if has_purchase:
                    purchase_price = st.number_input(
                        "Purchase Option Price ($)",
                        min_value=0.0,
                        value=0.0,
                        step=1000.0,
                        key=widget_key(selected_lease_id, "admin_purchase_price"),
                    )
                    purchase_certain = st.checkbox(
                        "Reasonably Certain to Purchase",
                        key=widget_key(selected_lease_id, "admin_purchase_certain"),
                    )
                else:
                    purchase_price = 0
                    purchase_certain = False
            
            with col3:
                st.markdown("**Variable Payments**")
                has_variable = st.checkbox(
                    "Has Variable Payments",
                    value=params["has_variable"],
                    key=widget_key(selected_lease_id, "admin_has_variable"),
                )
                if has_variable:
                    variable_rate = st.number_input(
                        "Variable Rate / Index (%)",
                        min_value=0.0,
                        max_value=10.0,
                        value=0.0,
                        step=0.1,
                        key=widget_key(selected_lease_id, "admin_variable_rate"),
                    ) / 100
                else:
                    variable_rate = 0
            
            st.markdown("---")
            
            assumptions_notes = st.text_area(
                "Assumptions & Notes",
                placeholder="Document key assumptions, management judgments, and rationale for discount rate, lease term, and option assessments...",
                height=100
            )
            
            calculate_button = st.form_submit_button("🧮 Calculate ASC 842 Compliance", use_container_width=True)
        
        # Process calculation OUTSIDE the form
        if calculate_button:
            with st.spinner("Running ASC 842 compliance calculations..."):
                # Prepare lease data for engine
                lease_data = {
                    'commencement_date': commencement_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'monthly_payment': monthly_payment,
                    'discount_rate': discount_rate,
                    'annual_rent_increases': annual_increase,
                    'initial_direct_costs': initial_direct_costs,
                    'lease_incentives': lease_incentives,
                    'prepayments': prepayments,
                    'residual_value_guarantee': residual_guarantee,
                    'has_renewal_option': has_renewal,
                    'renewal_term_months': renewal_months,
                    'renewal_reasonably_certain': renewal_certain,
                    'has_purchase_option': has_purchase,
                    'purchase_option_price': purchase_price,
                    'purchase_reasonably_certain': purchase_certain,
                    'has_variable_payments': has_variable,
                    'variable_payment_index_rate': variable_rate
                }
                
                # Run calculation
                try:
                    engine = ASC842ComplianceEngine(lease_data)
                    results = engine.run_full_calculation()
                    
                    # Display results (outside form)
                    display_calculation_results(results)
                    
                    # Save to database
                    save_calculation_to_db(
                        supabase,
                        auth,
                        selected_lease_id,
                        lease_data,
                        results,
                        assumptions_notes
                    )
                    
                    st.success("✅ ASC 842 calculation completed and saved!")
                    st.balloons()
                
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    except Exception as e:
        st.error(f"Error loading leases: {str(e)}")


def display_calculation_results(results):
    """Display comprehensive calculation results."""
    st.markdown("---")
    st.subheader("📊 Calculation Results")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Lease Classification", results['classification'])
    
    with col2:
        st.metric("Initial Lease Liability", f"${results['initial_liability']:,.2f}")
    
    with col3:
        st.metric("Initial ROU Asset", f"${results['initial_rou_asset']:,.2f}")
    
    with col4:
        st.metric("Lease Term", f"{results['lease_term_months']} months")
    
    # Classification reasons
    if results['classification_reasons']:
        st.info("**Classification Rationale:** " + ", ".join(results['classification_reasons']))
    
    # Warnings
    if results['warnings']:
        with st.expander("⚠️ Warnings & Assumptions"):
            for warning in results['warnings']:
                st.warning(warning)
    
    st.markdown("---")
    
    # Schedules
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📉 Lease Liability Amortization")
        liability_df = pd.DataFrame(results['liability_schedule'])
        
        # Display summary table (first 12 months)
        st.dataframe(
            liability_df.head(12)[['period', 'date', 'opening_balance', 'interest_expense', 'payment', 'closing_balance']],
            hide_index=True,
            use_container_width=True
        )
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=liability_df['period'],
            y=liability_df['closing_balance'],
            mode='lines',
            name='Lease Liability',
            line=dict(color='#1976D2', width=3)
        ))
        fig.update_layout(
            title="Lease Liability Over Time",
            xaxis_title="Period (Months)",
            yaxis_title="Balance ($)",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📉 ROU Asset Depreciation")
        rou_df = pd.DataFrame(results['rou_asset_schedule'])
        
        # Display summary table (first 12 months)
        st.dataframe(
            rou_df.head(12)[['period', 'date', 'opening_balance', 'depreciation_expense', 'net_book_value']],
            hide_index=True,
            use_container_width=True
        )
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=rou_df['period'],
            y=rou_df['net_book_value'],
            mode='lines',
            name='ROU Asset Net Book Value',
            line=dict(color='#00C853', width=3)
        ))
        fig.update_layout(
            title="ROU Asset Net Book Value Over Time",
            xaxis_title="Period (Months)",
            yaxis_title="Net Book Value ($)",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Download schedules
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        liability_csv = liability_df.to_csv(index=False)
        st.download_button(
            "📥 Download Liability Schedule",
            liability_csv,
            "lease_liability_schedule.csv",
            "text/csv"
        )
    
    with col2:
        rou_csv = rou_df.to_csv(index=False)
        st.download_button(
            "📥 Download ROU Asset Schedule",
            rou_csv,
            "rou_asset_schedule.csv",
            "text/csv"
        )
    
    with col3:
        full_json = json.dumps(results, indent=2, default=str)
        st.download_button(
            "📥 Download Full Report (JSON)",
            full_json,
            "asc842_full_report.json",
            "application/json"
        )
    
    # Journal entries
    with st.expander("📖 View Journal Entries"):
        st.subheader("Initial Recognition Entry")
        initial_entry = results['initial_journal_entry']
        st.json(initial_entry)
        
        st.markdown("---")
        st.subheader("Monthly Recurring Entries (Sample - First 2 Months)")
        for entry in results['monthly_journal_entries'][:6]:
            st.json(entry)
            st.markdown("---")


def save_calculation_to_db(supabase, auth, lease_id, lease_data, results, assumptions):
    """Save ASC 842 calculation to database."""
    try:
        calc_data = {
            'lease_id': lease_id,
            'lease_commencement_date': lease_data['commencement_date'],
            'lease_end_date': lease_data['end_date'],
            'lease_term_months': results['lease_term_months'],
            'monthly_base_rent': lease_data['monthly_payment'],
            'annual_rent_increases': lease_data['annual_rent_increases'],
            'discount_rate': lease_data['discount_rate'],
            'initial_lease_liability': results['initial_liability'],
            'initial_rou_asset': results['initial_rou_asset'],
            'initial_direct_costs': lease_data['initial_direct_costs'],
            'lease_incentives': lease_data['lease_incentives'],
            'prepayments': lease_data['prepayments'],
            'lease_classification': results['classification'],
            'has_renewal_option': lease_data['has_renewal_option'],
            'renewal_term_months': lease_data.get('renewal_term_months', 0),
            'renewal_reasonably_certain': lease_data.get('renewal_reasonably_certain', False),
            'has_purchase_option': lease_data['has_purchase_option'],
            'purchase_option_price': lease_data.get('purchase_option_price', 0),
            'purchase_reasonably_certain': lease_data.get('purchase_reasonably_certain', False),
            'has_variable_payments': lease_data['has_variable_payments'],
            'variable_payment_index_rate': lease_data.get('variable_payment_index_rate', 0),
            'residual_value_guarantee': lease_data['residual_value_guarantee'],
            'liability_schedule': json.dumps(results['liability_schedule'], default=str),
            'rou_asset_schedule': json.dumps(results['rou_asset_schedule'], default=str),
            'assumptions': assumptions,
            'calculated_by_email': auth.get_user_name()  # Store email instead of user_id
        }
        
        supabase.table("asc842_calculations").insert(calc_data).execute()
        
    except Exception as e:
        st.error(f"Error saving calculation: {str(e)}")


def render_view_calculations_tab(supabase):
    """Render saved calculations list."""
    st.subheader("Saved ASC 842 Calculations")
    
    try:
        response = supabase.table("asc842_calculations").select(
            "*, leases(property_address, tenant_name)"
        ).order("calculated_at", desc=True).execute()
        
        calcs = response.data
        
        if not calcs:
            st.info("No calculations saved yet. Create one in the 'New Calculation' tab.")
            return
        
        for calc in calcs:
            with st.expander(f"📊 {calc['leases']['property_address']} - {calc['lease_classification']} Lease"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Initial Liability", f"${calc['initial_lease_liability']:,.2f}")
                
                with col2:
                    st.metric("Initial ROU Asset", f"${calc['initial_rou_asset']:,.2f}")
                
                with col3:
                    st.metric("Lease Term", f"{calc['lease_term_months']} months")
                
                with col4:
                    st.metric("Discount Rate", f"{calc['discount_rate'] * 100:.2f}%")
                
                st.markdown("---")
                
                if calc['assumptions']:
                    st.write("**Assumptions:**")
                    st.text(calc['assumptions'])
                
                # View schedules
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("View Liability Schedule", key=f"liab_{calc['id']}"):
                        liability_data = json.loads(calc['liability_schedule'])
                        st.dataframe(pd.DataFrame(liability_data))
                
                with col2:
                    if st.button("View ROU Asset Schedule", key=f"rou_{calc['id']}"):
                        rou_data = json.loads(calc['rou_asset_schedule'])
                        st.dataframe(pd.DataFrame(rou_data))
    
    except Exception as e:
        st.error(f"Error loading calculations: {str(e)}")


def render_disclosures_tab(supabase):
    """Render financial statement disclosures."""
    st.subheader("Financial Statement Disclosures")
    st.markdown("Generate ASC 842 / IFRS 16 disclosure notes for financial statements")
    
    st.info("🚧 Disclosure generation coming soon! This will include:\n\n" +
            "- Maturity analysis of lease liabilities\n" +
            "- Weighted average discount rates and remaining terms\n" +
            "- Lease expense breakdown\n" +
            "- Supplemental balance sheet information\n" +
            "- Narrative disclosures for significant judgments")


def render_guidance_tab():
    """Render ASC 842 guidance and help."""
    st.subheader("📚 ASC 842 / IFRS 16 Guidance")
    
    st.markdown("""
    ## Key Concepts
    
    ### Lease Classification (ASC 842)
    
    A lease is classified as a **Finance Lease** if ANY of these criteria are met:
    
    1. **Transfer of ownership** at the end of the lease term
    2. **Purchase option** that is reasonably certain to be exercised
    3. **Lease term** is a major part (≥75%) of the asset's economic life
    4. **Present value** of lease payments ≥ substantially all (≥90%) of the fair market value
    5. **Specialized asset** with no alternative use to the lessor
    
    Otherwise, the lease is classified as an **Operating Lease**.
    
    ### Initial Measurement
    
    **Lease Liability** = Present value of:
    - Fixed lease payments
    - Variable payments based on an index or rate (using initial rate)
    - Residual value guarantees
    - Purchase option price (if reasonably certain)
    - Termination penalties (if reasonably certain)
    
    **ROU Asset** = Lease Liability + Initial Direct Costs + Prepayments - Lease Incentives
    
    ### Subsequent Measurement
    
    **Lease Liability:**
    - Increase by interest expense (effective interest method)
    - Decrease by lease payments
    - Remeasure when changes occur
    
    **ROU Asset:**
    - Depreciate on straight-line basis over shorter of lease term or useful life
    - Test for impairment under ASC 360
    
    ### Discount Rate
    
    Use the **rate implicit in the lease** if readily determinable.
    
    Otherwise, use the lessee's **incremental borrowing rate (IBR)**:
    - Risk-free rate + credit spread
    - Adjusted for lease term, currency, collateral
    
    ### Key Judgments
    
    Document management's judgments for:
    - Lease term (including renewal/termination options)
    - Purchase option assessment
    - Discount rate determination
    - Variable payment estimates
    - Non-lease component allocation
    
    ## Common Scenarios
    
    ### Rent Escalations
    - Fixed escalations (e.g., 3% annually): Include in PV calculation
    - CPI-based escalations: Only initial rate included; remeasure when rate changes
    
    ### Tenant Improvements
    - Paid by landlord (tenant allowance): Reduces ROU Asset
    - Paid by tenant: Capitalize separately, not part of ROU Asset
    
    ### CAM Charges
    - If separated in contract: Account as non-lease component
    - If not separated: Practical expedient to combine with lease component
    
    ## Resources
    
    - FASB ASC 842: Leases (full standard)
    - IFRS 16: Leases (international standard)
    - FASB Implementation Q&A
    - Big 4 Technical Guidance
    """)
    
    st.markdown("---")
    
    st.subheader("💡 LeaseAI Best Practices")
    
    st.markdown("""
    1. **Document assumptions thoroughly** - especially discount rate and lease term judgments
    2. **Update calculations quarterly** - for any lease modifications or market changes
    3. **Maintain audit trail** - keep all versions of calculations
    4. **Review classification annually** - conditions may change
    5. **Coordinate with auditors** - align on methodology before year-end
    """)
