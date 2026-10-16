"""
LeaseAI Amendment Processing Module - Enhanced Version
Handles amendment document extraction and clause resolution
Powers the Amendment Resolution Graph™ ($5.6M IP Asset)

This module:
1. Extracts amendment PDFs using OCR (AWS Textract + Tesseract fallback)
2. Uses GPT-4o to identify modified clauses with original → new values
3. Builds temporal clause history with version control
4. Enables "controlling value at any date" queries
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from extraction_pipeline import LeaseExtractionPipeline


class AmendmentProcessorV2:
    """
    Enhanced amendment processor with improved GPT-4 prompting and clause detection.
    """
    
    def __init__(self):
        """Initialize the amendment processor"""
        self.extraction_pipeline = LeaseExtractionPipeline()
        
        # Comprehensive list of clause types to track
        self.clause_types = [
            # Financial
            "Base Rent",
            "Additional Rent",
            "Percentage Rent",
            "Rent Escalations",
            "Security Deposit",
            "Letter of Credit",
            
            # Operating Costs
            "CAM Charges",
            "CAM Cap",
            "CAM Exclusions",
            "Property Taxes",
            "Insurance Costs",
            "Utilities",
            
            # Term & Options
            "Lease Term",
            "Commencement Date",
            "Expiration Date",
            "Renewal Options",
            "Extension Options",
            "Termination Rights",
            "Early Termination",
            "Holdover Provisions",
            
            # Use & Operations
            "Permitted Use",
            "Prohibited Uses",
            "Exclusivity Clause",
            "Operating Hours",
            "Signage Rights",
            "Co-Tenancy Clause",
            
            # Space & Access
            "Premises Description",
            "Parking Spaces",
            "Parking Cost",
            "Storage Space",
            "Common Areas",
            "Roof Access",
            "Exclusive Use Areas",
            
            # Responsibilities
            "Maintenance Obligations",
            "Repair Responsibilities",
            "HVAC Responsibility",
            "Structural Repairs",
            "Roof Maintenance",
            "ADA Compliance",
            
            # Legal & Assignment
            "Assignment Rights",
            "Subletting Rights",
            "Landlord Consent Requirements",
            "Insurance Requirements",
            "Indemnification",
            "Default Provisions",
            "Cure Periods",
            "Force Majeure",
            
            # Improvements
            "Tenant Improvements",
            "TI Allowance",
            "Alterations",
            "Restoration Obligations",
            "Surrender Conditions",
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
        
        print(f"\n{'='*80}")
        print(f"🔗 AMENDMENT RESOLUTION GRAPH™ - Processing Amendment")
        print(f"{'='*80}\n")
        
        # Step 1: Extract PDF text (with OCR fallback)
        print(f"[1/8] Extracting text from amendment PDF...")
        amendment_text, page_count = self.extraction_pipeline.extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(amendment_text):,} characters from {page_count} pages")
        
        # Step 2: PII scan
        print(f"\n[2/8] Scanning for PII...")
        pii_detected = self.extraction_pipeline.detect_pii(amendment_text)
        if pii_detected:
            print(f"⚠️  PII detected: {', '.join(pii_detected)}")
        else:
            print(f"✓ No PII detected")
        
        # Step 3: Get base lease context
        print(f"\n[3/8] Loading base lease context...")
        lease_response = supabase_client.table("leases").select("*").eq("id", lease_id).execute()
        if not lease_response.data:
            raise Exception(f"Base lease {lease_id} not found")
        lease_data = lease_response.data[0]
        print(f"✓ Base lease found: {lease_data.get('property_address', 'Unknown')}")
        
        # Step 4: Extract amendment metadata and clause changes with GPT-4o
        print(f"\n[4/8] Extracting amendment metadata and clause modifications (GPT-4o)...")
        print(f"   This takes 30-60 seconds...")
        extracted_fields = self._extract_amendment_with_gpt4(
            amendment_text, 
            lease_data, 
            supabase_client
        )
        print(f"✓ Extracted {len(extracted_fields)} fields")
        
        # Step 5: Create amendment record
        print(f"\n[5/8] Creating amendment record in database...")
        amendment_number = self._parse_amendment_number(extracted_fields.get("Amendment Number", {}))
        amendment_date = self._parse_date(extracted_fields.get("Amendment Date", {}))
        effective_date = self._parse_date(extracted_fields.get("Effective Date", {})) or amendment_date
        
        amendment_data = {
            "lease_id": lease_id,
            "amendment_number": amendment_number,
            "amendment_date": amendment_date,
            "effective_date": effective_date,
            "filename": filename or os.path.basename(pdf_path),
            "page_count": page_count,
            "status": "PROCESSING",
            "extracted_data": extracted_fields,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        amendment_response = supabase_client.table("amendments").insert(amendment_data).execute()
        amendment_id = amendment_response.data[0]["id"]
        print(f"✓ Amendment #{amendment_number} created: {amendment_id}")
        
        # Step 6: Parse and save clause modifications
        print(f"\n[6/8] Analyzing clause modifications...")
        clause_modifications = self._parse_clause_modifications(
            extracted_fields, 
            effective_date
        )
        print(f"✓ Found {len(clause_modifications)} clause modification(s)")
        
        if clause_modifications:
            print(f"\n   Clause modifications detected:")
            for mod in clause_modifications:
                print(f"   • {mod['clause_type']}: {mod['modification_type']}")
                print(f"     Before: {(mod['original_value'] or 'N/A')[:60]}...")
                print(f"     After:  {(mod['new_value'] or 'N/A')[:60]}...")
        
        print(f"\n[7/8] Saving clause modifications to database...")
        for clause_mod in clause_modifications:
            clause_record = {
                "amendment_id": amendment_id,
                "clause_type": clause_mod["clause_type"],
                "clause_section": clause_mod.get("clause_section"),
                "modification_type": clause_mod["modification_type"],
                "original_value": clause_mod.get("original_value"),
                "new_value": clause_mod["new_value"],
                "source_text": clause_mod.get("source_text", "")[:1000],  # Limit to 1000 chars
                "confidence": clause_mod.get("confidence", "MEDIUM"),
                "effective_date": effective_date,
                "created_at": datetime.utcnow().isoformat(),
            }
            supabase_client.table("amendment_clauses").insert(clause_record).execute()
        print(f"✓ Saved {len(clause_modifications)} clause modification(s)")
        
        # Step 8: Update lease clause history
        print(f"\n[8/8] Updating lease clause history...")
        self._update_lease_clause_history(
            lease_id, 
            amendment_id, 
            clause_modifications, 
            effective_date,
            supabase_client
        )
        print(f"✓ Clause history updated - version control active")
        
        # Mark as ready for review
        supabase_client.table("amendments").update({
            "status": "READY FOR REVIEW",
        }).eq("id", amendment_id).execute()
        
        print(f"\n{'='*80}")
        print(f"✅ Amendment processing complete!")
        print(f"{'='*80}")
        print(f"Amendment ID: {amendment_id}")
        print(f"Amendment Number: #{amendment_number}")
        print(f"Clauses Modified: {len(clause_modifications)}")
        print(f"Status: READY FOR REVIEW")
        print(f"{'='*80}\n")
        
        return amendment_id, extracted_fields
    
    def _extract_amendment_with_gpt4(
        self, 
        amendment_text: str, 
        lease_data: Dict,
        supabase_client
    ) -> Dict:
        """
        Use GPT-4o to extract amendment metadata and clause modifications.
        
        This is the core intelligence of the Amendment Resolution Graph™.
        
        Args:
            amendment_text: Full text of amendment
            lease_data: Base lease data for context
            supabase_client: Supabase client
            
        Returns:
            Dictionary of extracted amendment fields
        """
        
        property_address = lease_data.get("property_address", "")
        tenant_name = lease_data.get("tenant_name", "")
        
        # Truncate if too long (GPT-4o has 128K token context ~500K chars)
        max_chars = 400000
        amendment_text_truncated = amendment_text[:max_chars]
        if len(amendment_text) > max_chars:
            print(f"   ⚠️  Amendment text truncated from {len(amendment_text):,} to {max_chars:,} chars")
        
        # Build comprehensive extraction prompt
        prompt = f"""You are an expert commercial real estate lease amendment analyst with 20+ years of experience.

CONTEXT:
This is a lease AMENDMENT document (not a base lease). It modifies an existing lease agreement.

Base Lease Information:
- Property: {property_address}
- Tenant: {tenant_name}

YOUR TASK:
Extract ALL modifications made by this amendment. For EACH modified clause, identify:
1. What clause is being changed (e.g., "Base Rent", "Parking", "Renewal Options")
2. The ORIGINAL value (before amendment)
3. The NEW value (after amendment)
4. The type of modification (MODIFIES, SUPERSEDES, ADDS, DELETES)
5. The section reference (e.g., "Section 4.1", "Article VII")

CRITICAL INSTRUCTIONS:
- Focus ONLY on what is being CHANGED or ADDED by this amendment
- Extract the COMPLETE clause text for both original and new values
- Do NOT summarize - extract the full legal text
- If the original value is not stated, write "Not stated - amendment only provides new value"
- Be precise about dates, amounts, percentages, and legal terms

AMENDMENT DOCUMENT TEXT ({len(amendment_text_truncated):,} characters):
---
{amendment_text_truncated}
---

OUTPUT FORMAT:
Return a JSON object with these fields:

{{
  "Amendment Number": {{
    "value": "1",
    "confidence": "HIGH|MEDIUM|LOW",
    "notes": "Any clarifying notes"
  }},
  "Amendment Date": {{
    "value": "YYYY-MM-DD",
    "confidence": "HIGH|MEDIUM|LOW",
    "notes": ""
  }},
  "Effective Date": {{
    "value": "YYYY-MM-DD or same as Amendment Date",
    "confidence": "HIGH|MEDIUM|LOW",
    "notes": ""
  }},
  "Clause_Modifications": [
    {{
      "clause_type": "Base Rent",
      "modification_type": "MODIFIES|SUPERSEDES|ADDS|DELETES",
      "section": "Section 4.1",
      "original_value": "Full text of original clause value",
      "new_value": "Full text of new clause value",
      "source_snippet": "Relevant excerpt from amendment (first 300 chars)",
      "confidence": "HIGH|MEDIUM|LOW",
      "notes": "Brief explanation of the change"
    }},
    ...additional modified clauses...
  ]
}}

EXAMPLES OF CLAUSE TYPES (use these when applicable):
{chr(10).join(f"- {ct}" for ct in self.clause_types[:20])}
...and any other clauses you identify.

RETURN ONLY THE JSON OBJECT. No additional text or explanation.
"""
        
        # Call GPT-4o
        response = self.extraction_pipeline.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert lease amendment abstraction specialist. Extract ALL clause modifications with complete original and new values. Be thorough and precise."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=16000,  # Allow long responses for comprehensive extraction
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        
        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        try:
            extracted_fields = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Failed to parse GPT-4 response as JSON: {e}")
            print(f"   Response preview: {response_text[:500]}...")
            # Return minimal valid structure
            extracted_fields = {
                "Amendment Number": {"value": "1", "confidence": "LOW", "notes": "Parsing failed"},
                "Amendment Date": {"value": datetime.now().strftime("%Y-%m-%d"), "confidence": "LOW"},
                "Effective Date": {"value": datetime.now().strftime("%Y-%m-%d"), "confidence": "LOW"},
                "Clause_Modifications": []
            }
        
        return extracted_fields
    
    def _parse_clause_modifications(
        self, 
        extracted_fields: Dict, 
        effective_date: str
    ) -> List[Dict]:
        """
        Parse extracted fields into structured clause modification records.
        
        Args:
            extracted_fields: GPT-4 extracted fields
            effective_date: When amendment takes effect
            
        Returns:
            List of clause modification dictionaries
        """
        
        modifications = []
        
        # Extract from Clause_Modifications array (new format)
        clause_mods = extracted_fields.get("Clause_Modifications", [])
        
        for mod in clause_mods:
            if not isinstance(mod, dict):
                continue
            
            clause_type = mod.get("clause_type")
            if not clause_type:
                continue
            
            modification = {
                "clause_type": clause_type,
                "clause_section": mod.get("section", ""),
                "modification_type": mod.get("modification_type", "MODIFIES"),
                "original_value": mod.get("original_value", ""),
                "new_value": mod.get("new_value", ""),
                "source_text": mod.get("source_snippet", "")[:1000],
                "confidence": mod.get("confidence", "MEDIUM"),
                "effective_date": effective_date,
            }
            
            modifications.append(modification)
        
        return modifications
    
    def _update_lease_clause_history(
        self,
        lease_id: str,
        amendment_id: str,
        clause_modifications: List[Dict],
        effective_date: str,
        supabase_client
    ):
        """
        Update the lease_clause_history table to track clause evolution over time.
        
        This enables "controlling value at any date" queries.
        
        Args:
            lease_id: UUID of base lease
            amendment_id: UUID of amendment
            clause_modifications: List of clause modification dicts
            effective_date: When amendment takes effect (ISO date)
            supabase_client: Supabase client
        """
        
        for clause_mod in clause_modifications:
            clause_type = clause_mod["clause_type"]
            
            # 1. Mark previous version as no longer current
            supabase_client.table("lease_clause_history").update({
                "is_current": False,
                "effective_to": effective_date
            }).eq("lease_id", lease_id).eq("clause_type", clause_type).eq("is_current", True).execute()
            
            # 2. Get max version number for this clause type
            history_response = supabase_client.table("lease_clause_history").select("version_number").eq(
                "lease_id", lease_id
            ).eq(
                "clause_type", clause_type
            ).order("version_number", desc=True).limit(1).execute()
            
            max_version = history_response.data[0]["version_number"] if history_response.data else 0
            new_version = max_version + 1
            
            # 3. Insert new version
            history_record = {
                "lease_id": lease_id,
                "clause_type": clause_type,
                "version_number": new_version,
                "source_document_type": "AMENDMENT",
                "source_document_id": amendment_id,
                "clause_value": clause_mod["new_value"],
                "effective_from": effective_date,
                "effective_to": None,  # Current version has no end date
                "is_current": True,
                "modification_type": clause_mod["modification_type"],
                "created_at": datetime.utcnow().isoformat(),
            }
            
            supabase_client.table("lease_clause_history").insert(history_record).execute()
            print(f"   ✓ {clause_type}: v{max_version} → v{new_version}")
    
    def _parse_amendment_number(self, field_data) -> int:
        """Parse amendment number from field data."""
        if isinstance(field_data, dict):
            value = field_data.get("value", "1")
        else:
            value = field_data
        
        # Extract number from strings like "1st Amendment", "2nd", "Third", etc.
        value_str = str(value).lower()
        
        # Try direct int conversion first
        try:
            return int(value_str)
        except:
            pass
        
        # Extract first number found
        import re
        match = re.search(r'\d+', value_str)
        if match:
            return int(match.group())
        
        # Word to number mapping
        word_to_num = {
            "first": 1, "1st": 1,
            "second": 2, "2nd": 2,
            "third": 3, "3rd": 3,
            "fourth": 4, "4th": 4,
            "fifth": 5, "5th": 5,
        }
        
        for word, num in word_to_num.items():
            if word in value_str:
                return num
        
        # Default to 1
        return 1
    
    def _parse_date(self, field_data) -> Optional[str]:
        """Parse date from field data into ISO format (YYYY-MM-DD)."""
        if not field_data:
            return None
        
        if isinstance(field_data, dict):
            date_value = field_data.get("value")
        else:
            date_value = field_data
        
        if not date_value or date_value == "NOT FOUND":
            return None
        
        # Try various date formats
        try:
            for date_format in [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%B %d, %Y",
                "%b %d, %Y",
                "%Y/%m/%d"
            ]:
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
        
        This is the core query function of the Amendment Resolution Graph™.
        
        Args:
            lease_id: UUID of lease
            clause_type: Type of clause (e.g., "Base Rent")
            as_of_date: Date in ISO format (YYYY-MM-DD)
            supabase_client: Supabase client
            
        Returns:
            Dictionary with controlling value info or None
        """
        
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
        print("Usage: python amendment_processor_v2.py <amendment_pdf_path> <lease_id>")
        print("\nExample:")
        print("  python amendment_processor_v2.py amendment_1.pdf 123e4567-e89b-12d3-a456-426614174000")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    lease_id = sys.argv[2]
    
    # Initialize Supabase
    from supabase import create_client
    import config
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # Process amendment
    processor = AmendmentProcessorV2()
    
    try:
        amendment_id, fields = processor.process_amendment(
            pdf_path,
            lease_id,
            supabase
        )
        
        print(f"\n✅ SUCCESS")
        print(f"Amendment ID: {amendment_id}")
        print(f"Extracted {len(fields)} field(s)")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
