"""
Test script for PMS export functionality
Tests Yardi and MRI export with sample data
"""

from pms_export import export_to_yardi, export_to_mri
import json

# Sample lease data
lease_data = {
    "id": "test-123",
    "property_address": "123 Main Street, Vancouver BC",
    "status": "APPROVED",
    "created_at": "2024-01-15T10:00:00Z"
}

# Sample extracted fields
extracted_fields = {
    "Tenant Legal Name": {"value": "Acme Corporation", "confidence": "HIGH"},
    "Tenant ID": {"value": "ACME001", "confidence": "HIGH"},
    "Unit Number": {"value": "Suite 200", "confidence": "HIGH"},
    "Lease Start Date": {"value": "2024-01-01", "confidence": "HIGH"},
    "Lease End Date": {"value": "2029-12-31", "confidence": "HIGH"},
    "Base Rent": {"value": "$5,000/month", "confidence": "HIGH"},
    "Rent Payment Frequency": {"value": "Monthly", "confidence": "HIGH"},
    "Security Deposit": {"value": "$10,000", "confidence": "HIGH"},
    "Rentable Square Footage": {"value": "2,500", "confidence": "HIGH"},
    "Permitted Use": {"value": "Office", "confidence": "HIGH"},
    "Rent Escalation Type": {"value": "Fixed", "confidence": "MEDIUM"},
    "Rent Escalation Percentage": {"value": "3%", "confidence": "MEDIUM"},
    "CAM Base Amount": {"value": "$500/month", "confidence": "MEDIUM"},
    "CAM Calculation Method": {"value": "Pro Rata", "confidence": "MEDIUM"},
    "Number of Renewal Options": {"value": "2", "confidence": "HIGH"},
    "Non-Renewal Notice Period": {"value": "6 months", "confidence": "HIGH"},
    "Lease Type": {"value": "Net Lease", "confidence": "HIGH"},
    "Building Name": {"value": "Main Street Tower", "confidence": "HIGH"},
    "Operating Expense Base Year Amount": {"value": "$12,000", "confidence": "MEDIUM"},
    "Tenant Improvement Allowance": {"value": "$25,000", "confidence": "MEDIUM"},
    "Free Rent Period": {"value": "2", "confidence": "HIGH"}
}

def test_yardi_export():
    """Test Yardi CSV export"""
    print("Testing Yardi Export...")
    print("=" * 60)
    
    try:
        csv_data = export_to_yardi(lease_data, extracted_fields)
        csv_str = csv_data.decode('utf-8')
        
        print("✅ Yardi export successful!")
        print("\nGenerated CSV:")
        print(csv_str)
        
        # Write to file
        with open('test_yardi_export.csv', 'wb') as f:
            f.write(csv_data)
        print("\n✅ Saved to: test_yardi_export.csv")
        
    except Exception as e:
        print(f"❌ Yardi export failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")

def test_mri_export():
    """Test MRI CSV export"""
    print("Testing MRI Export...")
    print("=" * 60)
    
    try:
        csv_data = export_to_mri(lease_data, extracted_fields)
        csv_str = csv_data.decode('utf-8')
        
        print("✅ MRI export successful!")
        print("\nGenerated CSV:")
        print(csv_str)
        
        # Write to file
        with open('test_mri_export.csv', 'wb') as f:
            f.write(csv_data)
        print("\n✅ Saved to: test_mri_export.csv")
        
    except Exception as e:
        print(f"❌ MRI export failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PMS EXPORT TEST SUITE")
    print("=" * 60 + "\n")
    
    test_yardi_export()
    test_mri_export()
    
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
