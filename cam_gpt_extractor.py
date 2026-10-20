"""
LeaseAI - CAM GPT-4o Integration
Phase 2B: Automated CAM extraction and parsing using OpenAI GPT-4o

This module handles:
- CAM provision extraction from lease documents using GPT-4o
- CAM statement parsing and line-item extraction
- Intelligent categorization of CAM charges
"""

import os
import json
from typing import Dict, List, Optional
import openai


class CAMProvisionGPTExtractor:
    """
    Use GPT-4o to extract CAM-specific provisions from lease text
    More accurate than regex-based extraction
    """
    
    CAM_EXTRACTION_PROMPT = """
You are a commercial real estate lease analyst specializing in Common Area Maintenance (CAM) provisions. 

Extract the following CAM-specific information from this lease document:

1. **CAM Base Year**: The year used as baseline for CAM calculations (e.g., "2024")
2. **CAM Stop Amount**: The maximum CAM amount covered by landlord (e.g., "$50,000" or "none")
3. **CAM Base Amount**: The base amount for CAM calculations (e.g., "$45,000")
4. **Tenant Pro-Rata Share**: Tenant's percentage of building CAM charges (e.g., "10.5%" or calculate from square footage)
5. **Tenant Square Footage**: Leased premises area in square feet (e.g., "10,000 SF")
6. **Building Square Footage**: Total building area (e.g., "100,000 SF")
7. **CAM Cap**: Is there a cap on annual CAM increases? (Yes/No)
8. **CAM Cap Percentage**: If yes, what is the maximum annual increase? (e.g., "5%")
9. **CAM Exclusions**: List of items landlord CANNOT charge tenant for (e.g., ["Capital improvements", "Structural repairs", "Property taxes"])
10. **CAM Payment Frequency**: How often tenant pays CAM (e.g., "Monthly", "Quarterly", "Annually")
11. **Reconciliation Deadline**: When must landlord provide annual CAM reconciliation? (e.g., "Within 90 days of year-end")
12. **Tenant Audit Rights**: Can tenant audit CAM charges? (Yes/No)
13. **Audit Deadline**: If yes, within what timeframe? (e.g., "Within 60 days of reconciliation")

Return ONLY a JSON object with these exact keys (use null for missing values):
{
  "cam_base_year": integer or null,
  "cam_stop_amount": number or null,
  "cam_base_amount": number or null,
  "tenant_prorata_share": number (as decimal, e.g., 0.105 for 10.5%) or null,
  "tenant_square_footage": integer or null,
  "building_square_footage": integer or null,
  "has_cam_cap": boolean,
  "cam_cap_percentage": number or null,
  "cam_exclusions": array of strings or empty array,
  "cam_payment_frequency": string or null,
  "reconciliation_deadline": string or null,
  "tenant_audit_right": boolean,
  "audit_deadline": string or null
}

If square footage is provided but not pro-rata share, calculate it: tenant_sf / building_sf

Lease Document:
{lease_text}
"""

    @staticmethod
    def extract_cam_provisions_from_text(lease_text: str, openai_api_key: str) -> Dict:
        """
        Use GPT-4o to extract CAM provisions from lease text
        
        Args:
            lease_text: Full text of the lease document
            openai_api_key: OpenAI API key
            
        Returns:
            Dictionary of CAM provisions
        """
        try:
            client = openai.OpenAI(api_key=openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a commercial real estate lease analyst. Extract CAM provisions and return valid JSON only."},
                    {"role": "user", "content": CAMProvisionGPTExtractor.CAM_EXTRACTION_PROMPT.format(lease_text=lease_text[:15000])}  # Limit to 15k chars
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and add confidence scores
            result['extraction_method'] = 'GPT-4o'
            result['extraction_confidence'] = 'HIGH' if result.get('tenant_prorata_share') else 'MEDIUM'
            
            return result
            
        except Exception as e:
            print(f"Error in GPT-4o CAM extraction: {str(e)}")
            return {
                'error': str(e),
                'extraction_method': 'FAILED'
            }


class CAMStatementGPTParser:
    """
    Use GPT-4o to parse landlord CAM statements and extract line items
    Intelligently categorizes charges and detects anomalies
    """
    
    CAM_PARSING_PROMPT = """
You are a commercial real estate CAM charge auditor. Parse this landlord CAM reconciliation statement.

Extract ALL line items with:
1. **Description**: What the charge is for (exactly as written)
2. **Category**: Classify into ONE of these categories:
   - UTILITIES (electric, gas, water, sewer)
   - MAINTENANCE (routine maintenance, repairs)
   - REPAIRS (non-routine repairs)
   - INSURANCE (property insurance, liability)
   - PROPERTY_TAX (real estate taxes)
   - MANAGEMENT_FEE (property management)
   - SECURITY (security services, systems)
   - LANDSCAPING (grounds, lawn care)
   - SNOW_REMOVAL (snow plowing, ice removal)
   - JANITORIAL (cleaning services)
   - HVAC (heating, cooling, ventilation)
   - ELEVATOR (elevator maintenance)
   - PARKING (parking lot maintenance)
   - ADMIN (administrative costs)
   - OTHER (anything that doesn't fit above)

3. **Amount**: The dollar amount (just the number, no $ or commas)

4. **Frequency**: How often this charge occurs (Annual, Monthly, One-time)

5. **Notes**: Any special notes or flags (e.g., "Unusually high", "Capital improvement?", "May be excluded per lease")

Return ONLY a JSON object:
{
  "statement_date": "YYYY-MM-DD" or null,
  "period_year": integer (e.g., 2024),
  "total_building_charges": number,
  "tenant_share_billed": number or null,
  "line_items": [
    {
      "line_number": 1,
      "description": "string",
      "category": "string (from list above)",
      "amount": number,
      "frequency": "Annual|Monthly|One-time",
      "notes": "string or null"
    }
  ]
}

CAM Statement:
{statement_text}
"""

    @staticmethod
    def parse_cam_statement(statement_text: str, openai_api_key: str) -> Dict:
        """
        Use GPT-4o to parse CAM statement and extract line items
        
        Args:
            statement_text: Text extracted from CAM statement PDF
            openai_api_key: OpenAI API key
            
        Returns:
            Dictionary with line items and metadata
        """
        try:
            client = openai.OpenAI(api_key=openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a CAM charge auditor. Parse the statement and return valid JSON only."},
                    {"role": "user", "content": CAMStatementGPTParser.CAM_PARSING_PROMPT.format(statement_text=statement_text[:20000])}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add metadata
            result['parsing_method'] = 'GPT-4o'
            result['total_line_items'] = len(result.get('line_items', []))
            
            return result
            
        except Exception as e:
            print(f"Error in GPT-4o CAM parsing: {str(e)}")
            return {
                'error': str(e),
                'parsing_method': 'FAILED',
                'line_items': []
            }


def extract_cam_provisions_with_gpt(lease_text: str, openai_api_key: str) -> Dict:
    """Convenience function for GPT-4o CAM extraction"""
    return CAMProvisionGPTExtractor.extract_cam_provisions_from_text(lease_text, openai_api_key)


def parse_cam_statement_with_gpt(statement_text: str, openai_api_key: str) -> Dict:
    """Convenience function for GPT-4o CAM statement parsing"""
    return CAMStatementGPTParser.parse_cam_statement(statement_text, openai_api_key)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF file
    Uses pdfplumber for better text extraction
    """
    try:
        import pdfplumber
        
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        return text
    except ImportError:
        # Fallback to PyPDF2
        import PyPDF2
        
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""


def save_cam_provisions_to_db(lease_id: str, provisions: Dict, supabase_client):
    """
    Save extracted CAM provisions to database
    
    Args:
        lease_id: UUID of the lease
        provisions: Dictionary of CAM provisions
        supabase_client: Supabase client instance
    """
    try:
        # Check if provisions already exist
        existing = supabase_client.table("cam_provisions").select("id").eq("lease_id", lease_id).execute()
        
        record = {
            'lease_id': lease_id,
            'cam_base_year': provisions.get('cam_base_year'),
            'cam_stop_amount': provisions.get('cam_stop_amount'),
            'cam_base_amount': provisions.get('cam_base_amount'),
            'tenant_prorata_share': provisions.get('tenant_prorata_share'),
            'tenant_square_footage': provisions.get('tenant_square_footage'),
            'building_square_footage': provisions.get('building_square_footage'),
            'has_cam_cap': provisions.get('has_cam_cap', False),
            'cam_cap_percentage': provisions.get('cam_cap_percentage'),
            'cam_cap_amount': None,  # Can be calculated from base * percentage
            'excluded_items': provisions.get('cam_exclusions', []),
            'exclusions_description': ', '.join(provisions.get('cam_exclusions', [])) if provisions.get('cam_exclusions') else None,
            'cam_payment_frequency': provisions.get('cam_payment_frequency'),
            'cam_reconciliation_deadline': provisions.get('reconciliation_deadline'),
            'tenant_audit_right': provisions.get('tenant_audit_right', False),
            'audit_deadline': provisions.get('audit_deadline'),
            'base_year_confidence': provisions.get('extraction_confidence', 'MEDIUM'),
            'prorata_share_confidence': provisions.get('extraction_confidence', 'MEDIUM'),
            'exclusions_confidence': provisions.get('extraction_confidence', 'MEDIUM'),
            'extracted_at': datetime.now().isoformat(),
            'extracted_by': provisions.get('extraction_method', 'GPT-4o')
        }
        
        if existing.data:
            # Update existing record
            supabase_client.table("cam_provisions").update(record).eq("lease_id", lease_id).execute()
        else:
            # Insert new record
            supabase_client.table("cam_provisions").insert(record).execute()
        
        return True
    except Exception as e:
        print(f"Error saving CAM provisions: {str(e)}")
        return False
