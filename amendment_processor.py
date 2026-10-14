"""
LeaseAI Amendment Processing Module
Handles amendment document extraction and clause resolution
Powers the Amendment Resolution Graph™
"""

import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from extraction_pipeline import LeaseExtractionPipeline


class AmendmentProcessor:
    """
    Processes amendment documents and builds the Amendment Resolution Graph™
    """
    
    def __init__(self):
        """Initialize the amendment processor"""
        self.extraction_pipeline = LeaseExtractionPipeline()
        
        # Amendment-specific fields to extract
        self.amendment_fields = [
            "Amendment Number",
            "Amendment Date",
            "Effective Date",
            "Clauses Modified",
            "Base Rent Modification",
            "Renewal Terms Modification",
            "Termination Rights Modification",
            "CAM Charges Modification",
            "Parking Modification",
            "Operating Hours Modification",
            "Use Clause Modification",
            "Assignment Rights Modification",
            "Insurance Requirements Modification",
            "Maintenance Responsibilities Modification",
            "Superseded Clauses",
            "New Clauses Added",
            "Deleted Clauses",
        ]
    
    def process_amendment(
        self,
        pdf_path: str,
        lease_id: str,
        supabase_client,
        filename: str = None
    ) -> Tuple[str, Dict]:
        """
        Process an amendment document and link it to its base lease.
        
        Args:
            pdf_path: Path to amendment PDF
            lease_id: UUID of the base lease
            supabase_client: Supabase client instance
            filename: Optional filename
            
        Returns:
            Tuple of (amendment_id, extracted_fields)
        """
        
        print(f"[1/7] Extracting text from amendment PDF: {pdf_path}")
        amendment_text, page_count = self.extraction_pipeline.extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(amendment_text)} characters from {page_count} pages")
        
        print(f"[2/7] Scanning for PII...")
        pii_detected = self.extraction_pipeline.detect_pii(amendment_text)
        if pii_detected:
            print(f"⚠ PII detected: {', '.join(pii_detected)}")
        else:
            print(f"✓ No PII detected")
        
        print(f"[3/7] Extracting amendment-specific fields with GPT-4...")
        extracted_fields = self._extract_amendment_fields(amendment_text, lease_id, supabase_client)
        print(f"✓ Extracted {len(extracted_fields)} fields")
        
        print(f"[4/7] Creating amendment record in database...")
        amendment_data = {
            "lease_id": lease_id,
            "amendment_number": extracted_fields.get("Amendment Number", {}).get("value", 1),
            "amendment_date": self._parse_date(extracted_fields.get("Amendment Date", {}).get("value")),
            "effective_date": self._parse_date(extracted_fields.get("Effective Date", {}).get("value")),
            "filename": filename or os.path.basename(pdf_path),
            "page_count": page_count,
            "status": "PROCESSING",
            "extracted_data": extracted_fields,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        amendment_response = supabase_client.table("amendments").insert(amendment_data).execute()
        amendment_id = amendment_response.data[0]["id"]
        print(f"✓ Amendment created with ID: {amendment_id}")
        
        print(f"[5/7] Analyzing clause modifications...")
        clause_modifications = self._analyze_clause_modifications(extracted_fields)
        print(f"✓ Found {len(clause_modifications)} clause modifications")
        
        print(f"[6/7] Saving amendment clauses to database...")
        for clause_mod in clause_modifications:
            clause_record = {
                "amendment_id": amendment_id,
                "clause_type": clause_mod["clause_type"],
                "clause_section": clause_mod.get("clause_section"),
                "modification_type": clause_mod["modification_type"],
                "original_value": clause_mod.get("original_value"),
                "new_value": clause_mod["new_value"],
                "source_text": clause_mod.get("source_text", "")[:500],
                "confidence": clause_mod.get("confidence", "MEDIUM"),
                "effective_date": self._parse_date(clause_mod.get("effective_date")),
                "created_at": datetime.utcnow().isoformat(),
            }
            supabase_client.table("amendment_clauses").insert(clause_record).execute()
        
        print(f"✓ Saved {len(clause_modifications)} clause modifications")
        
        print(f"[7/7] Updating lease clause history...")
        self._update_lease_clause_history(lease_id, amendment_id, clause_modifications, supabase_client)
        print(f"✓ Lease clause history updated")
        
        print(f"[8/7] Updating amendment status to READY FOR REVIEW...")
        supabase_client.table("amendments").update({
            "status": "READY FOR REVIEW",
        }).eq("id", amendment_id).execute()
        print(f"✓ Amendment status updated")
        
        print(f"✓ Amendment processing complete!")
        
        return amendment_id, extracted_fields
    
    def _extract_amendment_fields(self, amendment_text: str, lease_id: str, supabase_client) -> Dict:
        """
        Extract amendment-specific fields using GPT-4.
        
        Args:
            amendment_text: Full text of amendment document
            lease_id: UUID of base lease
            supabase_client: Supabase client
            
        Returns:
            Dictionary of extracted amendment fields
        """
        
        # Get base lease info for context
        lease_response = supabase_client.table("leases").select("*").eq("id", lease_id).execute()
        lease_data = lease_response.data[0] if lease_response.data else {}
        
        property_address = lease_data.get("property_address", "")
        tenant_name = lease_data.get("tenant_name", "")
        
        # Build amendment-specific extraction prompt
        prompt = f"""You are a commercial real estate lease amendment specialist. Extract information from this lease amendment document.

CRITICAL: This is an AMENDMENT to an existing lease, not a new lease. Focus on:
1. What is being CHANGED, MODIFIED, or SUPERSEDED
2. The original value BEFORE the amendment
3. The new value AFTER the amendment
4. Which specific clauses/sections are affected

Base Lease Context:
- Property: {property_address}
- Tenant: {tenant_name}

Amendment Document Text ({len(amendment_text):,} characters):
{amendment_text[:100000]}

Extract the following amendment-specific information:

1. Amendment Number (1st Amendment, 2nd Amendment, etc.)
2. Amendment Date (date signed)
3. Effective Date (when changes take effect - may differ from signing date)
4. List ALL clauses being modified (e.g., "Base Rent", "Renewal Options", "Parking")
5. For EACH modified clause:
   - Original value (before amendment)
   - New value (after amendment)
   - Section reference (e.g., "Section 4.1")
   - Type of modification (MODIFIES, SUPERSEDES, ADDS, DELETES)

Return as JSON:
{{
  "Amendment Number": {{"value": "1", "confidence": "HIGH", "notes": ""}},
  "Amendment Date": {{"value": "2024-06-15", "confidence": "HIGH", "notes": ""}},
  "Effective Date": {{"value": "2024-07-01", "confidence": "HIGH", "notes": ""}},
  "Clauses Modified": {{"value": "Base Rent, Parking, Operating Hours", "confidence": "HIGH", "notes": ""}},
  "Base Rent Modification": {{
    "value": "Original: $1,923.33/month → New: $2,100.00/month",
    "confidence": "HIGH",
    "original_value": "$1,923.33/month",
    "new_value": "$2,100.00/month",
    "modification_type": "MODIFIES",
    "section": "Section 4.1",
    "source_snippet": "...excerpt from amendment...",
    "notes": "Base rent increased effective July 1, 2024"
  }},
  ...
}}

IMPORTANT: Return ONLY the JSON object, no additional text.
"""
        
        # Use GPT-4 to extract
        response = self.extraction_pipeline.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert lease amendment abstraction specialist. Extract ONLY the changes made by amendments, not the full lease terms."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=8000,
        )
        
        # Parse JSON response
        response_text = response.choices[0].message.content
        
        # Extract JSON from response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        import json
        extracted_fields = json.loads(response_text)
        
        return extracted_fields
    
    def _analyze_clause_modifications(self, extracted_fields: Dict) -> List[Dict]:
        """
        Analyze extracted fields and create structured clause modification records.
        
        Args:
            extracted_fields: Dictionary of extracted amendment fields
            
        Returns:
            List of clause modification dictionaries
        """
        
        modifications = []
        
        # Map of field names to clause types
        clause_mappings = {
            "Base Rent Modification": "Base Rent",
            "Renewal Terms Modification": "Renewal Options",
            "Termination Rights Modification": "Termination Rights",
            "CAM Charges Modification": "CAM Charges",
            "Parking Modification": "Parking",
            "Operating Hours Modification": "Operating Hours",
            "Use Clause Modification": "Permitted Use",
            "Assignment Rights Modification": "Assignment Rights",
            "Insurance Requirements Modification": "Insurance Requirements",
            "Maintenance Responsibilities Modification": "Maintenance Responsibilities",
        }
        
        for field_name, clause_type in clause_mappings.items():
            if field_name in extracted_fields:
                field_data = extracted_fields[field_name]
                
                if isinstance(field_data, dict) and field_data.get("value") != "NOT FOUND":
                    modification = {
                        "clause_type": clause_type,
                        "clause_section": field_data.get("section", ""),
                        "modification_type": field_data.get("modification_type", "MODIFIES"),
                        "original_value": field_data.get("original_value", ""),
                        "new_value": field_data.get("new_value", field_data.get("value", "")),
                        "source_text": field_data.get("source_snippet", ""),
                        "confidence": field_data.get("confidence", "MEDIUM"),
                        "effective_date": None,  # Will be set from amendment effective date
                    }
                    modifications.append(modification)
        
        return modifications
    
    def _update_lease_clause_history(
        self,
        lease_id: str,
        amendment_id: str,
        clause_modifications: List[Dict],
        supabase_client
    ):
        """
        Update the lease_clause_history table with amendment changes.
        This powers the "controlling value at any date" functionality.
        
        Args:
            lease_id: UUID of base lease
            amendment_id: UUID of amendment
            clause_modifications: List of clause modification dicts
            supabase_client: Supabase client
        """
        
        # Get amendment details
        amendment_response = supabase_client.table("amendments").select("*").eq("id", amendment_id).execute()
        amendment_data = amendment_response.data[0] if amendment_response.data else {}
        
        effective_date = amendment_data.get("effective_date") or amendment_data.get("amendment_date")
        amendment_number = amendment_data.get("amendment_number", 1)
        
        for clause_mod in clause_modifications:
            clause_type = clause_mod["clause_type"]
            
            # Mark previous version as no longer current
            supabase_client.table("lease_clause_history").update({
                "is_current": False,
                "effective_to": effective_date
            }).eq("lease_id", lease_id).eq("clause_type", clause_type).eq("is_current", True).execute()
            
            # Get max version number for this clause
            history_response = supabase_client.table("lease_clause_history").select("version_number").eq("lease_id", lease_id).eq("clause_type", clause_type).order("version_number", desc=True).limit(1).execute()
            
            max_version = history_response.data[0]["version_number"] if history_response.data else 0
            new_version = max_version + 1
            
            # Insert new version
            history_record = {
                "lease_id": lease_id,
                "clause_type": clause_type,
                "version_number": new_version,
                "source_document_type": "AMENDMENT",
                "source_document_id": amendment_id,
                "clause_value": clause_mod["new_value"],
                "effective_from": effective_date,
                "effective_to": None,
                "is_current": True,
                "modification_type": clause_mod["modification_type"],
                "created_at": datetime.utcnow().isoformat(),
            }
            
            supabase_client.table("lease_clause_history").insert(history_record).execute()
    
    def _parse_date(self, date_value) -> Optional[str]:
        """
        Parse date value into ISO format.
        
        Args:
            date_value: Date string or dict with value
            
        Returns:
            ISO format date string or None
        """
        
        if not date_value:
            return None
        
        if isinstance(date_value, dict):
            date_value = date_value.get("value")
        
        if not date_value or date_value == "NOT FOUND":
            return None
        
        # Try to parse various date formats
        try:
            from datetime import datetime
            for date_format in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    dt = datetime.strptime(str(date_value).split()[0], date_format)
                    return dt.date().isoformat()
                except:
                    continue
        except:
            pass
        
        return None
    
    def get_controlling_clause_value(
        self,
        lease_id: str,
        clause_type: str,
        as_of_date: str,
        supabase_client
    ) -> Optional[Dict]:
        """
        Get the controlling value for a clause at a specific date.
        This is the core of the Amendment Resolution Graph™ query engine.
        
        Args:
            lease_id: UUID of lease
            clause_type: Type of clause (e.g., "Base Rent")
            as_of_date: Date in ISO format (YYYY-MM-DD)
            supabase_client: Supabase client
            
        Returns:
            Dictionary with controlling value info or None
        """
        
        # Query using the helper function
        result = supabase_client.rpc(
            "get_controlling_clause",
            {
                "p_lease_id": lease_id,
                "p_clause_type": clause_type,
                "p_as_of_date": as_of_date
            }
        ).execute()
        
        return result.data[0] if result.data else None
    
    def get_amendment_chain(
        self,
        lease_id: str,
        supabase_client
    ) -> List[Dict]:
        """
        Get the full amendment chain for a lease.
        
        Args:
            lease_id: UUID of lease
            supabase_client: Supabase client
            
        Returns:
            List of amendments with their modified clauses
        """
        
        result = supabase_client.rpc(
            "get_amendment_chain",
            {"p_lease_id": lease_id}
        ).execute()
        
        return result.data or []


# Command-line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python amendment_processor.py <amendment_pdf_path> <lease_id>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    lease_id = sys.argv[2]
    
    # Initialize Supabase
    from supabase import create_client
    import config
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # Process amendment
    processor = AmendmentProcessor()
    
    try:
        amendment_id, fields = processor.process_amendment(
            pdf_path,
            lease_id,
            supabase
        )
        
        print(f"\n{'='*80}")
        print(f"SUCCESS! Amendment ID: {amendment_id}")
        print(f"{'='*80}")
        print(f"\nProcessed amendment with {len(fields)} extracted fields.")
        print(f"Amendment linked to lease: {lease_id}")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"ERROR: {str(e)}")
        print(f"{'='*80}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
