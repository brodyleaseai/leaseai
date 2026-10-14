"""
Test Full 84-Field Extraction (No Database)
Extracts all lease fields using GPT-4 without saving to Supabase
"""

import sys
import json
from extraction_pipeline import LeaseExtractionPipeline

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_full_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("=" * 80)
    print("  LeaseAI Full 84-Field Extraction Test")
    print("=" * 80)
    print()
    
    # Initialize pipeline
    print("Initializing extraction pipeline...")
    pipeline = LeaseExtractionPipeline()
    print(f"✓ Pipeline configured to extract {len(pipeline.lease_fields)} fields")
    print()
    
    # Extract text from PDF
    print("[Step 1/3] Extracting text from PDF...")
    try:
        lease_text, page_count = pipeline.extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(lease_text):,} characters from {page_count} pages")
    except Exception as e:
        print(f"✗ Failed to extract text: {e}")
        sys.exit(1)
    
    print()
    
    # Check for PII
    print("[Step 2/3] Scanning for PII...")
    pii_detected = pipeline.detect_pii(lease_text)
    if pii_detected:
        print(f"⚠ PII detected: {', '.join(pii_detected)}")
    else:
        print("✓ No PII detected")
    
    print()
    
    # Extract fields with GPT-4
    print("[Step 3/3] Extracting all 84 fields with GPT-4...")
    print("This will take 30-60 seconds...")
    print()
    
    try:
        extracted_fields = pipeline.extract_fields_with_gpt4(lease_text)
        print(f"✓ Successfully extracted {len(extracted_fields)} fields!")
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("  EXTRACTION RESULTS")
    print("=" * 80)
    print()
    
    # Categorize and display results
    high_confidence = []
    medium_confidence = []
    low_confidence = []
    not_found = []
    
    for field_name, field_data in extracted_fields.items():
        if isinstance(field_data, dict):
            value = field_data.get("value", "")
            confidence = field_data.get("confidence", "LOW")
            
            if value == "NOT FOUND":
                not_found.append(field_name)
            elif confidence == "HIGH":
                high_confidence.append((field_name, value, field_data.get("notes", "")))
            elif confidence == "MEDIUM":
                medium_confidence.append((field_name, value, field_data.get("notes", "")))
            else:
                low_confidence.append((field_name, value, field_data.get("notes", "")))
    
    # Summary statistics
    print(f"📊 Extraction Statistics:")
    print(f"   Total Fields:        {len(extracted_fields)}")
    print(f"   ✓ High Confidence:   {len(high_confidence)}")
    print(f"   ⚠ Medium Confidence: {len(medium_confidence)}")
    print(f"   ⚠ Low Confidence:    {len(low_confidence)}")
    print(f"   ✗ Not Found:         {len(not_found)}")
    print()
    
    # Display HIGH confidence fields
    if high_confidence:
        print("=" * 80)
        print("  HIGH CONFIDENCE FIELDS")
        print("=" * 80)
        print()
        for field_name, value, notes in high_confidence:
            print(f"📌 {field_name}")
            print(f"   Value: {value}")
            if notes:
                print(f"   Notes: {notes}")
            print()
    
    # Display MEDIUM confidence fields
    if medium_confidence:
        print("=" * 80)
        print("  MEDIUM CONFIDENCE FIELDS")
        print("=" * 80)
        print()
        for field_name, value, notes in medium_confidence:
            print(f"📌 {field_name}")
            print(f"   Value: {value}")
            if notes:
                print(f"   Notes: {notes}")
            print()
    
    # Display LOW confidence fields (first 10)
    if low_confidence:
        print("=" * 80)
        print(f"  LOW CONFIDENCE FIELDS (showing first 10 of {len(low_confidence)})")
        print("=" * 80)
        print()
        for field_name, value, notes in low_confidence[:10]:
            print(f"📌 {field_name}")
            print(f"   Value: {value}")
            if notes:
                print(f"   Notes: {notes}")
            print()
    
    # Display NOT FOUND fields (summary only)
    if not_found:
        print("=" * 80)
        print(f"  NOT FOUND ({len(not_found)} fields)")
        print("=" * 80)
        print()
        print(", ".join(not_found))
        print()
    
    # Save full results to JSON file
    output_file = "extraction_results.json"
    with open(output_file, "w") as f:
        json.dump(extracted_fields, f, indent=2)
    
    print("=" * 80)
    print(f"✓ Full results saved to: {output_file}")
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()
