"""
Quick OCR System Verification
Tests that all OCR components are installed and importable
"""

import sys

print("=" * 80)
print("  LeaseAI OCR System Verification")
print("=" * 80)

# Test 1: Core imports
print("\n[1/5] Testing core imports...")
try:
    import config
    print("  ✓ config.py")
    from extraction_pipeline import LeaseExtractionPipeline
    print("  ✓ extraction_pipeline.py")
    print("  ✓ Core imports successful")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Test 2: OCR dependencies
print("\n[2/5] Testing OCR dependencies...")
try:
    import PyPDF2
    print("  ✓ PyPDF2 (PDF text extraction)")
except ImportError:
    print("  ✗ PyPDF2 not installed")

try:
    import boto3
    print("  ✓ boto3 (AWS Textract SDK)")
except ImportError:
    print("  ⚠ boto3 not installed (AWS Textract unavailable)")

try:
    import pdf2image
    print("  ✓ pdf2image (PDF to image converter)")
except ImportError:
    print("  ⚠ pdf2image not installed (OCR unavailable)")

try:
    import pytesseract
    print("  ✓ pytesseract (Tesseract OCR wrapper)")
except ImportError:
    print("  ⚠ pytesseract not installed (Tesseract OCR unavailable)")

try:
    from PIL import Image
    print("  ✓ PIL/Pillow (Image processing)")
except ImportError:
    print("  ⚠ Pillow not installed (Image processing unavailable)")

# Test 3: Configuration
print("\n[3/5] Testing configuration...")
print(f"  OpenAI API Key: {'✓ Configured' if config.OPENAI_API_KEY and config.OPENAI_API_KEY != 'your-actual-openai-key-here' else '✗ Not configured'}")
print(f"  Supabase URL: {'✓ Configured' if config.SUPABASE_URL else '✗ Not configured'}")
print(f"  AWS Access Key: {'✓ Configured' if config.AWS_ACCESS_KEY_ID else '⚠ Not configured (will use Tesseract fallback)'}")

# Test 4: System dependencies
print("\n[4/5] Testing system dependencies...")
import subprocess
try:
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        version = result.stdout.split('\n')[0]
        print(f"  ✓ Tesseract OCR: {version}")
    else:
        print("  ✗ Tesseract not found")
except FileNotFoundError:
    print("  ✗ Tesseract not installed")

try:
    result = subprocess.run(['pdfinfo', '-v'], capture_output=True, text=True)
    if result.returncode == 0 or 'pdfinfo' in result.stdout.lower() or 'pdfinfo' in result.stderr.lower():
        print("  ✓ Poppler utils (pdfinfo)")
    else:
        print("  ⚠ Poppler utils may not be installed")
except FileNotFoundError:
    print("  ⚠ Poppler utils not found")

# Test 5: Pipeline initialization
print("\n[5/5] Testing pipeline initialization...")
try:
    pipeline = LeaseExtractionPipeline()
    print("  ✓ LeaseExtractionPipeline initialized")
    print(f"  ✓ Configured to extract {len(pipeline.lease_fields)} lease fields")
except Exception as e:
    print(f"  ✗ Failed to initialize pipeline: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 80)
print("  ✓ OCR System Verification Complete")
print("=" * 80)
print("\nNext steps:")
print("  1. Ensure all ✗ items are resolved")
print("  2. Configure API keys in .env file")
print("  3. Test with a real PDF: python test_ocr_extraction.py lease.pdf")
print()
