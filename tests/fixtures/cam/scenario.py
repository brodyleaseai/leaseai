"""Canonical numbers for the Northridge / Cascade Analytics CAM test pair.

The lease and CAM statement PDFs, the expected-results README, and
test_cam_fixtures.py all read from this module so the planted overcharge
cannot drift from what cam_engine.py will compute.
"""

from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent

LEASE_PDF_NAME = "Northridge_Meridian_Tower_Office_Lease.pdf"
STATEMENT_PDF_NAME = "Northridge_2025_CAM_Reconciliation_Statement.pdf"

LEASE_PDF = FIXTURE_DIR / LEASE_PDF_NAME
STATEMENT_PDF = FIXTURE_DIR / STATEMENT_PDF_NAME

# Parties and property (all fictional)
LANDLORD_NAME = "Northridge Office Partners, LLC"
LANDLORD_NOTICE = "800 Pioneer Square, Suite 1200, Seattle, Washington 98104"
TENANT_NAME = "Cascade Analytics, Inc."
TENANT_TRADE_NAME = "Cascade Analytics"
PROPERTY_ADDRESS = "1200 Cascade Plaza, Portland, Oregon 97204"
PROPERTY_NAME = "The Meridian Tower"
SUITE = "Suite 400"
FLOOR = "4"
LEGAL_DESCRIPTION = (
    "Lot 4, Block 2, Cascade Plaza Addition, City of Portland, "
    "Multnomah County, Oregon"
)
BUILDING_CLASS = "Class A"

# Size / share
PREMISES_RSF = 12500
BUILDING_RSF = 100000
TENANT_PRORATA_SHARE = PREMISES_RSF / BUILDING_RSF  # 0.125
TENANT_PRORATA_PERCENT = 12.50

# Term
COMMENCEMENT_DATE = "January 1, 2023"
RENT_COMMENCEMENT_DATE = "January 1, 2023"
EXPIRATION_DATE = "December 31, 2027"
TERM_MONTHS = 60
LEASE_TYPE = "Modified Gross"
GOVERNING_LAW = "State of Oregon"

# CAM terms that the reconciliation engine actually uses
CAM_BASE_YEAR = 2023
CAM_BASE_AMOUNT = 100000.00  # tenant share in the base year
CAM_CAP_PERCENTAGE = 5.0
HAS_CAM_CAP = True
# No CAM stop: cam_engine currently replaces the share with the overage
# when a stop is set, which would confuse this test.
CAM_STOP_AMOUNT = None
CAM_PAYMENT_FREQUENCY = "MONTHLY"
RECONCILIATION_DEADLINE = "Within 120 days of calendar year end"
TENANT_AUDIT_RIGHT = True
AUDIT_DEADLINE = "Within 90 days of receipt of the annual CAM reconciliation"

CAM_EXCLUSIONS = [
    "capital improvements",
    "structural repairs",
    "roof replacement",
    "depreciation",
    "debt service",
    "mortgage payments",
    "legal fees relating to other tenants",
]

# Categories cam_engine.CAMProvisionExtractor._parse_exclusions will emit
CAM_EXCLUSION_CATEGORIES = [
    "CAPITAL_IMPROVEMENTS",
    "STRUCTURAL_REPAIRS",
    "ROOF_REPLACEMENT",
    "DEPRECIATION",
    "DEBT_SERVICE",
    "MORTGAGE_PAYMENTS",
    "LEGAL_FEES",
]

# 2025 landlord statement
RECONCILIATION_YEAR = 2025
STATEMENT_DATE = "March 15, 2026"
STATEMENT_PERIOD = "January 1, 2025 through December 31, 2025"

# Line items. Allowable operating costs total $821,000.
# Planted excluded costs total $379,000. Building total $1,200,000.
ALLOWABLE_LINE_ITEMS = [
    ("Electricity — common area and HVAC plant", "UTILITIES", 145000.00),
    ("Water and sewer", "UTILITIES", 38000.00),
    ("Natural gas", "UTILITIES", 22000.00),
    ("Janitorial and night cleaning", "JANITORIAL", 95000.00),
    ("HVAC maintenance contract", "HVAC", 48000.00),
    ("Elevator maintenance contract", "ELEVATOR", 36000.00),
    ("Landscaping and grounds", "LANDSCAPING", 28000.00),
    ("Snow and ice removal", "SNOW_REMOVAL", 12000.00),
    ("Security services", "SECURITY", 64000.00),
    ("Parking lot maintenance", "PARKING", 18000.00),
    ("Building property insurance", "INSURANCE", 85000.00),
    ("Property management fee", "MANAGEMENT_FEE", 72000.00),
    ("Routine repairs and maintenance", "MAINTENANCE", 89000.00),
    ("Common area lighting", "UTILITIES", 15000.00),
    ("Fire and life safety monitoring", "SECURITY", 21000.00),
    ("Window washing", "JANITORIAL", 8000.00),
    ("Pest control", "MAINTENANCE", 6000.00),
    ("Trash and recycling", "MAINTENANCE", 19000.00),
]

# These should be challenged under the lease CAM Exclusions.
EXCLUDED_LINE_ITEMS = [
    ("Roof replacement — full membrane (capital improvement)", "CAPITAL_IMPROVEMENTS", 180000.00),
    ("Structural steel repairs — Level 2 transfer beam", "STRUCTURAL_REPAIRS", 40000.00),
    ("Legal fees — eviction of unrelated tenant", "LEGAL_FEES", 14000.00),
    ("Depreciation expense", "DEPRECIATION", 25000.00),
    ("Mortgage interest / debt service", "DEBT_SERVICE", 120000.00),
]

BUILDING_TOTAL_CHARGES = sum(item[2] for item in ALLOWABLE_LINE_ITEMS + EXCLUDED_LINE_ITEMS)
TENANT_SHARE_BILLED = round(BUILDING_TOTAL_CHARGES * TENANT_PRORATA_SHARE, 2)
ESTIMATED_CAM_PAID = 108000.00  # $9,000 x 12
BALANCE_DUE_BILLED = round(TENANT_SHARE_BILLED - ESTIMATED_CAM_PAID, 2)

# What cam_engine.calculate_tenant_share should return when given
# BUILDING_TOTAL_CHARGES and the provisions below:
#   1,200,000 x 0.125 = 150,000
#   cap = 100,000 + (100,000 x 5%) = 105,000
CALCULATED_TENANT_SHARE = 105000.00
VARIANCE_OVERCHARGE = round(TENANT_SHARE_BILLED - CALCULATED_TENANT_SHARE, 2)
VARIANCE_SEVERITY = "CRITICAL"  # overcharge > $2,000
RECOMMENDED_ACTION = "CHALLENGE_IMMEDIATELY"

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
