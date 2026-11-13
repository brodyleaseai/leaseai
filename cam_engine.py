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
            extracted_fields.get('Building Square Footage')
            or extracted_fields.get('Building Total Square Footage', '')
        )
        
        if tenant_sf and building_sf:
            provisions['tenant_square_footage'] = tenant_sf
            provisions['building_square_footage'] = building_sf
            provisions['tenant_prorata_share'] = round(tenant_sf / building_sf, 6)
        
        # Extract CAM cap — field names vary by extraction prompt version
        for cap_field in (
            'CAM Escalation Cap',
            'CAM Annual Increase Cap (%)',
            'CAM Annual Increase Cap',
        ):
            if cap_field not in extracted_fields:
                continue
            cap_text = extracted_fields[cap_field]
            if cap_text and 'N/A' not in str(cap_text).upper() and 'NOT FOUND' not in str(cap_text).upper():
                provisions['has_cam_cap'] = True
                provisions['cam_cap_percentage'] = CAMProvisionExtractor._extract_percentage(cap_text)
                break

        if 'Base Year for Operating Expenses' in extracted_fields and not provisions['cam_base_year']:
            provisions['cam_base_year'] = CAMProvisionExtractor._extract_year(
                extracted_fields['Base Year for Operating Expenses']
            )
        
        # Extract excluded items from CAM Exclusions field
        if 'CAM Exclusions' in extracted_fields:
            exclusions_text = str(extracted_fields['CAM Exclusions'])
            if exclusions_text and 'NOT FOUND' not in exclusions_text:
                provisions['exclusions_description'] = exclusions_text
                provisions['excluded_items'] = CAMProvisionExtractor._parse_exclusions(exclusions_text)
        
        # Extract tenant audit rights (prompt versions use Right and Rights)
        for audit_field in ('Tenant Audit Right', 'Tenant Audit Rights'):
            if audit_field not in extracted_fields:
                continue
            audit_text = CAMProvisionExtractor._field_text(extracted_fields.get(audit_field)).upper()
            if not audit_text or 'NOT FOUND' in audit_text:
                continue
            provisions['tenant_audit_right'] = (
                'YES' in audit_text or 'ALLOWED' in audit_text or audit_text == 'TRUE'
            )
            break

        for deadline_field in (
            'Audit Deadline',
            'CAM Audit Deadline',
            'Tenant Audit Deadline',
        ):
            if deadline_field not in extracted_fields:
                continue
            deadline = CAMProvisionExtractor._field_text(extracted_fields.get(deadline_field))
            if deadline and 'NOT FOUND' not in deadline.upper() and deadline.upper() != 'N/A':
                provisions['audit_deadline'] = deadline
                break
        if not provisions.get('audit_deadline'):
            for key, raw in extracted_fields.items():
                if 'AUDIT DEADLINE' not in str(key).upper():
                    continue
                deadline = CAMProvisionExtractor._field_text(raw)
                if deadline and 'NOT FOUND' not in deadline.upper():
                    provisions['audit_deadline'] = deadline
                    break

        if not provisions.get('cam_base_amount'):
            for amount_field in ('CAM Base Amount', 'CAM Base Amount (tenant share)'):
                if amount_field not in extracted_fields:
                    continue
                amount = CAMProvisionExtractor._extract_currency(extracted_fields.get(amount_field))
                if amount:
                    provisions['cam_base_amount'] = amount
                    break
        if not provisions.get('cam_base_amount'):
            for key, raw in extracted_fields.items():
                blob = CAMProvisionExtractor._field_text(raw)
                if 'CAM BASE AMOUNT' in f"{key} {blob}".upper():
                    amount = CAMProvisionExtractor._extract_currency(blob)
                    if amount:
                        provisions['cam_base_amount'] = amount
                        break
        
        return provisions

    @staticmethod
    def _field_text(value) -> str:
        if isinstance(value, dict):
            value = (
                value.get('reviewed_value')
                or value.get('raw_value')
                or value.get('value')
                or ''
            )
        return str(value or '').strip()
    
    @staticmethod
    def _extract_currency(value) -> Optional[float]:
        """Extract numeric currency value from string"""
        if isinstance(value, dict):
            value = value.get('value', '')
        
        value_str = str(value)
        match = re.search(r'\$\s*([\d,]+(?:\.\d{1,2})?)', value_str)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        match = re.search(r'\b(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?)\b', value_str)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        cleaned = re.sub(r'[^\d.]', '', value_str)
        try:
            return float(cleaned) if cleaned else None
        except (TypeError, ValueError):
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
            'CAPITAL_IMPROVEMENTS': ['CAPITAL IMPROVEMENT', 'ROOF REPLACEMENT', 'CAPITAL'],
            'STRUCTURAL_REPAIRS': ['STRUCTURAL'],
            'DEBT_SERVICE': ['DEBT SERVICE', 'MORTGAGE'],
            'DEPRECIATION': ['DEPRECIATION'],
            'LEGAL_FEES': ['LEGAL FEE', 'EVICTION'],
            'UTILITIES': ['ELECTRIC', 'GAS', 'WATER', 'SEWER', 'UTILITY', 'POWER'],
            'INSURANCE': ['INSURANCE', 'LIABILITY', 'COVERAGE'],
            'PROPERTY_TAX': ['PROPERTY TAX', 'REAL ESTATE TAX'],
            'MANAGEMENT_FEE': ['MANAGEMENT FEE', 'MANAGEMENT'],
            'SECURITY': ['SECURITY', 'GUARD', 'SURVEILLANCE'],
            'LANDSCAPING': ['LANDSCAPE', 'LAWN', 'GROUNDS', 'GARDEN'],
            'SNOW_REMOVAL': ['SNOW', 'ICE', 'WINTER', 'PLOW'],
            'JANITORIAL': ['JANITORIAL', 'CLEANING', 'CUSTODIAL'],
            'HVAC': ['HVAC', 'HEATING', 'COOLING', 'AIR CONDITIONING', 'VENTILATION'],
            'ELEVATOR': ['ELEVATOR', 'LIFT'],
            'PARKING': ['PARKING', 'LOT'],
            'MAINTENANCE': ['MAINTENANCE', 'REPAIR', 'FIX', 'UPKEEP'],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in desc_upper for keyword in keywords):
                return category
        
        return 'OTHER'

    NUMBERED_AMOUNT = re.compile(
        r'^\s*(\d+)\s+(.+?)\s+\$\s*([\d,]+\.\d{2})\s*$'
    )
    CATEGORY_SUFFIXES = [
        ('Capital improvements', 'CAPITAL_IMPROVEMENTS'),
        ('Structural repairs', 'STRUCTURAL_REPAIRS'),
        ('Legal fees', 'LEGAL_FEES'),
        ('Debt service', 'DEBT_SERVICE'),
        ('Depreciation', 'DEPRECIATION'),
        ('Management fee', 'MANAGEMENT_FEE'),
        ('Snow removal', 'SNOW_REMOVAL'),
        ('Property tax', 'PROPERTY_TAX'),
        ('Utilities', 'UTILITIES'),
        ('Janitorial', 'JANITORIAL'),
        ('Landscaping', 'LANDSCAPING'),
        ('Maintenance', 'MAINTENANCE'),
        ('Insurance', 'INSURANCE'),
        ('Elevator', 'ELEVATOR'),
        ('Parking', 'PARKING'),
        ('Security', 'SECURITY'),
        ('HVAC', 'HVAC'),
        ('Admin', 'ADMIN'),
        ('Other', 'OTHER'),
    ]

    @staticmethod
    def parse_numbered_line_items(statement_text: str) -> List[Dict]:
        """Keep every numbered '$X,XXX.XX' row, including excluded capital/debt lines."""
        items = []
        seen = set()
        for raw in (statement_text or "").splitlines():
            match = CAMStatementParser.NUMBERED_AMOUNT.match(raw)
            if not match:
                continue
            line_number = int(match.group(1))
            if line_number in seen:
                continue
            seen.add(line_number)
            remainder = match.group(2).strip()
            amount = float(match.group(3).replace(',', ''))
            category = None
            description = remainder
            for label, code in CAMStatementParser.CATEGORY_SUFFIXES:
                suffix = f" {label}"
                if remainder.lower().endswith(suffix.lower()):
                    description = remainder[: -len(suffix)].strip()
                    category = code
                    break
            if not category:
                category = CAMStatementParser._categorize_line(remainder)
            items.append({
                'line_number': line_number,
                'description': description,
                'category': category,
                'amount': amount,
                'landlord_amount': amount,
                'frequency': 'Annual',
                'notes': None,
            })
        items.sort(key=lambda item: item['line_number'])
        return items

    @staticmethod
    def extract_statement_totals(statement_text: str) -> Dict:
        """Pull year, statement date, building total, and tenant share from statement text."""
        text = statement_text or ""
        totals: Dict = {}

        year_match = re.search(r'(?:Calendar Year|Reconciliation Year|Period Year)\s+(\d{4})', text, re.I)
        if not year_match:
            year_match = re.search(r'\b(20\d{2})\s+annual', text, re.I)
        if year_match:
            totals['period_year'] = int(year_match.group(1))

        date_match = re.search(
            r'Statement Date:\s*([A-Za-z]+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})',
            text,
            re.I,
        )
        if date_match:
            totals['statement_date'] = CAMStatementParser._parse_date_string(date_match.group(1))

        building_match = re.search(
            r'Total Building(?: CAM)? Charges[^\n$]*\$\s*([\d,]+\.\d{2})',
            text,
            re.I,
        )
        if building_match:
            totals['total_building_charges'] = float(building_match.group(1).replace(',', ''))

        share_match = re.search(
            r'Tenant Share Billed[^\n$]*\$\s*([\d,]+\.\d{2})',
            text,
            re.I,
        )
        if share_match:
            totals['tenant_share_billed'] = float(share_match.group(1).replace(',', ''))

        return totals

    @staticmethod
    def _parse_date_string(value: str) -> Optional[str]:
        if not value:
            return None
        value = value.strip()
        for fmt in ('%Y-%m-%d', '%B %d, %Y', '%b %d, %Y'):
            try:
                return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return value

    @staticmethod
    def assemble_parsed_statement(statement_text: str, gpt_result: Optional[Dict] = None) -> Dict:
        """Prefer numbered rows from the PDF so GPT cannot drop excluded charges."""
        gpt_result = gpt_result or {}
        numbered = CAMStatementParser.parse_numbered_line_items(statement_text)
        gpt_items = gpt_result.get('line_items') or []
        gpt_by_number = {}
        for item in gpt_items:
            try:
                gpt_by_number[int(item.get('line_number'))] = item
            except (TypeError, ValueError):
                continue

        if numbered:
            line_items = []
            for item in numbered:
                gpt_item = gpt_by_number.get(item['line_number'], {})
                notes = gpt_item.get('notes') or item.get('notes')
                category = item.get('category') or gpt_item.get('category') or 'OTHER'
                if category == 'OTHER' and gpt_item.get('category'):
                    category = gpt_item['category']
                amount = item['amount']
                line_items.append({
                    'line_number': item['line_number'],
                    'description': item['description'],
                    'category': category,
                    'amount': amount,
                    'landlord_amount': amount,
                    'frequency': gpt_item.get('frequency') or 'Annual',
                    'notes': notes,
                })
            parsing_method = 'numbered+gpt' if gpt_items else 'numbered'
        else:
            line_items = []
            for item in gpt_items:
                amount = item.get('amount', item.get('landlord_amount', 0)) or 0
                line_items.append({
                    **item,
                    'amount': amount,
                    'landlord_amount': amount,
                })
            parsing_method = gpt_result.get('parsing_method') or 'gpt'

        totals = CAMStatementParser.extract_statement_totals(statement_text)
        numbered_sum = round(sum(item.get('amount') or 0 for item in line_items), 2)
        building_total = (
            totals.get('total_building_charges')
            or gpt_result.get('total_building_charges')
            or numbered_sum
        )
        tenant_share = totals.get('tenant_share_billed') or gpt_result.get('tenant_share_billed')

        return {
            'statement_date': gpt_result.get('statement_date') or totals.get('statement_date'),
            'period_year': gpt_result.get('period_year') or totals.get('period_year'),
            'total_building_charges': building_total,
            'tenant_share_billed': tenant_share,
            'line_items': line_items,
            'total_line_items': len(line_items),
            'parsing_method': parsing_method,
        }

    @staticmethod
    def defaults_from_parsed_statement(parsed: Dict) -> Dict:
        """Values for the Step 2 reconciliation fields."""
        statement_date = parsed.get('statement_date')
        parsed_date = None
        if statement_date:
            try:
                parsed_date = datetime.strptime(str(statement_date)[:10], '%Y-%m-%d').date()
            except ValueError:
                iso = CAMStatementParser._parse_date_string(str(statement_date))
                if iso and iso != str(statement_date):
                    parsed_date = datetime.strptime(iso, '%Y-%m-%d').date()

        year = parsed.get('period_year')
        if not year and parsed_date:
            year = parsed_date.year - 1 if parsed_date.month <= 3 else parsed_date.year

        return {
            'recon_year': int(year) if year else datetime.now().year - 1,
            'statement_date': parsed_date or datetime.now().date(),
            'landlord_total': float(parsed.get('total_building_charges') or 0),
            'tenant_share_billed': float(parsed.get('tenant_share_billed') or 0),
        }


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
        cam_provisions = cam_provisions or {}
        total_cam_charges = CAMCalculationEngine._as_float(total_cam_charges, 0.0)
        prorata_share = CAMCalculationEngine._prorata_share(cam_provisions)

        result = {
            'total_building_charges': total_cam_charges,
            'tenant_prorata_share': prorata_share,
            'calculated_tenant_share': 0,
            'cam_stop_applied': False,
            'cam_cap_applied': False,
            'calculations': []
        }
        
        # Step 1: Calculate base tenant share (pro-rata)
        tenant_share = total_cam_charges * prorata_share
        result['calculations'].append({
            'step': 'Pro-rata calculation',
            'formula': f'${total_cam_charges:,.2f} × {prorata_share:.4f}',
            'result': tenant_share
        })
        
        # Step 2: Apply CAM stop if applicable
        cam_stop = CAMCalculationEngine._as_float(cam_provisions.get('cam_stop_amount'), None)
        if cam_stop and tenant_share > cam_stop:
            overage = tenant_share - cam_stop
            result['cam_stop_applied'] = True
            result['calculations'].append({
                'step': 'CAM stop applied',
                'formula': f'${tenant_share:,.2f} - ${cam_stop:,.2f}',
                'result': overage
            })
            tenant_share = overage
        
        # Step 3: Apply CAM cap against the base-year amount, never against this year's bill.
        cap_percentage = CAMCalculationEngine._as_float(
            cam_provisions.get('cam_cap_percentage'), None
        )
        if not cap_percentage and cam_provisions.get('has_cam_cap'):
            cap_percentage = None
        if cap_percentage:
            base_amount = CAMCalculationEngine._as_float(
                cam_provisions.get('cam_base_amount'), None
            )
            if base_amount is None:
                result['calculations'].append({
                    'step': 'CAM cap skipped',
                    'formula': f'{cap_percentage}% cap is in the lease but no CAM Base Amount was stored',
                    'result': tenant_share
                })
            else:
                capped_amount = base_amount + (base_amount * (cap_percentage / 100))
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
    def reconcile_cam_charges(
        landlord_total: float,
        tenant_share_billed: float,
        cam_provisions: Dict,
        line_items: Optional[List[Dict]] = None,
    ) -> Dict:
        """Tenant share after removing lease-excluded lines, then applying stop/cap."""
        cam_provisions = cam_provisions or {}
        landlord_total = CAMCalculationEngine._as_float(landlord_total, 0.0)
        tenant_share_billed = CAMCalculationEngine._as_float(tenant_share_billed, 0.0)
        analyzed = CAMCalculationEngine.analyze_line_items(line_items or [], cam_provisions)
        excluded_building = round(sum(
            item.get('amount') or 0 for item in analyzed if item.get('should_challenge')
        ), 2)
        allowable_building = max(0.0, round(landlord_total - excluded_building, 2))

        calc = CAMCalculationEngine.calculate_tenant_share(allowable_building, cam_provisions)
        calculated_share = calc['calculated_tenant_share']
        variance = round(tenant_share_billed - calculated_share, 2)
        steps = []
        if excluded_building:
            steps.append({
                'step': 'Excluded costs removed from building total',
                'formula': f'${landlord_total:,.2f} - ${excluded_building:,.2f}',
                'result': allowable_building,
            })
        steps.extend(calc.get('calculations') or [])
        calc['calculations'] = steps
        calc['excluded_building_charges'] = excluded_building
        calc['allowable_building_charges'] = allowable_building
        calc['analyzed_line_items'] = analyzed
        calc['landlord_tenant_share'] = tenant_share_billed
        calc['variance_amount'] = variance
        calc['calculated_tenant_share'] = calculated_share
        return calc

    @staticmethod
    def enrich_provisions(provisions: Optional[Dict], extracted_fields: Optional[Dict] = None) -> Dict:
        """Fill blank CAM terms from the lease abstract fields."""
        merged = dict(provisions or {})
        if extracted_fields:
            from_fields = CAMProvisionExtractor.extract_cam_provisions(extracted_fields)
            for key, value in from_fields.items():
                current = merged.get(key)
                empty = current in (None, '', [], False)
                if empty and value not in (None, '', [], False):
                    merged[key] = value
        if CAMCalculationEngine._as_float(merged.get('cam_cap_percentage'), None):
            merged['has_cam_cap'] = True
        return merged

    @staticmethod
    def _as_float(value, default=0.0):
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _prorata_share(cam_provisions: Dict) -> float:
        share = CAMCalculationEngine._as_float(cam_provisions.get('tenant_prorata_share'), None)
        if share is None:
            tenant_sf = CAMCalculationEngine._as_float(cam_provisions.get('tenant_square_footage'), 0)
            building_sf = CAMCalculationEngine._as_float(cam_provisions.get('building_square_footage'), 0)
            share = (tenant_sf / building_sf) if tenant_sf and building_sf else 0.0
        if share > 1:
            share = share / 100.0
        return share
    
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
        
        for item in line_items:
            analyzed = item.copy()
            amount = float(item.get('landlord_amount', item.get('amount', 0)) or 0)
            analyzed['amount'] = amount
            analyzed['landlord_amount'] = amount
            excluded, reason = CAMCalculationEngine.line_item_exclusion(item, cam_provisions)
            analyzed['is_excluded'] = excluded
            analyzed['is_disputed'] = excluded
            analyzed['should_challenge'] = excluded
            analyzed['dispute_reason'] = reason
            analyzed['recommended_action'] = 'CHALLENGE' if excluded else 'ACCEPT'
            analyzed['calculated_amount'] = 0 if excluded else amount
            analyzed['variance_amount'] = amount if excluded else 0
            analyzed['variance'] = analyzed['variance_amount']
            analyzed_items.append(analyzed)
        
        return analyzed_items

    @staticmethod
    def line_item_exclusion(item: Dict, cam_provisions: Dict) -> Tuple[bool, Optional[str]]:
        """Flag a line if the lease exclusions match its category or description."""
        blob = " ".join([
            str(item.get('category') or ''),
            str(item.get('description') or ''),
            str(item.get('notes') or ''),
        ]).upper()
        excluded = cam_provisions.get('excluded_items') or []
        exclusion_text = " ".join(str(x) for x in excluded)
        exclusion_text = f"{exclusion_text} {cam_provisions.get('exclusions_description') or ''}".upper()
        if not exclusion_text.strip() and not excluded:
            return False, None

        checks = [
            (['CAPITAL', 'ROOF'], 'Capital improvement / roof replacement is excluded per lease terms'),
            (['STRUCTURAL'], 'Structural repairs are excluded per lease terms'),
            (['DEPRECIATION'], 'Depreciation is excluded per lease terms'),
            (['DEBT SERVICE', 'DEBT_SERVICE', 'MORTGAGE'], 'Debt service / mortgage is excluded per lease terms'),
            (['LEGAL'], 'Legal fees relating to other tenants are excluded per lease terms'),
        ]
        for keys, reason in checks:
            lease_has = any(key in exclusion_text for key in keys)
            item_has = any(key in blob for key in keys)
            if lease_has and item_has:
                return True, reason
        return False, None
    
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
    assembled = CAMStatementParser.assemble_parsed_statement(statement_text)
    return assembled.get('line_items') or CAMStatementParser.parse_statement_text(statement_text)


def assemble_cam_statement(statement_text: str, gpt_result: Optional[Dict] = None) -> Dict:
    """Merge GPT output with numbered rows from the statement text."""
    return CAMStatementParser.assemble_parsed_statement(statement_text, gpt_result)


def defaults_from_parsed_statement(parsed: Dict) -> Dict:
    """Step 2 field values from a parsed CAM statement."""
    return CAMStatementParser.defaults_from_parsed_statement(parsed)


def calculate_cam_charges(total_charges: float, provisions: Dict) -> Dict:
    """Quick CAM calculation"""
    return CAMCalculationEngine.calculate_tenant_share(total_charges, provisions)


def reconcile_cam_charges(
    landlord_total: float,
    tenant_share_billed: float,
    provisions: Dict,
    line_items: Optional[List[Dict]] = None,
) -> Dict:
    """Tenant CAM after exclusions, pro-rata, stop, and cap."""
    return CAMCalculationEngine.reconcile_cam_charges(
        landlord_total, tenant_share_billed, provisions, line_items
    )


def enrich_cam_provisions(provisions: Optional[Dict], extracted_fields: Optional[Dict] = None) -> Dict:
    """Fill blank CAM terms from abstracted lease fields."""
    return CAMCalculationEngine.enrich_provisions(provisions, extracted_fields)


def analyze_line_items(line_items: List[Dict], cam_provisions: Dict) -> List[Dict]:
    """Quick line item analysis"""
    return CAMCalculationEngine.analyze_line_items(line_items, cam_provisions)


def detect_discrepancies(landlord_total: float, calculated_total: float, line_items: List[Dict]) -> Dict:
    """Quick discrepancy detection"""
    return CAMCalculationEngine.detect_discrepancies(landlord_total, calculated_total, line_items)


def generate_cam_dispute_letter(lease_data: Dict, reconciliation: Dict, items: List[Dict]) -> str:
    """Quick dispute letter generation"""
    return CAMDisputeLetter.generate_dispute_letter(lease_data, reconciliation, items)
