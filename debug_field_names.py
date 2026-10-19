"""
Debug script to show what field names are in the database
Run this to see exactly what your extracted fields are called
"""

from supabase import create_client
import config

sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

print("\n" + "="*60)
print("CHECKING FIELD NAMES IN DATABASE")
print("="*60 + "\n")

# Get all leases
leases = sb.table("leases").select("id, filename").order("created_at", desc=True).limit(5).execute()

if not leases.data:
    print("No leases found in database.")
    exit()

print(f"Found {len(leases.data)} recent leases\n")

# Check the most recent lease
lease = leases.data[0]
lease_id = lease['id']
filename = lease.get('filename', 'Unknown')

print(f"Checking lease: {filename}")
print(f"Lease ID: {lease_id}\n")

# Get all fields for this lease
fields = sb.table("extracted_fields").select("*").eq("lease_id", lease_id).order("field_number").execute()

if not fields.data:
    print("No extracted fields found for this lease.")
    exit()

print(f"Found {len(fields.data)} extracted fields:\n")
print("-"*60)

# Show all field names and their values
for i, field in enumerate(fields.data, 1):
    field_name = field.get('field_name', 'Unknown')
    raw_value = field.get('raw_value', '')
    reviewed_value = field.get('reviewed_value', '')
    confidence = field.get('confidence', 'UNKNOWN')
    
    value = reviewed_value or raw_value or "NOT FOUND"
    
    # Truncate long values
    if len(value) > 50:
        value = value[:47] + "..."
    
    print(f"{i:2}. {field_name}")
    print(f"    Value: {value}")
    print(f"    Confidence: {confidence}")
    print()

print("-"*60)
print("\nIMPORTANT FIELD NAMES FOR EXPORT:")
print("-"*60)

# List the fields the export expects
expected_fields = [
    "Tenant Legal Name",
    "Tenant ID", 
    "Unit Number",
    "Lease Start Date",
    "Lease End Date",
    "Base Rent",
    "Rent Payment Frequency",
    "Security Deposit",
    "Rentable Square Footage",
    "Permitted Use",
    "Rent Escalation Type",
    "Rent Escalation Percentage",
    "CAM Base Amount",
    "CAM Calculation Method",
    "Number of Renewal Options",
    "Non-Renewal Notice Period",
    "Lease Type",
    "Building Name",
    "Operating Expense Base Year Amount",
    "Tenant Improvement Allowance",
    "Free Rent Period"
]

# Check which expected fields exist
field_names = [f.get('field_name', '') for f in fields.data]

print("\nChecking which expected fields are in your database:\n")

for expected in expected_fields:
    if expected in field_names:
        print(f"✅ {expected}")
    else:
        # Try to find similar names
        similar = [fn for fn in field_names if expected.lower() in fn.lower() or fn.lower() in expected.lower()]
        if similar:
            print(f"❌ {expected} (found similar: {', '.join(similar[:3])})")
        else:
            print(f"❌ {expected} (NOT FOUND)")

print("\n" + "="*60)
