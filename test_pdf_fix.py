"""
Test script to verify PDF layout fix with long field values.
"""
from lease_report import generate_lease_abstract_pdf

# Test with realistic long field values that were causing overflow
test_lease = {
    "property_address": "877 Goldstream Avenue, Victoria, BC, V9B 2X8",
    "tenant_name": "1392180 BC Ltd. (Rhino Coffee House)"
}

test_fields = {
    "permitted_use": {
        "value": "Coffee shop under the name and style of Rhino Coffee House",
        "confidence": "HIGH"
    },
    "tenant_insurance_requirements": {
        "value": "commercial general liability insurance including coverage for death, personal injury liability, contractual liability, non-owned automobile liability, employers' liability, and owners' and contractors' protective insurance coverage",
        "confidence": "HIGH"
    },
    "signage_rights": {
        "value": "Tenant will not erect or place, or permit to be erected or placed, or maintain any signs of any nature or kind whatsoever either on the exterior walls of the Premises or on the walls of the Clubhouse, if applicable, or elsewhere in the Clubhouse; nor will the Tenant erect or place, or permit to be erected or placed...",
        "confidence": "MEDIUM"
    },
    "force_majeure_clause": {
        "value": "Despite anything contained in this Lease to the contrary, if the Landlord or the Tenant is, in good faith, delayed or prevented from doing anything required by this Lease because of a strike, labour trouble, inability to obtain materials or services, power failure, restrictive government laws, orders, decrees, or regulations...",
        "confidence": "MEDIUM"
    },
    "holdover_provision": {
        "value": "tenant from month to month, at a monthly rent payable in advance on the first day of each month equal to the sum of: (a) one-tenth of the Basic Rent payable during the last 12 months of the Term; and (b) one-tenth of the Additional Rent, payable hereunder during the last 12 months of the Term",
        "confidence": "HIGH"
    },
    "estoppel_certificate_obligation": {
        "value": "Tenant will deliver, in a form supplied by the Landlord, an estoppel certificate to any proposed mortgagee, assignee, lessee, or purchaser, or to the Landlord, confirming the basic terms of the Lease and stating any modification or defaults under the Lease by either party and such other information as reasonably requested",
        "confidence": "HIGH"
    },
    "dispute_resolution_mechanism": {
        "value": "either the Landlord or the Tenant may, by notice in writing to the other, require that such fair market rental value be determined by arbitration conducted by a single arbitrator pursuant to the Arbitration Act (British Columbia).",
        "confidence": "HIGH"
    },
    "demolition_redevelopment_clause": {
        "value": "In the event of the substantial destruction of the Clubhouse (whether or not the Premises are damaged), the Landlord will, at its option to be exercised within 90 days after the occurrence of such damage or destruction, by notice in writing to the Tenant, have the right to terminate this Lease, and upon the giving of such notice...",
        "confidence": "MEDIUM"
    },
    "hazardous_materials_clause": {
        "value": "Tenant will not use or permit to be used the Premises for the sale, storage, manufacture, disposal, handling, treatment, generation, use, transport, remediation or any other dealing with any Hazardous Substances without the prior written consent of the Landlord",
        "confidence": "HIGH"
    },
    # Short fields for variety
    "lease_commencement_date": {"value": "April 1, 2024", "confidence": "HIGH"},
    "lease_expiration_date": {"value": "March 31, 2027", "confidence": "HIGH"},
    "base_rent_year_1": {"value": "$1,923.33/month", "confidence": "HIGH"},
    "base_rent_year_2": {"value": "$1,923.33/month", "confidence": "HIGH"},
    "base_rent_year_3": {"value": "$1,923.33/month", "confidence": "HIGH"},
    "lease_term_months": {"value": "36 months", "confidence": "HIGH"},
    "security_deposit_amount": {"value": "$1,923.33", "confidence": "HIGH"},
    "premises_square_footage": {"value": "1,154 sq ft", "confidence": "HIGH"},
    "number_of_renewal_options": {"value": "2", "confidence": "HIGH"},
    "renewal_option_term_length": {"value": "5 years", "confidence": "HIGH"},
    "parking_number_of_stalls": {"value": "2-3 designated 15-minute parking spaces", "confidence": "HIGH"},
    "tenant_improvement_allowance": {"value": "$75,000.00", "confidence": "HIGH"},
    # Some NOT FOUND fields
    "building_class": {"value": "NOT FOUND", "confidence": "LOW"},
    "cam_exclusions": {"value": "NOT FOUND", "confidence": "LOW"},
    "expansion_option": {"value": "NOT FOUND", "confidence": "LOW"},
}

print("Generating test PDF with long field values...")
pdf_bytes = generate_lease_abstract_pdf(test_lease, test_fields)

output_file = "test_pdf_fixed.pdf"
with open(output_file, "wb") as f:
    f.write(pdf_bytes)

print(f"✅ PDF generated successfully: {output_file}")
print(f"   File size: {len(pdf_bytes):,} bytes")
print("\n📄 Test includes:")
print("   - Multiple long field values (150+ characters)")
print("   - Short field values")
print("   - NOT FOUND fields")
print("   - All confidence levels (HIGH, MEDIUM, LOW)")
print("\n🔍 Please open the PDF and verify:")
print("   1. Long values wrap correctly within their column")
print("   2. No text overlaps into the confidence column")
print("   3. Confidence indicators are aligned and visible")
print("   4. Table looks professional and readable")
