"""
LeaseAI - CAM Reconciliation Engine
Phase 2A & 2B: CAM Data Model, Extraction, Calculation, and Dispute Detection

This module handles:
- CAM provision extraction from leases
- CAM statement parsing and categorization
- CAM charge calculations based on lease terms
- Variance detection and dispute recommendations
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal


class CAMProvisionExtractor:
    """
    Extract CAM-specific provisions from lease documents
    Uses GPT-4o to identify CAM terms, exclusions, caps, and tenant share
    """
    
    CAM_CATEGORIES = [
        'UTILITIES', 'MAINTENANCE', 'REPAIRS', 'INSURANCE', 'PROPERTY_TAX',
        'MANAGEMENT_FEE', 'SECURITY', 'LANDSCAPING', 'SNOW_REMOVAL',
        'JANITORIAL', 'HVAC', 'ELEVATOR', 'PARKING', 'ADMIN', 'OTHER'
    ]
    
    @staticmethod
    def extract_cam_provisions(extracted_fields: Dict) -> Dict:
        """
        Extract CAM provisions from lease extracted fields
        
        Args:
            extracted_fields: Dictionary of all extracted lease fields
            
        Returns:
            Dictionary of CAM-specific provisions
        """
        provisions = {
            'cam_base_year': None,
            'cam_stop_amount': None,
            'cam_base_amount': None,
            'tenant_prorata_share': None,
            'tenant_square_footage': None,
            'building_square_footage': None,
            'has_cam_cap': False,
            'cam_cap_percentage': None,
            'cam_cap_amount': None,
            'excluded_items': [],
            'exclusions_description': None,
            'cam_payment_frequency': 'MONTHLY',
            'cam_reconciliation_deadline': None,
            'tenant_audit_right': False,
            'audit_deadline': None,
        }
        
        # Extract CAM base year
        if 'CAM Base Year' in extracted_fields:
            provisions['cam_base_year'] = CAMProvisionExtractor._extract_year(
                extracted_fields['CAM Base Year']
            )
        
        # Extract CAM stop amount
        if 'CAM Stop Amount' in extracted_fields:
            provisions['cam_stop_amount'] = CAMProvisionExtractor._extract_currency(
                extracted_fields['CAM Stop Amount']
            )
        
        # Calculate tenant pro-rata share from square footage
        tenant_sf = CAMProvisionExtractor._extract_number(
            extracted_fields.get('Premises Square Footage (RSF)', '')
        )
        building_sf = CAMProvisionExtractor._extract_number(
            extracted_fields.get('Building Square Footage', '')
        )
        
        if tenant_sf and building_sf:
            provisions['tenant_square_footage'] = tenant_sf
            provisions['building_square_footage'] = building_sf
            provisions['tenant_prorata_share'] = round(tenant_sf / building_sf, 6)
        
        # Extract CAM cap
        if 'CAM Escalation Cap' in extracted_fields:
            cap_text = extracted_fields['CAM Escalation Cap']
            if cap_text and 'N/A' not in str(cap_text).upper():
                provisions['has_cam_cap'] = True
                provisions['cam_cap_percentage'] = CAMProvisionExtractor._extract_percentage(cap_text)
        
        # Extract excluded items from CAM Exclusions field
        if 'CAM Exclusions' in extracted_fields:
            exclusions_text = str(extracted_fields['CAM Exclusions'])
            if exclusions_text and 'NOT FOUND' not in exclusions_text:
                provisions['exclusions_description'] = exclusions_text
                provisions['excluded_items'] = CAMProvisionExtractor._parse_exclusions(exclusions_text)
        
        # Extract tenant audit rights
        if 'Tenant Audit Right' in extracted_fields:
            audit_text = str(extracted_fields.get('Tenant Audit Right', '')).upper()
            provisions['tenant_audit_right'] = 'YES' in audit_text or 'ALLOWED' in audit_text
        
        return provisions
    
    @staticmethod
    def _extract_currency(value) -> Optional[float]:
        """Extract numeric currency value from string"""
        if isinstance(value, dict):
            value = value.get('value', '')
        
        value_str = str(value)
        # Remove currency symbols, commas, and extract number
        cleaned = re.sub(r'[^\d.]', '', value_str)
        try:
            return float(cleaned) if cleaned else None
        except:
            return None
    
    @staticmethod
    def _extract_number(value) -> Optional[int]:
        """Extract integer from string"""
        if isinstance(value, dict):
            value = value.get('value', '')
        
        value_str = str(value)
        cleaned = re.sub(r'[^\d]', '', value_str)
        try:
            return int(cleaned) if cleaned else None
        except:
            return None
    
    @staticmethod
    def _extract_year(value) -> Optional[int]:
        """Extract year from string"""
        if isinstance(value, dict):
            value = value.get('value', '')
        
        value_str = str(value)
        # Look for 4-digit year
        match = re.search(r'\b(19|20)\d{2}\b', value_str)
        return int(match.group(0)) if match else None
    
    @staticmethod
    def _extract_percentage(value) -> Optional[float]:
        """Extract percentage value"""
        if isinstance(value, dict):
            value = value.get('value', '')
        
        value_str = str(value)
        # Extract number before % sign
        match = re.search(r'(\d+\.?\d*)\s*%', value_str)
        if match:
            return float(match.group(1))
        # Or just extract the first number
        cleaned = re.sub(r'[^\d.]', '', value_str)
        try:
            return float(cleaned) if cleaned else None
        except:
            return None
    
    @staticmethod
    def _parse_exclusions(text: str) -> List[str]:
        """Parse CAM exclusions text into category list"""
        exclusions = []
        text_upper = text.upper()
        
        keywords = {
            'CAPITAL': 'CAPITAL_IMPROVEMENTS',
            'STRUCTURAL': 'STRUCTURAL_REPAIRS',
            'ROOF': 'ROOF_REPLACEMENT',
            'TAX': 'PROPERTY_TAX',
            'INSURANCE': 'LANDLORD_INSURANCE',
            'LEGAL': 'LEGAL_FEES',
            'MANAGEMENT FEE': 'MANAGEMENT_FEE',
            'DEPRECIATION': 'DEPRECIATION',
            'DEBT SERVICE': 'DEBT_SERVICE',
            'MORTGAGE': 'MORTGAGE_PAYMENTS'
        }
        
        for keyword, category in keywords.items():
            if keyword in text_upper:
                exclusions.append(category)
        
        return exclusions if exclusions else ['UNSPECIFIED']


class CAMStatementParser:
    """
    Parse landlord CAM statements (PDF or CSV) and categorize line items
    Uses GPT-4o for intelligent categorization
    """
    
    @staticmethod
    def parse_statement_text(statement_text: str) -> List[Dict]:
        """
        Parse CAM statement text into structured line items
        
        Args:
            statement_text: Raw text extracted from CAM statement
            
        Returns:
            List of dictionaries, each representing a line item
        """
        # This would use GPT-4o in production
        # For now, placeholder for line item extraction
        line_items = []
        
        # Pattern: Look for lines with amounts
        lines = statement_text.split('\n')
        for i, line in enumerate(lines):
            # Look for dollar amounts
            amount_match = re.search(r'\$\s*([\d,]+\.\d{2})', line)
            if amount_match:
                amount = float(amount_match.group(1).replace(',', ''))
                
                # Categorize based on keywords
                category = CAMStatementParser._categorize_line(line)
                
                line_items.append({
                    'line_number': i + 1,
                    'description': line.strip(),
                    'category': category,
                    'landlord_amount': amount
                })
        
        return line_items
    
    @staticmethod
    def _categorize_line(description: str) -> str:
        """Categorize a line item based on description keywords"""
        desc_upper = description.upper()
        
        # Mapping of keywords to categories
        category_keywords = {
            'UTILITIES': ['ELECTRIC', 'GAS', 'WATER', 'SEWER', 'UTILITY', 'POWER'],
            'MAINTENANCE': ['MAINTENANCE', 'REPAIR', 'FIX', 'UPKEEP'],
            'INSURANCE': ['INSURANCE', 'LIABILITY', 'COVERAGE'],
            'PROPERTY_TAX': ['TAX', 'PROPERTY TAX', 'REAL ESTATE TAX'],
            'MANAGEMENT_FEE': ['MANAGEMENT', 'ADMIN', 'MANAGEMENT FEE'],
            'SECURITY': ['SECURITY', 'GUARD', 'SURVEILLANCE'],
            'LANDSCAPING': ['LANDSCAPE', 'LAWN', 'GROUNDS', 'GARDEN'],
            'SNOW_REMOVAL': ['SNOW', 'ICE', 'WINTER', 'PLOW'],
            'JANITORIAL': ['JANITORIAL', 'CLEANING', 'CUSTODIAL'],
            'HVAC': ['HVAC', 'HEATING', 'COOLING', 'AIR CONDITIONING', 'VENTILATION'],
            'ELEVATOR': ['ELEVATOR', 'LIFT'],
            'PARKING': ['PARKING', 'LOT'],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in desc_upper for keyword in keywords):
                return category
        
        return 'OTHER'


class CAMCalculationEngine:
    """
    Calculate correct CAM charges based on lease provisions
    Detect variances and recommend disputes
    """
    
    MINOR_VARIANCE_THRESHOLD = 100  # $100
    MODERATE_VARIANCE_THRESHOLD = 500  # $500
    MAJOR_VARIANCE_THRESHOLD = 2000  # $2000
    
    @staticmethod
    def calculate_tenant_share(
        total_cam_charges: float,
        cam_provisions: Dict
    ) -> Dict:
        """
        Calculate tenant's correct CAM share based on lease provisions
        
        Args:
            total_cam_charges: Total building CAM charges
            cam_provisions: Dictionary of CAM provisions from lease
            
        Returns:
            Dictionary with calculation results
        """
        result = {
            'total_building_charges': total_cam_charges,
            'tenant_prorata_share': cam_provisions.get('tenant_prorata_share', 0),
            'calculated_tenant_share': 0,
            'cam_stop_applied': False,
            'cam_cap_applied': False,
            'calculations': []
        }
        
        # Step 1: Calculate base tenant share (pro-rata)
        prorata_share = cam_provisions.get('tenant_prorata_share', 0)
        tenant_share = total_cam_charges * prorata_share
        result['calculations'].append({
            'step': 'Pro-rata calculation',
            'formula': f'${total_cam_charges:,.2f} × {prorata_share:.4f}',
            'result': tenant_share
        })
        
        # Step 2: Apply CAM stop if applicable
        cam_stop = cam_provisions.get('cam_stop_amount')
        if cam_stop and tenant_share > cam_stop:
            overage = tenant_share - cam_stop
            result['cam_stop_applied'] = True
            result['calculations'].append({
                'step': 'CAM stop applied',
                'formula': f'${tenant_share:,.2f} - ${cam_stop:,.2f}',
                'result': overage
            })
            tenant_share = overage
        
        # Step 3: Apply CAM cap if applicable
        if cam_provisions.get('has_cam_cap'):
            cap_percentage = cam_provisions.get('cam_cap_percentage', 0)
            base_amount = cam_provisions.get('cam_base_amount', tenant_share)
            
            max_increase = base_amount * (cap_percentage / 100)
            capped_amount = base_amount + max_increase
            
            if tenant_share > capped_amount:
                result['cam_cap_applied'] = True
                result['calculations'].append({
                    'step': f'CAM cap applied ({cap_percentage}%)',
                    'formula': f'${base_amount:,.2f} + (${base_amount:,.2f} × {cap_percentage}%)',
                    'result': capped_amount
                })
                tenant_share = capped_amount
        
        result['calculated_tenant_share'] = round(tenant_share, 2)
        return result
    
    @staticmethod
    def analyze_line_items(
        line_items: List[Dict],
        cam_provisions: Dict
    ) -> List[Dict]:
        """
        Analyze CAM line items and flag issues
        
        Args:
            line_items: List of CAM line items from statement
            cam_provisions: CAM provisions from lease
            
        Returns:
            Line items with analysis flags and recommendations
        """
        analyzed_items = []
        excluded_categories = cam_provisions.get('excluded_items', [])
        
        for item in line_items:
            analyzed = item.copy()
            analyzed['is_excluded'] = False
            analyzed['is_disputed'] = False
            analyzed['dispute_reason'] = None
            analyzed['recommended_action'] = 'ACCEPT'
            
            # Check if category is excluded per lease
            category = item.get('category', '')
            if any(excl in category for excl in excluded_categories):
                analyzed['is_excluded'] = True
                analyzed['is_disputed'] = True
                analyzed['dispute_reason'] = f'{category} is excluded per lease terms'
                analyzed['recommended_action'] = 'CHALLENGE'
                analyzed['calculated_amount'] = 0
                analyzed['variance_amount'] = item.get('landlord_amount', 0)
            
            analyzed_items.append(analyzed)
        
        return analyzed_items
    
    @staticmethod
    def detect_discrepancies(
        landlord_total: float,
        calculated_total: float,
        line_items: List[Dict]
    ) -> Dict:
        """
        Detect and categorize CAM discrepancies
        
        Args:
            landlord_total: Total charged by landlord
            calculated_total: Correct amount per lease terms
            line_items: Analyzed line items
            
        Returns:
            Discrepancy analysis with severity and recommendations
        """
        variance = landlord_total - calculated_total
        variance_pct = (variance / landlord_total * 100) if landlord_total > 0 else 0
        
        # Categorize severity
        if abs(variance) < CAMCalculationEngine.MINOR_VARIANCE_THRESHOLD:
            severity = 'MINOR'
            recommendation = 'ACCEPT'
        elif abs(variance) < CAMCalculationEngine.MODERATE_VARIANCE_THRESHOLD:
            severity = 'MODERATE'
            recommendation = 'REQUEST_CLARIFICATION'
        elif abs(variance) < CAMCalculationEngine.MAJOR_VARIANCE_THRESHOLD:
            severity = 'MAJOR'
            recommendation = 'CHALLENGE'
        else:
            severity = 'CRITICAL'
            recommendation = 'CHALLENGE_IMMEDIATELY'
        
        # Find disputed line items
        disputed_items = [item for item in line_items if item.get('is_disputed')]
        total_disputed = sum(item.get('variance_amount', 0) for item in disputed_items)
        
        return {
            'landlord_total': landlord_total,
            'calculated_total': calculated_total,
            'variance_amount': variance,
            'variance_percentage': variance_pct,
            'severity': severity,
            'recommendation': recommendation,
            'disputed_line_items_count': len(disputed_items),
            'total_disputed_amount': total_disputed,
            'potential_savings': max(0, variance) if variance > 0 else 0
        }


class CAMDisputeLetter:
    """
    Generate professional dispute letter to landlord
    """
    
    @staticmethod
    def generate_dispute_letter(
        lease_data: Dict,
        reconciliation_data: Dict,
        disputed_items: List[Dict]
    ) -> str:
        """
        Generate a professional CAM dispute letter
        
        Args:
            lease_data: Lease information
            reconciliation_data: CAM reconciliation results
            disputed_items: List of disputed line items
            
        Returns:
            Formatted dispute letter as string
        """
        today = datetime.now().strftime('%B %d, %Y')
        
        letter = f"""
[Tenant Letterhead]

{today}

[Landlord Name and Address]

Re: CAM Reconciliation Dispute - {lease_data.get('property_address', 'Property')}
    Lease Dated: {lease_data.get('lease_commencement_date', '[Date]')}
    Reconciliation Year: {reconciliation_data.get('reconciliation_year', '[Year]')}

Dear [Landlord],

We are in receipt of the Common Area Maintenance (CAM) reconciliation statement dated {reconciliation_data.get('statement_date', '[Date]')} for the above-referenced property. After careful review of the statement and comparison with our lease terms, we have identified discrepancies that require clarification and adjustment.

SUMMARY OF DISCREPANCY:
- Landlord's Billed Amount: ${reconciliation_data.get('landlord_total_charges', 0):,.2f}
- Correct Amount Per Lease: ${reconciliation_data.get('calculated_total_charges', 0):,.2f}
- Variance (Overcharge): ${reconciliation_data.get('variance_amount', 0):,.2f}

SPECIFIC ISSUES:

"""
        
        for i, item in enumerate(disputed_items, 1):
            letter += f"{i}. {item.get('category', 'Category')}: {item.get('description', '')}\n"
            letter += f"   Billed: ${item.get('landlord_amount', 0):,.2f}\n"
            letter += f"   Issue: {item.get('dispute_reason', '')}\n"
            letter += f"   Adjustment Required: ${item.get('variance_amount', 0):,.2f}\n\n"
        
        letter += """
LEASE TERMS SUPPORTING OUR POSITION:

Per Section [X] of the Lease Agreement, CAM charges are subject to the following limitations:
- [List relevant lease provisions]
- [Exclusions]
- [Caps]

REQUESTED ACTION:

We respectfully request that you review the above discrepancies and issue a revised CAM reconciliation statement reflecting the correct charges of $[AMOUNT]. We also request a credit of $[VARIANCE] to be applied to our next monthly rent payment.

Per our lease terms, we reserve the right to conduct a formal audit of the CAM charges should this matter not be resolved within [X] days.

We appreciate your prompt attention to this matter and look forward to your response.

Sincerely,

[Tenant Name]
[Title]
[Contact Information]
"""
        
        return letter


# Convenience functions
def extract_cam_provisions_from_lease(extracted_fields: Dict) -> Dict:
    """Quick extraction of CAM provisions"""
    return CAMProvisionExtractor.extract_cam_provisions(extracted_fields)


def parse_cam_statement(statement_text: str) -> List[Dict]:
    """Quick parsing of CAM statement"""
    return CAMStatementParser.parse_statement_text(statement_text)


def calculate_cam_charges(total_charges: float, provisions: Dict) -> Dict:
    """Quick CAM calculation"""
    return CAMCalculationEngine.calculate_tenant_share(total_charges, provisions)


def analyze_line_items(line_items: List[Dict], cam_provisions: Dict) -> List[Dict]:
    """Quick line item analysis"""
    return CAMCalculationEngine.analyze_line_items(line_items, cam_provisions)


def detect_discrepancies(landlord_total: float, calculated_total: float, line_items: List[Dict]) -> Dict:
    """Quick discrepancy detection"""
    return CAMCalculationEngine.detect_discrepancies(landlord_total, calculated_total, line_items)


def generate_cam_dispute_letter(lease_data: Dict, reconciliation: Dict, items: List[Dict]) -> str:
    """Quick dispute letter generation"""
    return CAMDisputeLetter.generate_dispute_letter(lease_data, reconciliation, items)
