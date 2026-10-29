"""
ASC 842 / IFRS 16 Lease Accounting Compliance Engine
Comprehensive lease accounting calculations and reporting.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Tuple, Optional
import json


class ASC842ComplianceEngine:
    """
    Full-featured ASC 842 / IFRS 16 lease accounting compliance calculator.
    
    Handles:
    - Initial recognition (Day 1 calculations)
    - Subsequent measurement (amortization schedules)
    - Complex lease terms (options, variable payments)
    - Lease modifications and remeasurements
    - Classification (Operating vs Finance)
    - Journal entry generation
    - Disclosure requirements
    """
    
    def __init__(self, lease_data: Dict):
        """
        Initialize compliance engine with lease data.
        
        Args:
            lease_data: Dictionary containing all lease parameters
        """
        self.lease_data = lease_data
        self.errors = []
        self.warnings = []
        
        # Parse required fields
        self.commencement_date = self._parse_date(lease_data.get('commencement_date'))
        self.end_date = self._parse_date(lease_data.get('end_date'))
        self.monthly_payment = float(lease_data.get('monthly_payment', 0))
        self.discount_rate = float(lease_data.get('discount_rate', 0.05))
        
        # Optional fields
        self.initial_direct_costs = float(lease_data.get('initial_direct_costs', 0))
        self.lease_incentives = float(lease_data.get('lease_incentives', 0))
        self.prepayments = float(lease_data.get('prepayments', 0))
        self.residual_value_guarantee = float(lease_data.get('residual_value_guarantee', 0))
        
        # Renewal options
        self.has_renewal = lease_data.get('has_renewal_option', False)
        self.renewal_months = int(lease_data.get('renewal_term_months', 0))
        self.renewal_certain = lease_data.get('renewal_reasonably_certain', False)
        
        # Purchase options
        self.has_purchase = lease_data.get('has_purchase_option', False)
        self.purchase_price = float(lease_data.get('purchase_option_price', 0))
        self.purchase_certain = lease_data.get('purchase_reasonably_certain', False)
        
        # Termination options
        self.has_termination = lease_data.get('has_termination_option', False)
        self.termination_penalty = float(lease_data.get('termination_penalty', 0))
        
        # Variable payments
        self.has_variable = lease_data.get('has_variable_payments', False)
        self.variable_rate = float(lease_data.get('variable_payment_index_rate', 0))
        
        # Annual rent increases
        self.annual_increase_rate = float(lease_data.get('annual_rent_increases', 0))
        
        # Calculate lease term
        self.lease_term_months = self._calculate_lease_term()
        
        # Results storage
        self.initial_liability = 0
        self.initial_rou_asset = 0
        self.lease_classification = None
        self.liability_schedule = None
        self.rou_schedule = None
        self.journal_entries = []
    
    def _parse_date(self, date_input) -> datetime:
        """Parse date from various formats."""
        if isinstance(date_input, datetime):
            return date_input
        elif isinstance(date_input, str):
            try:
                return datetime.strptime(date_input, '%Y-%m-%d')
            except:
                try:
                    return datetime.strptime(date_input, '%m/%d/%Y')
                except:
                    self.errors.append(f"Unable to parse date: {date_input}")
                    return datetime.now()
        return datetime.now()
    
    def _calculate_lease_term(self) -> int:
        """Calculate effective lease term including options."""
        if not self.commencement_date or not self.end_date:
            self.errors.append("Commencement date and end date are required.")
            return 0
        if self.end_date <= self.commencement_date:
            self.errors.append(
                f"End date {self.end_date.strftime('%Y-%m-%d')} is not after "
                f"commencement {self.commencement_date.strftime('%Y-%m-%d')}."
            )
            return 0

        base_months = (self.end_date.year - self.commencement_date.year) * 12 + \
                      (self.end_date.month - self.commencement_date.month)
        if base_months <= 0:
            self.errors.append("Lease term must be at least one month.")
            return 0
        
        # Add renewal term if reasonably certain
        if self.has_renewal and self.renewal_certain:
            base_months += self.renewal_months
            self.warnings.append(f"Renewal option included: +{self.renewal_months} months")
        
        return base_months
    
    def classify_lease(self) -> str:
        """
        Classify lease as Operating or Finance under ASC 842.
        
        Finance lease if ANY of these criteria met:
        1. Transfer of ownership at end of lease
        2. Purchase option reasonably certain to exercise
        3. Lease term is major part of economic life (≥75%)
        4. PV of payments ≥ substantially all (≥90%) of FMV
        5. Specialized asset with no alternative use
        """
        reasons = []
        
        # Criterion 1: Purchase option reasonably certain
        if self.has_purchase and self.purchase_certain:
            reasons.append("Purchase option reasonably certain to exercise")
            return "FINANCE", reasons
        
        # Criterion 2: Lease term vs economic life (75% threshold)
        # Assuming 30-year economic life for commercial real estate
        economic_life_months = 30 * 12
        if self.lease_term_months / economic_life_months >= 0.75:
            reasons.append(f"Lease term ({self.lease_term_months} months) ≥ 75% of economic life")
            return "FINANCE", reasons
        
        # Criterion 3: PV vs Fair Market Value (90% threshold)
        # This requires FMV input - if not provided, skip this test
        fmv = self.lease_data.get('fair_market_value', 0)
        if fmv > 0:
            pv_payments = self.calculate_initial_lease_liability()
            if pv_payments / fmv >= 0.90:
                reasons.append(f"PV of payments (${pv_payments:,.2f}) ≥ 90% of FMV (${fmv:,.2f})")
                return "FINANCE", reasons
        
        # Default to Operating
        return "OPERATING", ["Does not meet finance lease criteria"]
    
    def calculate_payment_schedule(self) -> List[Dict]:
        """
        Generate payment schedule with annual escalations and variable adjustments.
        
        Returns:
            List of payment dictionaries with date, base payment, variable payment, total
        """
        payments = []
        current_date = self.commencement_date
        current_payment = self.monthly_payment
        
        for month in range(self.lease_term_months):
            payment_date = current_date + relativedelta(months=month)
            
            # Apply annual rent increases
            years_elapsed = month // 12
            if self.annual_increase_rate > 0 and month > 0 and month % 12 == 0:
                current_payment *= (1 + self.annual_increase_rate)
            
            # Variable payments (e.g., CPI adjustments)
            variable_amount = 0
            if self.has_variable:
                variable_amount = current_payment * self.variable_rate
            
            total_payment = current_payment + variable_amount
            
            payments.append({
                'period': month + 1,
                'date': payment_date.strftime('%Y-%m-%d'),
                'base_payment': round(current_payment, 2),
                'variable_payment': round(variable_amount, 2),
                'total_payment': round(total_payment, 2)
            })
        
        return payments
    
    def calculate_initial_lease_liability(self) -> float:
        """
        Calculate initial lease liability (PV of lease payments).
        
        Formula: PV = Σ (Payment_t / (1 + r)^t)
        where r = monthly discount rate, t = period
        """
        monthly_rate = self.discount_rate / 12
        pv = 0
        
        payment_schedule = self.calculate_payment_schedule()
        
        for payment in payment_schedule:
            period = payment['period']
            # Only include base payments in PV (variable payments excluded per ASC 842)
            payment_amount = payment['base_payment']
            discount_factor = (1 + monthly_rate) ** period
            pv += payment_amount / discount_factor
        
        # Add residual value guarantee if applicable
        if self.residual_value_guarantee > 0:
            discount_factor = (1 + monthly_rate) ** self.lease_term_months
            pv += self.residual_value_guarantee / discount_factor
        
        # Add purchase option price if reasonably certain
        if self.has_purchase and self.purchase_certain:
            discount_factor = (1 + monthly_rate) ** self.lease_term_months
            pv += self.purchase_price / discount_factor
        
        self.initial_liability = round(pv, 2)
        return self.initial_liability
    
    def calculate_initial_rou_asset(self) -> float:
        """
        Calculate initial ROU Asset.
        
        Formula: ROU Asset = Lease Liability + Initial Direct Costs + Prepayments - Lease Incentives
        """
        if self.initial_liability == 0:
            self.calculate_initial_lease_liability()
        
        rou_asset = (
            self.initial_liability +
            self.initial_direct_costs +
            self.prepayments -
            self.lease_incentives
        )
        
        self.initial_rou_asset = round(rou_asset, 2)
        return self.initial_rou_asset
    
    def generate_liability_amortization_schedule(self) -> pd.DataFrame:
        """
        Generate lease liability amortization schedule using effective interest method.
        
        Columns: Period, Date, Opening Balance, Interest Expense, Payment, Closing Balance
        """
        empty = pd.DataFrame(columns=[
            "period",
            "date",
            "opening_balance",
            "interest_expense",
            "payment",
            "principal_reduction",
            "closing_balance",
        ])
        if self.lease_term_months <= 0:
            self.liability_schedule = empty
            return empty

        if self.initial_liability == 0:
            self.calculate_initial_lease_liability()
        
        monthly_rate = self.discount_rate / 12
        payment_schedule = self.calculate_payment_schedule()
        
        schedule = []
        opening_balance = self.initial_liability
        
        for payment in payment_schedule:
            period = payment['period']
            date = payment['date']
            payment_amount = payment['base_payment']  # Only base payments reduce liability
            
            # Calculate interest expense
            interest_expense = opening_balance * monthly_rate
            
            # Principal reduction
            principal_payment = payment_amount - interest_expense
            
            # Closing balance
            closing_balance = opening_balance - principal_payment
            
            schedule.append({
                'period': period,
                'date': date,
                'opening_balance': round(opening_balance, 2),
                'interest_expense': round(interest_expense, 2),
                'payment': round(payment_amount, 2),
                'principal_reduction': round(principal_payment, 2),
                'closing_balance': round(closing_balance, 2)
            })
            
            opening_balance = closing_balance
        
        df = pd.DataFrame(schedule) if schedule else empty
        self.liability_schedule = df
        return df
    
    def generate_rou_asset_depreciation_schedule(self) -> pd.DataFrame:
        """
        Generate ROU Asset depreciation schedule (straight-line).
        
        Columns: Period, Date, Opening Balance, Depreciation Expense, Accumulated Depreciation, Net Book Value
        """
        empty = pd.DataFrame(columns=[
            "period",
            "date",
            "opening_balance",
            "depreciation_expense",
            "accumulated_depreciation",
            "net_book_value",
        ])
        if self.lease_term_months <= 0:
            self.rou_schedule = empty
            return empty

        if self.initial_rou_asset == 0:
            self.calculate_initial_rou_asset()
        
        # Determine depreciation period
        depreciation_months = self.lease_term_months
        
        # If purchase option reasonably certain, use useful life instead
        if self.has_purchase and self.purchase_certain:
            useful_life_months = self.lease_data.get('useful_life_months', self.lease_term_months)
            depreciation_months = useful_life_months
            self.warnings.append(f"Depreciating over useful life ({useful_life_months} months) due to purchase option")
        
        # Straight-line depreciation
        monthly_depreciation = self.initial_rou_asset / depreciation_months
        
        schedule = []
        accumulated_depreciation = 0
        
        for month in range(self.lease_term_months):
            period = month + 1
            date = (self.commencement_date + relativedelta(months=month)).strftime('%Y-%m-%d')
            
            opening_balance = self.initial_rou_asset - accumulated_depreciation
            
            # Calculate depreciation for this period
            depreciation_expense = monthly_depreciation if period <= depreciation_months else 0
            accumulated_depreciation += depreciation_expense
            
            net_book_value = self.initial_rou_asset - accumulated_depreciation
            
            schedule.append({
                'period': period,
                'date': date,
                'opening_balance': round(opening_balance, 2),
                'depreciation_expense': round(depreciation_expense, 2),
                'accumulated_depreciation': round(accumulated_depreciation, 2),
                'net_book_value': round(net_book_value, 2)
            })
        
        df = pd.DataFrame(schedule)
        self.rou_schedule = df
        return df
    
    def generate_initial_recognition_journal_entry(self) -> Dict:
        """Generate Day 1 journal entry."""
        entry = {
            'entry_type': 'INITIAL_RECOGNITION',
            'date': self.commencement_date.strftime('%Y-%m-%d'),
            'description': 'Initial recognition of lease under ASC 842',
            'lines': [
                {
                    'account': 'ROU Asset - Lease',
                    'debit': self.initial_rou_asset,
                    'credit': 0
                },
                {
                    'account': 'Lease Liability - Current',
                    'debit': 0,
                    'credit': self.initial_liability * 0.20  # Estimate 20% current
                },
                {
                    'account': 'Lease Liability - Non-Current',
                    'debit': 0,
                    'credit': self.initial_liability * 0.80  # Estimate 80% non-current
                }
            ]
        }
        
        # Add prepayment if applicable
        if self.prepayments > 0:
            entry['lines'][0]['debit'] -= self.prepayments  # ROU already includes prepayment
            entry['lines'].insert(0, {
                'account': 'Prepaid Rent',
                'debit': self.prepayments,
                'credit': 0
            })
        
        # Add initial direct costs if applicable
        if self.initial_direct_costs > 0:
            entry['lines'].append({
                'account': 'Cash',
                'debit': 0,
                'credit': self.initial_direct_costs
            })
        
        return entry
    
    def generate_monthly_journal_entries(self) -> List[Dict]:
        """Generate monthly recurring journal entries for interest and depreciation."""
        if self.liability_schedule is None:
            self.generate_liability_amortization_schedule()
        if self.rou_schedule is None:
            self.generate_rou_asset_depreciation_schedule()
        
        entries = []
        
        for index, row in self.liability_schedule.iterrows():
            period = row['period']
            date = row['date']
            interest = row['interest_expense']
            payment = row['payment']
            depreciation = self.rou_schedule.iloc[index]['depreciation_expense']
            
            # Interest expense entry
            entries.append({
                'entry_type': 'MONTHLY_INTEREST',
                'period': f"Month {period}",
                'date': date,
                'description': f'Lease interest expense for period {period}',
                'lines': [
                    {'account': 'Interest Expense - Lease', 'debit': round(interest, 2), 'credit': 0},
                    {'account': 'Lease Liability', 'debit': 0, 'credit': round(interest, 2)}
                ]
            })
            
            # Depreciation expense entry
            entries.append({
                'entry_type': 'MONTHLY_DEPRECIATION',
                'period': f"Month {period}",
                'date': date,
                'description': f'ROU Asset depreciation for period {period}',
                'lines': [
                    {'account': 'Depreciation Expense - ROU Asset', 'debit': round(depreciation, 2), 'credit': 0},
                    {'account': 'Accumulated Depreciation - ROU Asset', 'debit': 0, 'credit': round(depreciation, 2)}
                ]
            })
            
            # Payment entry
            entries.append({
                'entry_type': 'PAYMENT',
                'period': f"Month {period}",
                'date': date,
                'description': f'Lease payment for period {period}',
                'lines': [
                    {'account': 'Lease Liability', 'debit': round(payment, 2), 'credit': 0},
                    {'account': 'Cash', 'debit': 0, 'credit': round(payment, 2)}
                ]
            })
        
        self.journal_entries = entries
        return entries
    
    def generate_disclosure_report(self) -> Dict:
        """Generate comprehensive disclosure information for financial statements."""
        if self.liability_schedule is None:
            self.generate_liability_amortization_schedule()
        if self.rou_schedule is None:
            self.generate_rou_asset_depreciation_schedule()
        
        # Maturity analysis (future payments by year)
        payment_schedule = self.calculate_payment_schedule()
        maturity_analysis = {}
        
        for payment in payment_schedule:
            year = datetime.strptime(payment['date'], '%Y-%m-%d').year
            if year not in maturity_analysis:
                maturity_analysis[year] = 0
            maturity_analysis[year] += payment['total_payment']
        
        # Calculate totals
        total_future_payments = sum(p['total_payment'] for p in payment_schedule)
        liability = self.liability_schedule if self.liability_schedule is not None else pd.DataFrame()
        rou = self.rou_schedule if self.rou_schedule is not None else pd.DataFrame()
        total_interest = liability["interest_expense"].sum() if "interest_expense" in liability.columns and not liability.empty else 0
        total_depreciation = rou["depreciation_expense"].sum() if "depreciation_expense" in rou.columns and not rou.empty else 0
        
        disclosure = {
            'lease_classification': self.lease_classification,
            'lease_term_months': self.lease_term_months,
            'commencement_date': self.commencement_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'discount_rate': f"{self.discount_rate * 100:.2f}%",
            
            'initial_measurement': {
                'lease_liability': self.initial_liability,
                'rou_asset': self.initial_rou_asset,
                'initial_direct_costs': self.initial_direct_costs,
                'lease_incentives': self.lease_incentives,
                'prepayments': self.prepayments
            },
            
            'maturity_analysis': {str(year): round(amount, 2) for year, amount in sorted(maturity_analysis.items())},
            
            'lease_expense_summary': {
                'total_interest_expense': round(total_interest, 2),
                'total_depreciation_expense': round(total_depreciation, 2),
                'total_lease_expense': round(total_interest + total_depreciation, 2)
            },
            
            'balance_sheet_impact': {
                'current_liability': round(liability[liability['period'] <= 12]['principal_reduction'].sum(), 2) if 'principal_reduction' in liability.columns and not liability.empty else 0,
                'non_current_liability': round(liability[liability['period'] > 12]['closing_balance'].iloc[-1], 2) if 'closing_balance' in liability.columns and len(liability) > 12 else 0,
                'rou_asset_net_book_value': round(rou['net_book_value'].iloc[-1], 2) if 'net_book_value' in rou.columns and not rou.empty else 0
            },
            
            'lease_terms': {
                'has_renewal_option': self.has_renewal,
                'has_purchase_option': self.has_purchase,
                'has_termination_option': self.has_termination,
                'has_variable_payments': self.has_variable
            }
        }
        
        return disclosure
    
    def run_full_calculation(self) -> Dict:
        """
        Run complete ASC 842 compliance calculation.
        
        Returns:
            Dictionary with all calculation results
        """
        if self.lease_term_months <= 0:
            message = self.errors[-1] if self.errors else "Lease term is not a positive number of months."
            raise ValueError(message)

        # Step 1: Classify lease
        self.lease_classification, classification_reasons = self.classify_lease()
        
        # Step 2: Calculate initial measurement
        self.calculate_initial_lease_liability()
        self.calculate_initial_rou_asset()
        
        # Step 3: Generate schedules
        liability_df = self.generate_liability_amortization_schedule()
        rou_df = self.generate_rou_asset_depreciation_schedule()
        
        # Step 4: Generate journal entries
        initial_entry = self.generate_initial_recognition_journal_entry()
        monthly_entries = self.generate_monthly_journal_entries()
        
        # Step 5: Generate disclosures
        disclosures = self.generate_disclosure_report()
        
        return {
            'classification': self.lease_classification,
            'classification_reasons': classification_reasons,
            'initial_liability': self.initial_liability,
            'initial_rou_asset': self.initial_rou_asset,
            'lease_term_months': self.lease_term_months,
            'liability_schedule': liability_df.to_dict('records'),
            'rou_asset_schedule': rou_df.to_dict('records'),
            'initial_journal_entry': initial_entry,
            'monthly_journal_entries': monthly_entries[:6],  # First 6 months as sample
            'disclosures': disclosures,
            'warnings': self.warnings,
            'errors': self.errors
        }


# Example usage
if __name__ == "__main__":
    # Test case
    test_lease = {
        'commencement_date': '2024-01-01',
        'end_date': '2028-12-31',
        'monthly_payment': 5000,
        'discount_rate': 0.06,  # 6% annual
        'initial_direct_costs': 2500,
        'lease_incentives': 5000,
        'prepayments': 5000,
        'annual_rent_increases': 0.03,  # 3% annual increases
        'has_renewal_option': True,
        'renewal_term_months': 24,
        'renewal_reasonably_certain': False,
    }
    
    engine = ASC842ComplianceEngine(test_lease)
    results = engine.run_full_calculation()
    
    print("=" * 80)
    print("ASC 842 COMPLIANCE CALCULATION RESULTS")
    print("=" * 80)
    print(f"\nLease Classification: {results['classification']}")
    print(f"Reasons: {', '.join(results['classification_reasons'])}")
    print(f"\nInitial Lease Liability: ${results['initial_liability']:,.2f}")
    print(f"Initial ROU Asset: ${results['initial_rou_asset']:,.2f}")
    print(f"Lease Term: {results['lease_term_months']} months")
    print(f"\nWarnings: {len(results['warnings'])}")
    for warning in results['warnings']:
        print(f"  - {warning}")
