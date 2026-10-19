"""
Quick test to verify field mapping with your actual lease data
"""

from supabase import create_client
import config
from pms_export import export_to_yardi, export_to_mri

sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

print("\n" + "="*60)
print("TESTING PMS EXPORT WITH YOUR LEASE DATA")
print("="*60 + "\n")

# Get the most recent lease
leases = sb.table("leases").select("*").order("created_at", desc=True).limit(1).execute()

if not leases.data:
    print("No leases found.")
    exit()

lease = leases.data[0]
lease_id = lease['id']
print(f"Testing with lease: {lease.get('filename', 'Unknown')}")
print(f"Lease ID: {lease_id}\n")

# Get fields
fields = sb.table("extracted_fields").select("*").eq("lease_id", lease_id).order("field_number").execute()

print(f"Found {len(fields.data)} fields\n")

# Prepare extracted_dict the same way Streamlit does
extracted_dict = {}
for field in fields.data:
    field_name = field.get("field_name", "Unknown")
    extracted_dict[field_name] = {
        "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
        "confidence": field.get("confidence", "MEDIUM")
    }

# Show a few field names
print("Sample field names in extracted_dict:")
for i, name in enumerate(list(extracted_dict.keys())[:10]):
    print(f"  {i+1}. {name}")
print()

# Test Yardi export
print("-"*60)
print("TESTING YARDI EXPORT")
print("-"*60)

try:
    csv_bytes = export_to_yardi(lease, extracted_dict)
    csv_str = csv_bytes.decode('utf-8')
    
    print("✅ Yardi export successful!\n")
    print("Generated CSV:")
    print(csv_str)
    
    # Parse and show specific fields
    lines = csv_str.strip().split('\n')
    if len(lines) >= 2:
        headers = lines[0].split(',')
        values = lines[1].split(',')
        
        print("\n" + "="*60)
        print("KEY FIELD VALUES:")
        print("="*60)
        
        for h, v in zip(headers, values):
            # Remove quotes
            v_clean = v.strip('"')
            if v_clean:  # Only show non-empty values
                print(f"{h}: {v_clean}")
        
except Exception as e:
    print(f"❌ Export failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
