"""
OCR Fallback Test for LeaseAI Extraction Pipeline

This script tests the OCR extraction capabilities:
1. Standard PDF text extraction (PyPDF2)
2. AWS Textract OCR (cloud-based, high quality)
3. Tesseract OCR (local fallback)

Usage:
    python test_ocr_extraction.py <path_to_pdf>
    
Example:
    python test_ocr_extraction.py sample_scanned_lease.pdf
"""

import sys
import os
from pathlib import Path
from extraction_pipeline import LeaseExtractionPipeline
import config

def print_header(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def test_ocr_extraction(pdf_path: str):
    """Test OCR extraction on a PDF file"""
    
    print_header("LeaseAI OCR Extraction Test")
    
    # Validate file exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
    print(f"📄 File: {pdf_path}")
    print(f"📦 Size: {file_size:.2f} MB")
    
    # Check configuration
    print_header("Configuration Check")
    
    print("🔧 OpenAI API Key:", "✅ Configured" if config.OPENAI_API_KEY else "❌ Missing")
    print("🔧 AWS Access Key:", "✅ Configured" if config.AWS_ACCESS_KEY_ID else "⚠️  Not configured (will use Tesseract)")
    print("🔧 AWS Secret Key:", "✅ Configured" if config.AWS_SECRET_ACCESS_KEY else "⚠️  Not configured (will use Tesseract)")
    print("🔧 AWS Region:", config.AWS_REGION if hasattr(config, 'AWS_REGION') else "us-east-1")
    
    # Check dependencies
    print_header("Dependency Check")
    
    dependencies = {
        'boto3': 'AWS Textract SDK',
        'pdf2image': 'PDF to Image converter',
        'pytesseract': 'Tesseract OCR wrapper',
        'PIL': 'Image processing (Pillow)'
    }
    
    all_deps_installed = True
    for module, description in dependencies.items():
        try:
            if module == 'PIL':
                import PIL
            else:
                __import__(module)
            print(f"✅ {module:20s} - {description}")
        except ImportError:
            print(f"❌ {module:20s} - {description} (NOT INSTALLED)")
            all_deps_installed = False
    
    if not all_deps_installed:
        print("\n⚠️  Missing dependencies. Install with:")
        print("   pip install -r requirements_ocr.txt")
        print("\n   Also install system packages:")
        print("   - Ubuntu: sudo apt-get install tesseract-ocr poppler-utils")
        print("   - macOS: brew install tesseract poppler")
    
    # Test extraction
    print_header("Text Extraction Test")
    
    try:
        pipeline = LeaseExtractionPipeline()
        
        print("⏳ Extracting text from PDF...")
        print("   (This may take 30-60 seconds for scanned PDFs)\n")
        
        text, page_count = pipeline.extract_text_from_pdf(pdf_path)
        
        print_header("Extraction Results")
        
        print(f"✅ Extraction successful!")
        print(f"📄 Pages: {page_count}")
        print(f"📝 Characters extracted: {len(text):,}")
        print(f"📏 Words: ~{len(text.split()):,}")
        
        # Show sample of extracted text
        print("\n" + "-" * 80)
        print("First 1000 characters of extracted text:")
        print("-" * 80)
        print(text[:1000])
        if len(text) > 1000:
            print("\n... (truncated)")
        print("-" * 80)
        
        # Quality check
        print_header("Quality Assessment")
        
        if len(text) < 500:
            print("⚠️  WARNING: Very little text extracted (<500 chars)")
            print("   The PDF may be:")
            print("   - Heavily redacted")
            print("   - Poor quality scan")
            print("   - Protected/encrypted")
        elif len(text) < 2000:
            print("⚠️  Low text volume extracted (<2000 chars)")
            print("   Consider verifying OCR quality")
        else:
            print("✅ Good text volume extracted")
        
        # Check for common lease keywords
        keywords = ['lease', 'tenant', 'landlord', 'rent', 'term', 'premises', 'agreement']
        found_keywords = [kw for kw in keywords if kw.lower() in text.lower()]
        
        print(f"\n🔍 Lease keywords found: {len(found_keywords)}/{len(keywords)}")
        print(f"   Found: {', '.join(found_keywords) if found_keywords else 'None'}")
        
        if len(found_keywords) < 3:
            print("   ⚠️  Few lease-related keywords detected")
        else:
            print("   ✅ Document appears to be lease-related")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {str(e)}")
        import traceback
        print("\nFull error traceback:")
        print(traceback.format_exc())
        return False

def main():
    """Main test function"""
    
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_extraction.py <path_to_pdf>")
        print("\nExample:")
        print("  python test_ocr_extraction.py sample_lease.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    success = test_ocr_extraction(pdf_path)
    
    if success:
        print_header("✅ Test Complete - OCR System Working")
        print("\n💡 Next Steps:")
        print("   1. Test with a known scanned lease document")
        print("   2. Verify extracted text quality")
        print("   3. Run full lease extraction: python app.py")
        sys.exit(0)
    else:
        print_header("❌ Test Failed")
        print("\n💡 Troubleshooting:")
        print("   1. Check dependencies: pip install -r requirements_ocr.txt")
        print("   2. Install Tesseract: apt-get install tesseract-ocr (Linux)")
        print("   3. Install poppler: apt-get install poppler-utils (Linux)")
        print("   4. Configure AWS credentials in config.py for better OCR quality")
        sys.exit(1)

if __name__ == "__main__":
    main()
