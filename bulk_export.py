"""
Bulk Export Functions for LeaseAI
Export multiple leases to a single CSV file
"""

import csv
import io
from typing import List, Dict
from datetime import datetime

def export_all_leases_to_yardi(leases: List[Dict], all_fields: Dict[str, List[Dict]]) -> bytes:
    """
    Export all leases to a single Yardi CSV
    
    Args:
        leases: List of lease metadata dicts
        all_fields: Dict mapping lease_id to list of extracted fields
        
    Returns:
        CSV bytes with all leases
    """
    from pms_export import YardiExporter
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=YardiExporter.YARDI_FIELDS)
    
    writer.writeheader()
    
    for lease in leases:
        lease_id = lease['id']
        fields = all_fields.get(lease_id, [])
        
        # Convert fields list to dict
        extracted_dict = {}
        for field in fields:
            field_name = field.get("field_name", "Unknown")
            extracted_dict[field_name] = {
                "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                "confidence": field.get("confidence", "MEDIUM")
            }
        
        # Map fields
        row = {
            'PropertyCode': YardiExporter._clean_value(lease.get('property_address', '')),
            'UnitCode': YardiExporter._extract_field(extracted_dict, 'Suite / Unit Number', ''),
            'TenantCode': YardiExporter._extract_field(extracted_dict, 'Tenant ID', ''),
            'TenantName': YardiExporter._extract_field(extracted_dict, 'Tenant Legal Name', ''),
            'LeaseStartDate': YardiExporter._format_date(
                YardiExporter._extract_field(extracted_dict, 'Lease Commencement Date', '')
            ),
            'LeaseEndDate': YardiExporter._format_date(
                YardiExporter._extract_field(extracted_dict, 'Lease Expiration Date', '')
            ),
            'RentAmount': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_dict, 'Base Rent Year 1 (monthly)', '')
            ),
            'RentFrequency': 'Monthly',
            'SecurityDeposit': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_dict, 'Security Deposit Amount', '')
            ),
            'SquareFootage': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_dict, 'Premises Square Footage (RSF)', '')
            ),
            'UseType': YardiExporter._extract_field(extracted_dict, 'Permitted Use', ''),
            'EscalationType': YardiExporter._extract_field(extracted_dict, 'Annual Escalation Type', ''),
            'EscalationRate': YardiExporter._extract_field(extracted_dict, 'Annual Escalation Rate or Cap', ''),
            'CAMCharges': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_dict, 'CAM / Operating Cost Charges', '')
            ),
            'CAMMethod': '',
            'RenewalOptions': YardiExporter._extract_field(extracted_dict, 'Number of Renewal Options', ''),
            'NoticeRequired': YardiExporter._extract_field(extracted_dict, 'Renewal Notice Deadline', ''),
            'LeaseType': YardiExporter._extract_field(extracted_dict, 'Lease Type', 'Commercial'),
            'Status': lease.get('status', 'ACTIVE')
        }
        
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue().encode('utf-8')


def export_all_leases_to_mri(leases: List[Dict], all_fields: Dict[str, List[Dict]]) -> bytes:
    """
    Export all leases to a single MRI CSV
    
    Args:
        leases: List of lease metadata dicts
        all_fields: Dict mapping lease_id to list of extracted fields
        
    Returns:
        CSV bytes with all leases
    """
    from pms_export import MRIExporter
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=MRIExporter.MRI_FIELDS)
    
    writer.writeheader()
    
    for lease in leases:
        lease_id = lease['id']
        fields = all_fields.get(lease_id, [])
        
        # Convert fields list to dict
        extracted_dict = {}
        for field in fields:
            field_name = field.get("field_name", "Unknown")
            extracted_dict[field_name] = {
                "value": field.get("reviewed_value") or field.get("raw_value") or "NOT FOUND",
                "confidence": field.get("confidence", "MEDIUM")
            }
        
        # Extract and calculate values
        base_rent = MRIExporter._extract_field(extracted_dict, 'Base Rent Year 1 (monthly)', '')
        base_rent_amount = MRIExporter._extract_amount(base_rent)
        square_footage = MRIExporter._extract_amount(
            MRIExporter._extract_field(extracted_dict, 'Premises Square Footage (RSF)', '0')
        )
        
        # Calculate rent PSF
        rent_psf = ''
        try:
            if base_rent_amount and square_footage:
                monthly_rent = float(base_rent_amount)
                sqft = float(square_footage)
                if sqft > 0:
                    rent_psf = f"{(monthly_rent * 12 / sqft):.2f}"
        except:
            pass
        
        # Calculate annual rent
        annual_rent = ''
        try:
            if base_rent_amount:
                annual_rent = str(float(base_rent_amount) * 12)
        except:
            pass
        
        # Map fields
        row = {
            'Property_ID': MRIExporter._clean_value(lease.get('property_address', '')),
            'Building_ID': MRIExporter._extract_field(extracted_dict, 'Building Name', ''),
            'Unit_ID': MRIExporter._extract_field(extracted_dict, 'Suite / Unit Number', ''),
            'Tenant_ID': MRIExporter._extract_field(extracted_dict, 'Tenant ID', ''),
            'Tenant_Name': MRIExporter._extract_field(extracted_dict, 'Tenant Legal Name', ''),
            'Lease_Start': MRIExporter._format_date(
                MRIExporter._extract_field(extracted_dict, 'Lease Commencement Date', '')
            ),
            'Lease_Expiration': MRIExporter._format_date(
                MRIExporter._extract_field(extracted_dict, 'Lease Expiration Date', '')
            ),
            'Monthly_Rent': base_rent_amount,
            'Annual_Rent': annual_rent,
            'Square_Feet': square_footage,
            'Rent_PSF': rent_psf,
            'Security_Deposit': MRIExporter._extract_amount(
                MRIExporter._extract_field(extracted_dict, 'Security Deposit Amount', '')
            ),
            'Lease_Type': MRIExporter._extract_field(extracted_dict, 'Lease Type', 'Gross'),
            'Use_Code': MRIExporter._extract_field(extracted_dict, 'Permitted Use', ''),
            'Escalation_Type': MRIExporter._extract_field(extracted_dict, 'Annual Escalation Type', ''),
            'Escalation_Percent': MRIExporter._extract_field(extracted_dict, 'Annual Escalation Rate or Cap', ''),
            'Operating_Expense_Base': MRIExporter._extract_amount(
                MRIExporter._extract_field(extracted_dict, 'Base Year for Operating Expenses', '')
            ),
            'Operating_Expense_Method': '',
            'Renewal_Option_Count': MRIExporter._extract_field(extracted_dict, 'Number of Renewal Options', ''),
            'Notice_Days': MRIExporter._parse_notice_days(
                MRIExporter._extract_field(extracted_dict, 'Renewal Notice Deadline', '')
            ),
            'Tenant_Improvement_Allowance': MRIExporter._extract_amount(
                MRIExporter._extract_field(extracted_dict, 'Tenant Improvement Allowance (TIA)', '')
            ),
            'Free_Rent_Months': MRIExporter._extract_field(extracted_dict, 'Free Rent Period', ''),
            'Status': lease.get('status', 'ACTIVE')
        }
        
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue().encode('utf-8')
