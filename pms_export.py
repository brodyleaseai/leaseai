"""
LeaseAI - Property Management System (PMS) Export Module
Export lease data to Yardi Voyager and MRI Software CSV formats
"""

import csv
import io
from datetime import datetime
from typing import Dict, List, Optional


class YardiExporter:
    """
    Export lease data to Yardi Voyager CSV format
    Yardi is the #1 property management system used by major REITs
    """
    
    # Yardi Voyager standard field mappings
    YARDI_FIELDS = [
        'PropertyCode',
        'UnitCode', 
        'TenantCode',
        'TenantName',
        'LeaseStartDate',
        'LeaseEndDate',
        'RentAmount',
        'RentFrequency',
        'SecurityDeposit',
        'SquareFootage',
        'UseType',
        'EscalationType',
        'EscalationRate',
        'CAMCharges',
        'CAMMethod',
        'RenewalOptions',
        'NoticeRequired',
        'LeaseType',
        'Status'
    ]
    
    @staticmethod
    def export_lease(lease_data: Dict, extracted_fields: Dict) -> bytes:
        """
        Export a single lease to Yardi CSV format
        
        Args:
            lease_data: Dictionary containing lease metadata from 'leases' table
            extracted_fields: Dictionary of extracted field values
            
        Returns:
            CSV file as bytes
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=YardiExporter.YARDI_FIELDS)
        
        writer.writeheader()
        
        # Map LeaseAI fields to Yardi fields
        row = {
            'PropertyCode': YardiExporter._clean_value(lease_data.get('property_address', '')),
            'UnitCode': YardiExporter._extract_field(extracted_fields, 'Unit Number', ''),
            'TenantCode': YardiExporter._extract_field(extracted_fields, 'Tenant ID', ''),
            'TenantName': YardiExporter._extract_field(extracted_fields, 'Tenant Legal Name', ''),
            'LeaseStartDate': YardiExporter._format_date(
                YardiExporter._extract_field(extracted_fields, 'Lease Start Date', '')
            ),
            'LeaseEndDate': YardiExporter._format_date(
                YardiExporter._extract_field(extracted_fields, 'Lease End Date', '')
            ),
            'RentAmount': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_fields, 'Base Rent', '')
            ),
            'RentFrequency': YardiExporter._extract_field(extracted_fields, 'Rent Payment Frequency', 'Monthly'),
            'SecurityDeposit': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_fields, 'Security Deposit', '')
            ),
            'SquareFootage': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_fields, 'Rentable Square Footage', '')
            ),
            'UseType': YardiExporter._extract_field(extracted_fields, 'Permitted Use', ''),
            'EscalationType': YardiExporter._extract_field(extracted_fields, 'Rent Escalation Type', ''),
            'EscalationRate': YardiExporter._extract_field(extracted_fields, 'Rent Escalation Percentage', ''),
            'CAMCharges': YardiExporter._extract_amount(
                YardiExporter._extract_field(extracted_fields, 'CAM Base Amount', '')
            ),
            'CAMMethod': YardiExporter._extract_field(extracted_fields, 'CAM Calculation Method', ''),
            'RenewalOptions': YardiExporter._extract_field(extracted_fields, 'Number of Renewal Options', ''),
            'NoticeRequired': YardiExporter._extract_field(extracted_fields, 'Non-Renewal Notice Period', ''),
            'LeaseType': YardiExporter._extract_field(extracted_fields, 'Lease Type', 'Commercial'),
            'Status': lease_data.get('status', 'ACTIVE')
        }
        
        writer.writerow(row)
        
        output.seek(0)
        return output.getvalue().encode('utf-8')
    
    @staticmethod
    def _extract_field(fields: Dict, field_name: str, default: str = '') -> str:
        """Extract field value from extracted_fields dictionary"""
        if field_name in fields:
            field_data = fields[field_name]
            if isinstance(field_data, dict):
                return str(field_data.get('value', default))
            return str(field_data)
        return default
    
    @staticmethod
    def _clean_value(value: str) -> str:
        """Clean and sanitize field values for CSV"""
        if not value:
            return ''
        return str(value).strip().replace('\n', ' ').replace('\r', '')
    
    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format date to Yardi standard: MM/DD/YYYY"""
        if not date_str:
            return ''
        
        try:
            # Try parsing various date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y']:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%m/%d/%Y')
                except ValueError:
                    continue
            
            # If no format matched, return original
            return date_str
        except Exception:
            return date_str
    
    @staticmethod
    def _extract_amount(amount_str: str) -> str:
        """Extract numeric amount from string (e.g., '$5,000/month' -> '5000')"""
        if not amount_str:
            return ''
        
        # Remove currency symbols, commas, and common suffixes
        cleaned = amount_str.replace('$', '').replace(',', '').strip()
        
        # Remove '/month', '/year', etc.
        for suffix in ['/month', '/year', '/mo', '/yr', 'per month', 'per year']:
            cleaned = cleaned.replace(suffix, '').strip()
        
        # Try to extract just the number
        try:
            # Find first continuous numeric value
            import re
            match = re.search(r'[\d.]+', cleaned)
            if match:
                return match.group()
        except Exception:
            pass
        
        return cleaned


class MRIExporter:
    """
    Export lease data to MRI Software CSV format
    MRI is a major property management system used by commercial real estate firms
    """
    
    # MRI standard field mappings
    MRI_FIELDS = [
        'Property_ID',
        'Building_ID',
        'Unit_ID',
        'Tenant_ID',
        'Tenant_Name',
        'Lease_Start',
        'Lease_Expiration',
        'Monthly_Rent',
        'Annual_Rent',
        'Square_Feet',
        'Rent_PSF',
        'Security_Deposit',
        'Lease_Type',
        'Use_Code',
        'Escalation_Type',
        'Escalation_Percent',
        'Operating_Expense_Base',
        'Operating_Expense_Method',
        'Renewal_Option_Count',
        'Notice_Days',
        'Tenant_Improvement_Allowance',
        'Free_Rent_Months',
        'Status'
    ]
    
    @staticmethod
    def export_lease(lease_data: Dict, extracted_fields: Dict) -> bytes:
        """
        Export a single lease to MRI CSV format
        
        Args:
            lease_data: Dictionary containing lease metadata from 'leases' table
            extracted_fields: Dictionary of extracted field values
            
        Returns:
            CSV file as bytes
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=MRIExporter.MRI_FIELDS)
        
        writer.writeheader()
        
        # Extract values
        base_rent = MRIExporter._extract_field(extracted_fields, 'Base Rent', '')
        base_rent_amount = MRIExporter._extract_amount(base_rent)
        square_footage = MRIExporter._extract_amount(
            MRIExporter._extract_field(extracted_fields, 'Rentable Square Footage', '0')
        )
        
        # Calculate rent per square foot
        rent_psf = ''
        try:
            if base_rent_amount and square_footage:
                monthly_rent = float(base_rent_amount)
                sqft = float(square_footage)
                if sqft > 0:
                    rent_psf = f"{(monthly_rent * 12 / sqft):.2f}"
        except Exception:
            pass
        
        # Calculate annual rent
        annual_rent = ''
        try:
            if base_rent_amount:
                annual_rent = str(float(base_rent_amount) * 12)
        except Exception:
            pass
        
        # Map LeaseAI fields to MRI fields
        row = {
            'Property_ID': MRIExporter._clean_value(lease_data.get('property_address', '')),
            'Building_ID': MRIExporter._extract_field(extracted_fields, 'Building Name', ''),
            'Unit_ID': MRIExporter._extract_field(extracted_fields, 'Unit Number', ''),
            'Tenant_ID': MRIExporter._extract_field(extracted_fields, 'Tenant ID', ''),
            'Tenant_Name': MRIExporter._extract_field(extracted_fields, 'Tenant Legal Name', ''),
            'Lease_Start': MRIExporter._format_date(
                MRIExporter._extract_field(extracted_fields, 'Lease Start Date', '')
            ),
            'Lease_Expiration': MRIExporter._format_date(
                MRIExporter._extract_field(extracted_fields, 'Lease End Date', '')
            ),
            'Monthly_Rent': base_rent_amount,
            'Annual_Rent': annual_rent,
            'Square_Feet': square_footage,
            'Rent_PSF': rent_psf,
            'Security_Deposit': MRIExporter._extract_amount(
                MRIExporter._extract_field(extracted_fields, 'Security Deposit', '')
            ),
            'Lease_Type': MRIExporter._extract_field(extracted_fields, 'Lease Type', 'Gross'),
            'Use_Code': MRIExporter._extract_field(extracted_fields, 'Permitted Use', ''),
            'Escalation_Type': MRIExporter._extract_field(extracted_fields, 'Rent Escalation Type', ''),
            'Escalation_Percent': MRIExporter._extract_field(extracted_fields, 'Rent Escalation Percentage', ''),
            'Operating_Expense_Base': MRIExporter._extract_amount(
                MRIExporter._extract_field(extracted_fields, 'Operating Expense Base Year Amount', '')
            ),
            'Operating_Expense_Method': MRIExporter._extract_field(extracted_fields, 'CAM Calculation Method', ''),
            'Renewal_Option_Count': MRIExporter._extract_field(extracted_fields, 'Number of Renewal Options', ''),
            'Notice_Days': MRIExporter._parse_notice_days(
                MRIExporter._extract_field(extracted_fields, 'Non-Renewal Notice Period', '')
            ),
            'Tenant_Improvement_Allowance': MRIExporter._extract_amount(
                MRIExporter._extract_field(extracted_fields, 'Tenant Improvement Allowance', '')
            ),
            'Free_Rent_Months': MRIExporter._extract_field(extracted_fields, 'Free Rent Period', ''),
            'Status': lease_data.get('status', 'ACTIVE')
        }
        
        writer.writerow(row)
        
        output.seek(0)
        return output.getvalue().encode('utf-8')
    
    @staticmethod
    def _extract_field(fields: Dict, field_name: str, default: str = '') -> str:
        """Extract field value from extracted_fields dictionary"""
        if field_name in fields:
            field_data = fields[field_name]
            if isinstance(field_data, dict):
                return str(field_data.get('value', default))
            return str(field_data)
        return default
    
    @staticmethod
    def _clean_value(value: str) -> str:
        """Clean and sanitize field values for CSV"""
        if not value:
            return ''
        return str(value).strip().replace('\n', ' ').replace('\r', '')
    
    @staticmethod
    def _format_date(date_str: str) -> str:
        """Format date to MRI standard: YYYY-MM-DD"""
        if not date_str:
            return ''
        
        try:
            # Try parsing various date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y']:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # If no format matched, return original
            return date_str
        except Exception:
            return date_str
    
    @staticmethod
    def _extract_amount(amount_str: str) -> str:
        """Extract numeric amount from string"""
        if not amount_str:
            return ''
        
        # Remove currency symbols, commas, and common suffixes
        cleaned = amount_str.replace('$', '').replace(',', '').strip()
        
        # Remove '/month', '/year', etc.
        for suffix in ['/month', '/year', '/mo', '/yr', 'per month', 'per year']:
            cleaned = cleaned.replace(suffix, '').strip()
        
        # Try to extract just the number
        try:
            import re
            match = re.search(r'[\d.]+', cleaned)
            if match:
                return match.group()
        except Exception:
            pass
        
        return cleaned
    
    @staticmethod
    def _parse_notice_days(notice_str: str) -> str:
        """Parse notice period string to days (e.g., '6 months' -> '180')"""
        if not notice_str:
            return ''
        
        notice_str = notice_str.lower()
        
        try:
            import re
            
            # Look for number
            match = re.search(r'(\d+)', notice_str)
            if not match:
                return ''
            
            number = int(match.group(1))
            
            # Check unit
            if 'month' in notice_str:
                return str(number * 30)
            elif 'day' in notice_str:
                return str(number)
            elif 'year' in notice_str:
                return str(number * 365)
            elif 'week' in notice_str:
                return str(number * 7)
            else:
                # Assume days if no unit
                return str(number)
        except Exception:
            return ''


def export_to_yardi(lease_data: Dict, extracted_fields: Dict) -> bytes:
    """
    Convenience function to export lease to Yardi format
    
    Args:
        lease_data: Lease metadata from database
        extracted_fields: Extracted field values
        
    Returns:
        CSV bytes
    """
    return YardiExporter.export_lease(lease_data, extracted_fields)


def export_to_mri(lease_data: Dict, extracted_fields: Dict) -> bytes:
    """
    Convenience function to export lease to MRI format
    
    Args:
        lease_data: Lease metadata from database
        extracted_fields: Extracted field values
        
    Returns:
        CSV bytes
    """
    return MRIExporter.export_lease(lease_data, extracted_fields)
