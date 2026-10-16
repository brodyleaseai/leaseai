"""
Lease Clause History Seeder
Seeds the lease_clause_history table with version 0 (base lease) values
This must run after lease extraction to enable Amendment Resolution Graph™
"""

from datetime import datetime
from typing import Dict
import config
from supabase import create_client


def seed_base_lease_clause_history(
    lease_id: str,
    extracted_fields: Dict,
    lease_commencement_date: str,
    supabase_client
) -> int:
    """
    Seed the lease_clause_history table with base lease (version 0) values.
    
    This creates the foundation for the Amendment Resolution Graph™.
    Without version 0, amendments cannot track what changed from the original.
    
    Args:
        lease_id: UUID of the lease
        extracted_fields: Dictionary of extracted lease fields
        lease_commencement_date: Lease commencement date (ISO format)
        supabase_client: Supabase client instance
        
    Returns:
        Number of clause history records created
    """
    
    print(f"\n🌱 Seeding base lease clause history for lease {lease_id}...")
    
    # Map extracted field names to clause types
    field_to_clause_mapping = {
        # Financial
        "Base Rent Year 1 (monthly)": "Base Rent",
        "Full Rent Schedule (all years)": "Rent Schedule",
        "Annual Escalation Rate or Cap": "Rent Escalations",
        "Security Deposit Amount": "Security Deposit",
        "Free Rent Period (months)": "Free Rent Period",
        
        # Operating Costs
        "CAM / Operating Cost Charges": "CAM Charges",
        "CAM Annual Increase Cap (%)": "CAM Cap",
        "CAM Exclusions": "CAM Exclusions",
        "Property Tax Responsibility": "Property Taxes",
        "Property Insurance Responsibility": "Insurance Costs",
        "Utilities Responsibility": "Utilities",
        
        # Term & Options
        "Lease Term (Total Months)": "Lease Term",
        "Lease Commencement Date": "Commencement Date",
        "Lease Expiration Date": "Expiration Date",
        "Number of Renewal Options": "Renewal Options",
        "Renewal Option Term Length": "Renewal Term Length",
        "Renewal Notice Deadline": "Renewal Notice Deadline",
        "Early Termination Right": "Termination Rights",
        "Holdover Provision (rate & notice)": "Holdover Provisions",
        
        # Use & Operations
        "Permitted Use": "Permitted Use",
        "Prohibited Uses / Exclusivity Clause": "Prohibited Uses",
        "Co-Tenancy Clause": "Co-Tenancy Clause",
        "Operating Hours Responsibility": "Operating Hours",
        "Signage Rights": "Signage Rights",
        
        # Space & Access
        "Premises Square Footage (RSF)": "Premises Description",
        "Parking — Number of Stalls": "Parking Spaces",
        "Parking — Monthly Cost per Stall": "Parking Cost",
        "Storage Space Included": "Storage Space",
        "Roof / Exterior Access Rights": "Roof Access",
        
        # Responsibilities
        "Tenant Maintenance Obligation": "Maintenance Obligations",
        "HVAC Responsibility (Landlord / Tenant)": "HVAC Responsibility",
        "HVAC Maintenance Obligation": "HVAC Maintenance",
        "Structural / Roof Repair Responsibility": "Structural Repairs",
        "Janitorial Responsibility": "Janitorial",
        "ADA / Accessibility Compliance Responsibility": "ADA Compliance",
        
        # Legal & Assignment
        "Subletting / Assignment Rights": "Assignment Rights",
        "Subletting — Landlord Consent Required": "Subletting Rights",
        "Tenant Insurance Requirements": "Insurance Requirements",
        "Tenant Liability Insurance Minimum": "Liability Insurance",
        "Default Cure Period (Tenant)": "Default Cure Period",
        "Force Majeure Clause": "Force Majeure",
        
        # Improvements
        "Tenant Improvement Allowance (TIA)": "TI Allowance",
        "TIA Conditions / Milestones": "TI Conditions",
        "Alterations — Landlord Consent Threshold": "Alterations",
    }
    
    records_created = 0
    
    for field_name, clause_type in field_to_clause_mapping.items():
        if field_name not in extracted_fields:
            continue
        
        field_data = extracted_fields[field_name]
        
        # Extract value from field data structure
        if isinstance(field_data, dict):
            value = field_data.get("value")
            confidence = field_data.get("confidence", "MEDIUM")
        else:
            value = str(field_data)
            confidence = "MEDIUM"
        
        # Skip if not found or empty
        if not value or value == "NOT FOUND" or value == "N/A":
            continue
        
        # Check if this clause type already exists in history (avoid duplicates)
        existing = supabase_client.table("lease_clause_history").select("id").eq(
            "lease_id", lease_id
        ).eq(
            "clause_type", clause_type
        ).eq(
            "version_number", 0
        ).execute()
        
        if existing.data:
            print(f"  ⏭️  Skipping {clause_type} (already exists)")
            continue
        
        # Create version 0 (base lease) record
        history_record = {
            "lease_id": lease_id,
            "clause_type": clause_type,
            "version_number": 0,  # Version 0 = base lease
            "source_document_type": "BASE_LEASE",
            "source_document_id": lease_id,
            "clause_value": value,
            "effective_from": lease_commencement_date,
            "effective_to": None,  # Still current unless amended
            "is_current": True,
            "modification_type": None,  # No modification, this is original
            "created_at": datetime.utcnow().isoformat(),
        }
        
        try:
            supabase_client.table("lease_clause_history").insert(history_record).execute()
            print(f"  ✓ {clause_type}: {value[:60]}...")
            records_created += 1
        except Exception as e:
            print(f"  ⚠️  Failed to insert {clause_type}: {e}")
    
    print(f"\n✅ Seeded {records_created} base lease clause history record(s)")
    return records_created


def seed_lease_from_id(lease_id: str):
    """
    Seed clause history for a lease by ID.
    Utility function for CLI usage.
    
    Args:
        lease_id: UUID of the lease to seed
    """
    
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # Get lease data
    lease_response = sb.table("leases").select("*").eq("id", lease_id).execute()
    if not lease_response.data:
        print(f"❌ Lease {lease_id} not found")
        return
    
    lease_data = lease_response.data[0]
    extracted_data = lease_data.get("extracted_data", {})
    
    # Get commencement date
    commencement_field = extracted_data.get("Lease Commencement Date", {})
    if isinstance(commencement_field, dict):
        commencement_date = commencement_field.get("value", lease_data.get("created_at", ""))
    else:
        commencement_date = commencement_field or lease_data.get("created_at", "")
    
    # Parse date if needed
    from datetime import datetime
    try:
        if "T" in commencement_date:
            # ISO timestamp
            commencement_date = datetime.fromisoformat(commencement_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        elif len(commencement_date) > 10:
            # Has time component
            commencement_date = commencement_date[:10]
    except:
        commencement_date = datetime.now().strftime("%Y-%m-%d")
    
    # Seed
    seed_base_lease_clause_history(
        lease_id=lease_id,
        extracted_fields=extracted_data,
        lease_commencement_date=commencement_date,
        supabase_client=sb
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python seed_lease_history.py <lease_id>")
        print("\nExample:")
        print("  python seed_lease_history.py 123e4567-e89b-12d3-a456-426614174000")
        print("\nThis seeds the base lease (version 0) clause history for the Amendment Resolution Graph™")
        sys.exit(1)
    
    lease_id = sys.argv[1]
    seed_lease_from_id(lease_id)
