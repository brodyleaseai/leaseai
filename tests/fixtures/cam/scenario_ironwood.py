"""Canonical numbers for the Ironwood / Pinnacle Fresh CAM test pair.

Retail grocery, 20% share, 2024 statement. Unlike Northridge, the 4%
annual cap binds after excluded costs are removed.
"""

from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent

LEASE_PDF_NAME = "Ironwood_Shops_Grocery_Lease.pdf"
STATEMENT_PDF_NAME = "Ironwood_2024_CAM_Reconciliation_Statement.pdf"

LEASE_PDF = FIXTURE_DIR / LEASE_PDF_NAME
STATEMENT_PDF = FIXTURE_DIR / STATEMENT_PDF_NAME

LANDLORD_NAME = "Ironwood Retail Partners, LLC"
LANDLORD_NOTICE = "1601 Wewatta Street, Suite 700, Denver, Colorado 80202"
TENANT_NAME = "Pinnacle Grocery Company"
TENANT_TRADE_NAME = "Pinnacle Fresh"
PROPERTY_ADDRESS = "4800 East Colfax Avenue, Denver, Colorado 80220"
PROPERTY_NAME = "The Ironwood Shops"
SUITE = "Suite 100"
FLOOR = "1"
LEGAL_DESCRIPTION = (
    "Lot 8, Block 1, Ironwood Commercial Subdivision, City and County of Denver, Colorado"
)
BUILDING_CLASS = "Grocery-anchored strip center"

PREMISES_RSF = 8000
BUILDING_RSF = 40000
TENANT_PRORATA_SHARE = PREMISES_RSF / BUILDING_RSF  # 0.20
TENANT_PRORATA_PERCENT = 20.00

COMMENCEMENT_DATE = "March 1, 2022"
RENT_COMMENCEMENT_DATE = "April 1, 2022"
EXPIRATION_DATE = "February 28, 2032"
TERM_MONTHS = 120
LEASE_TYPE = "Triple Net (NNN)"
GOVERNING_LAW = "State of Colorado"
DISPUTE_VENUE = "Denver County, Colorado"
DOC_KIND = "RETAIL / GROCERY LEASE AGREEMENT"

CAM_BASE_YEAR = 2022
CAM_BASE_AMOUNT = 80000.00
CAM_CAP_PERCENTAGE = 4.0
CAM_CAP_PERCENTAGE_WORDS = "four percent (4%)"
HAS_CAM_CAP = True
CAM_STOP_AMOUNT = None
CAM_PAYMENT_FREQUENCY = "MONTHLY"
RECONCILIATION_DEADLINE = "Within 90 days of calendar year end"
TENANT_AUDIT_RIGHT = True
AUDIT_DEADLINE = "Within 60 days of receipt of the annual CAM reconciliation"
LEASE_TYPE_DETAIL = (
    "Tenant pays Base Rent, its pro-rata share of CAM / Operating Cost Charges, "
    "real property taxes, and insurance as provided in this Lease."
)
CAM_EXCLUSIONS_CLAUSE = (
    "Operating Expenses shall exclude, and Landlord shall not pass through, the following "
    "CAM Exclusions: capital improvements; parking lot reconstruction; HVAC replacement; "
    "roof replacement; and legal fees relating to other tenants. Capital improvements, "
    "parking lot reconstruction, HVAC replacement, and roof replacement are Landlord's sole cost."
)
BASE_RENT_CLAUSES = [
    "4.1 Base Rent Schedule. Base Rent is calculated at Twenty-Eight and 00/100 "
    "Dollars ($28.00) per rentable square foot per year for Year 1, with a "
    "fixed two and one-half percent (2.5%) Annual Escalation Type (Fixed / CPI / Percentage) "
    "and Annual Escalation Rate or Cap of 2.5%. CPI Index Used: not applicable. "
    "Percentage Rent Clause: none. Gross Revenue Breakpoint: not applicable.",
    "Base Rent Year 1 (monthly): $18,666.67. "
    "Full Rent Schedule (all years): Year 1 $224,000.00, increasing 2.5% annually "
    "for the remainder of the ten-year term.",
]
SECURITY_CLAUSES = [
    "5.1 Security Deposit Amount: $37,333.34 (two months of Year 1 Base Rent). "
    "Security Deposit — Letter of Credit: not required. "
    "Security Deposit Reduction Schedule: none.",
    "5.2 Parking — Number of Stalls: 40 customer stalls plus 8 employee stalls. "
    "Parking — Monthly Cost per Stall: $0.00 (included). Storage Space Included: "
    "rear dry-storage cage. Signage Rights: Tenant may install building-mounted "
    "grocery identification signage subject to Landlord approval and municipal code. "
    "Roof / Exterior Access Rights: Tenant may place rooftop refrigeration condensers "
    "subject to Landlord approval.",
]
USE_CLAUSES = [
    "6.1 Permitted Use: supermarket and grocery store, including bakery, deli, pharmacy, and "
    "incidental retail uses. Prohibited Uses / Exclusivity Clause: Landlord shall not lease "
    "other premises in the center for a competing full-service grocery. Co-Tenancy Clause: none.",
    "6.2 Subletting / Assignment Rights: Tenant may assign or sublet with "
    "Landlord's prior written consent, not to be unreasonably withheld. "
    "Subletting — Landlord Consent Required: Yes.",
    "6.3 Tenant Improvement Allowance (TIA): $55.00 per RSF, equal to "
    "$440,000.00. TIA Conditions / Milestones: paid upon substantial "
    "completion of Tenant's initial grocery build-out and delivery of lien waivers. "
    "Alterations — Landlord Consent Threshold: any alteration exceeding "
    "$50,000.00 requires Landlord consent. "
    "ADA / Accessibility Compliance Responsibility: Landlord as to the "
    "center common areas; Tenant as to the Premises.",
]
TAX_CLAUSES = [
    "8.1 Property Tax Responsibility: Tenant pays its pro-rata share of real property "
    "taxes separately from CAM. Property Insurance Responsibility: Landlord carries "
    "building insurance; Tenant's pro-rata share is billed as a CAM item. "
    "Tenant Insurance Requirements: commercial general liability, product liability, "
    "and property insurance covering Tenant's inventory and equipment. "
    "Tenant Liability Insurance Minimum: $5,000,000 per occurrence.",
    "8.2 Utilities Responsibility: Tenant pays electricity, gas, and water serving the "
    "Premises directly; common-area utilities are CAM. HVAC Responsibility "
    "(Landlord / Tenant): Tenant for Premises HVAC; Landlord for common-area HVAC. "
    "HVAC Maintenance Obligation: Tenant for Premises units; Landlord for common-area "
    "units as a CAM expense for routine maintenance. Replacement of rooftop HVAC units "
    "is a CAM Exclusion. Janitorial Responsibility: Tenant for the Premises; Landlord "
    "for common areas (CAM). Structural / Roof Repair Responsibility: Landlord, and "
    "such costs are CAM Exclusions (not pass-through).",
]
RENEWAL_CLAUSES = [
    "9.1 Number of Renewal Options: two (2). Renewal Option Term Length: "
    "five (5) years each. Renewal Notice Deadline: twelve (12) months prior "
    "to the then-current expiration. Renewal Rent Basis (FMV / Fixed / CPI): "
    "Fair Market Value (FMV). Right of First Refusal: none. Right of First "
    "Offer: none. Expansion Option: none. Contraction / Reduction Option: none.",
    "9.2 Early Termination Right: none. Termination Notice Period: not "
    "applicable. Early Termination Fee / Penalty: not applicable.",
]

CAM_EXCLUSIONS = [
    "capital improvements",
    "parking lot reconstruction",
    "HVAC replacement",
    "roof replacement",
    "legal fees relating to other tenants",
]

CAM_EXCLUSION_CATEGORIES = [
    "CAPITAL_IMPROVEMENTS",
    "ROOF_REPLACEMENT",
    "LEGAL_FEES",
]

PERMITTED_USE = (
    "supermarket and grocery store, including bakery, deli, pharmacy, and "
    "incidental retail uses"
)
LANDLORD_SIGNER = "David Chen, Managing Member"
TENANT_SIGNER = "Alicia Romero, Vice President, Real Estate"
ACCOUNTING_SIGNER = "Jordan Blake"
ACCOUNTING_TITLE = "Controller"
BASE_RENT_PSF = 28.00

RECONCILIATION_YEAR = 2024
STATEMENT_DATE = "February 28, 2025"
STATEMENT_PERIOD = "January 1, 2024 through December 31, 2024"

# Allowable operating costs total $500,000.
ALLOWABLE_LINE_ITEMS = [
    ("Electricity — common area and parking lot", "UTILITIES", 85000.00),
    ("Water and sewer", "UTILITIES", 18000.00),
    ("Natural gas — common area", "UTILITIES", 22000.00),
    ("Janitorial and night cleaning", "JANITORIAL", 45000.00),
    ("HVAC maintenance contract (routine)", "HVAC", 28000.00),
    ("Landscaping and grounds", "LANDSCAPING", 16000.00),
    ("Snow and ice removal", "SNOW_REMOVAL", 14000.00),
    ("Security services", "SECURITY", 38000.00),
    ("Parking lot sweeping and striping", "PARKING", 9000.00),
    ("Building property insurance", "INSURANCE", 52000.00),
    ("Property management fee", "MANAGEMENT_FEE", 40000.00),
    ("Routine repairs and maintenance", "MAINTENANCE", 96000.00),
    ("Common area lighting", "UTILITIES", 11000.00),
    ("Pest control", "MAINTENANCE", 5000.00),
    ("Trash and recycling", "MAINTENANCE", 16000.00),
    ("Window washing", "JANITORIAL", 5000.00),
]

# Planted exclusions: capital / roof / legal. No depreciation or debt service.
EXCLUDED_LINE_ITEMS = [
    ("Parking lot reconstruction — full mill and overlay (capital improvement)", "CAPITAL_IMPROVEMENTS", 90000.00),
    ("Rooftop HVAC replacement — four 20-ton units (capital improvement)", "CAPITAL_IMPROVEMENTS", 75000.00),
    ("Roof replacement — grocery wing TPO membrane", "ROOF_REPLACEMENT", 50000.00),
    ("Legal fees — eviction of vacant-space tenant", "LEGAL_FEES", 8000.00),
]

BUILDING_TOTAL_CHARGES = sum(item[2] for item in ALLOWABLE_LINE_ITEMS + EXCLUDED_LINE_ITEMS)
ALLOWABLE_BUILDING_CHARGES = sum(item[2] for item in ALLOWABLE_LINE_ITEMS)
EXCLUDED_BUILDING_CHARGES = sum(item[2] for item in EXCLUDED_LINE_ITEMS)
TENANT_SHARE_BILLED = round(BUILDING_TOTAL_CHARGES * TENANT_PRORATA_SHARE, 2)
SHARE_AFTER_EXCLUSIONS = round(ALLOWABLE_BUILDING_CHARGES * TENANT_PRORATA_SHARE, 2)
CAP_CEILING = round(CAM_BASE_AMOUNT * (1 + CAM_CAP_PERCENTAGE / 100.0), 2)
# Cap binds: $100,000 after exclusions > $83,200 ceiling.
CALCULATED_TENANT_SHARE = CAP_CEILING
VARIANCE_OVERCHARGE = round(TENANT_SHARE_BILLED - CALCULATED_TENANT_SHARE, 2)
VARIANCE_SEVERITY = "CRITICAL"
RECOMMENDED_ACTION = "CHALLENGE_IMMEDIATELY"

ESTIMATED_CAM_PAID = 84000.00  # $7,000 x 12
ESTIMATED_MONTHLY = 7000.00
BALANCE_DUE_BILLED = round(TENANT_SHARE_BILLED - ESTIMATED_CAM_PAID, 2)

PROVISIONS_FOR_ENGINE = {
    "tenant_prorata_share": TENANT_PRORATA_SHARE,
    "has_cam_cap": HAS_CAM_CAP,
    "cam_cap_percentage": CAM_CAP_PERCENTAGE,
    "cam_base_amount": CAM_BASE_AMOUNT,
    "cam_stop_amount": CAM_STOP_AMOUNT,
    "cam_base_year": CAM_BASE_YEAR,
    "excluded_items": CAM_EXCLUSION_CATEGORIES,
}


def money(amount: float) -> str:
    return f"${amount:,.2f}"
