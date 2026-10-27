"""
LeaseAI Extraction Pipeline
Complete PDF → AI Extraction → Database workflow
"""
import os
import re
import io
import json
import base64
import unicodedata
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import PyPDF2
from openai import OpenAI
import config

# Scanned PDFs often yield >100 junk characters (page numbers, "l" glyphs,
# CID font leftovers). Require real words before skipping OCR.
MIN_EXTRACTABLE_WORDS = 80
MIN_FOUND_FIELDS = 8
NOT_FOUND_VALUES = {"", "NOT FOUND", "N/A", "NA", "NONE", "NULL", "UNKNOWN"}


def normalize_lease_text(text: str) -> str:
    """Collapse lookalike Unicode so word counts see real letters."""
    return unicodedata.normalize("NFKC", text or "")


def word_list(text: str) -> List[str]:
    return re.findall(r"[A-Za-z]{3,}", normalize_lease_text(text))


def is_extractable_text(text: str, min_words: int = MIN_EXTRACTABLE_WORDS) -> bool:
    """True when the text looks like a readable lease, not OCR-skip junk."""
    if not text or not text.strip():
        return False
    words = word_list(text)
    unique = {w.lower() for w in words}
    return len(words) >= min_words and len(unique) >= max(20, min_words // 4)


def count_found_fields(extracted_fields: Dict) -> int:
    """Count fields that have a real value (not NOT FOUND)."""
    found = 0
    for field_data in (extracted_fields or {}).values():
        if isinstance(field_data, dict):
            value = str(field_data.get("value", "")).strip()
        else:
            value = str(field_data).strip()
        if value.upper() not in NOT_FOUND_VALUES:
            found += 1
    return found


class LeaseExtractionPipeline:
    """
    Complete pipeline for extracting lease data using GPT-4.
    """
    
    def __init__(self, openai_api_key: str = None):
        """Initialize the extraction pipeline."""
        self.api_key = openai_api_key or config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        
        # Define the 84 comprehensive lease fields to extract
        self.lease_fields = [
            # Party Information
            "Landlord Legal Name",
            "Landlord Registered Address",
            "Landlord Contact / Notice Address",
            "Tenant Legal Name",
            "Tenant Trade Name (if different)",
            "Tenant Registered Address",
            "Guarantor Name(s)",
            
            # Property Details
            "Property Civic Address",
            "Property Legal Description",
            "Premises Square Footage (RSF)",
            "Building Total Square Footage",
            "Floor(s) Occupied",
            "Suite / Unit Number",
            "Building Class",
            
            # Lease Type & Term
            "Lease Type (Gross / Net / Modified Gross)",
            "Net Lease Type (Single / Double / Triple)",
            "Lease Commencement Date",
            "Rent Commencement Date",
            "Lease Expiration Date",
            "Lease Term (Total Months)",
            
            # Base Rent
            "Base Rent Year 1 (monthly)",
            "Base Rent Year 2 (monthly)",
            "Base Rent Year 3 (monthly)",
            "Base Rent Year 4 (monthly)",
            "Base Rent Year 5 (monthly)",
            "Full Rent Schedule (all years)",
            "Free Rent Period (months)",
            
            # Rent Escalations
            "Annual Escalation Type (Fixed / CPI / Percentage)",
            "Annual Escalation Rate or Cap",
            "CPI Index Used (if applicable)",
            "Percentage Rent Clause",
            "Gross Revenue Breakpoint (if percentage rent)",
            
            # Operating Expenses
            "Base Year for Operating Expenses",
            "Operating Expense Stop Amount",
            "CAM / Operating Cost Charges",
            "CAM Annual Increase Cap (%)",
            "CAM Exclusions",
            
            # Taxes & Insurance
            "Property Tax Responsibility",
            "Property Insurance Responsibility",
            "Tenant Insurance Requirements",
            "Tenant Liability Insurance Minimum",
            
            # Utilities & Maintenance
            "Utilities Responsibility",
            "HVAC Responsibility (Landlord / Tenant)",
            "HVAC Maintenance Obligation",
            "Janitorial Responsibility",
            "Structural / Roof Repair Responsibility",
            
            # Renewal Options
            "Number of Renewal Options",
            "Renewal Option Term Length",
            "Renewal Notice Deadline",
            "Renewal Rent Basis (FMV / Fixed / CPI)",
            "Right of First Refusal",
            "Right of First Offer",
            "Expansion Option",
            "Contraction / Reduction Option",
            
            # Termination
            "Early Termination Right",
            "Termination Notice Period",
            "Early Termination Fee / Penalty",
            
            # Use & Assignment
            "Permitted Use",
            "Prohibited Uses / Exclusivity Clause",
            "Subletting / Assignment Rights",
            "Subletting — Landlord Consent Required",
            "Co-Tenancy Clause",
            
            # Improvements & Alterations
            "Tenant Improvement Allowance (TIA)",
            "TIA Conditions / Milestones",
            "Alterations — Landlord Consent Threshold",
            "ADA / Accessibility Compliance Responsibility",
            
            # Security & Deposits
            "Security Deposit Amount",
            "Security Deposit — Letter of Credit",
            "Security Deposit Reduction Schedule",
            
            # Parking & Amenities
            "Parking — Number of Stalls",
            "Parking — Monthly Cost per Stall",
            "Storage Space Included",
            "Signage Rights",
            "Roof / Exterior Access Rights",
            
            # Legal & Compliance
            "Hazardous Materials Clause",
            "Governing Law Jurisdiction",
            "SNDA Agreement Required",
            "Estoppel Certificate Obligation",
            "Force Majeure Clause",
            "Dispute Resolution Mechanism",
            "Holdover Provision (rate & notice)",
            "Demolition / Redevelopment Clause",
            "Default Cure Period (Tenant)",
            "Default Cure Period (Landlord)",
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF file with automatic OCR fallback for scanned documents.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        text = ""
        page_count = 0
        last_error = None

        for extractor_name, extractor in (
            ("pdfplumber", self._extract_with_pdfplumber),
            ("pymupdf", self._extract_with_pymupdf),
            ("pypdf2", self._extract_with_pypdf2),
        ):
            try:
                candidate, page_count = extractor(pdf_path)
            except Exception as exc:
                last_error = exc
                print(f"⚠️  {extractor_name} extraction failed: {exc}")
                continue
            text = (candidate or "").strip()
            print(
                f"   {extractor_name}: {len(text)} chars, "
                f"{len(re.findall(r'[A-Za-z]{{3,}}', text))} words, {page_count} pages"
            )
            if is_extractable_text(text):
                print(f"✓ Digital text extraction succeeded via {extractor_name}")
                return text, page_count

        print(
            f"⚠️  Digital text is not usable "
            f"({len(text)} chars). Running OCR..."
        )
        ocr_error = None
        try:
            text, page_count = self._extract_with_ocr(pdf_path)
            print(f"✓ OCR extraction complete: {len(text)} characters from {page_count} pages")
        except Exception as exc:
            ocr_error = exc
            print(f"⚠️  Classic OCR failed: {exc}")

        if is_extractable_text(text):
            return text, page_count

        print("⚠️  OCR text is still too thin. Transcribing pages with GPT-4o vision...")
        try:
            text, page_count = self._extract_with_gpt_vision(pdf_path)
            print(f"✓ Vision transcription complete: {len(text)} characters from {page_count} pages")
        except Exception as vision_error:
            raise Exception(
                "Could not read the lease. Digital text was unusable, OCR produced "
                f"{len(text)} characters"
                f"{f' ({ocr_error})' if ocr_error else ''}, "
                f"and GPT vision failed: {vision_error}."
            ) from vision_error

        if not is_extractable_text(text):
            preview = normalize_lease_text(text)[:240].replace("\n", " ")
            raise Exception(
                "The PDF is image-based and still did not yield a readable lease body "
                f"({len(text)} characters, {len(word_list(text))} words). "
                f"Text preview: {preview!r}. "
                "Confirm the file is the full lease PDF (not a photo of the cover) "
                "and that your OpenAI key can use gpt-4o vision."
            )

        return text, page_count

    def _extract_with_pypdf2(self, pdf_path: str) -> Tuple[str, int]:
        text = ""
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            page_count = len(pdf_reader.pages)
            for page in pdf_reader.pages:
                text += (page.extract_text() or "") + "\n\n"
        return text.strip(), page_count

    def _extract_with_pdfplumber(self, pdf_path: str) -> Tuple[str, int]:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n\n".join(text_parts).strip(), page_count

    def _extract_with_pymupdf(self, pdf_path: str) -> Tuple[str, int]:
        import fitz

        doc = fitz.open(pdf_path)
        try:
            page_count = doc.page_count
            text = "\n\n".join(page.get_text("text") or "" for page in doc)
        finally:
            doc.close()
        return text.strip(), page_count
    
    def _blank_ratio(self, image) -> float:
        """Share of near-white pixels. 1.0 means a blank page."""
        sample = image.convert("L").resize((160, 160))
        pale = sum(1 for px in sample.getdata() if px >= 245)
        return pale / float(sample.width * sample.height)

    def _prepare_scan_image(self, image):
        from PIL import ImageEnhance, ImageOps

        prepared = ImageOps.exif_transpose(image.convert("RGB"))
        if max(prepared.size) > 2200:
            prepared.thumbnail((2200, 2200))
        if self._blank_ratio(prepared) > 0.97:
            inverted = ImageOps.invert(prepared.convert("RGB"))
            if self._blank_ratio(inverted) < self._blank_ratio(prepared):
                prepared = inverted
        return ImageEnhance.Contrast(prepared).enhance(1.8)

    def _render_pdf_images(self, pdf_path: str, dpi: int = 200):
        """Collect page scans: rendered pages plus embedded images (common for scans)."""
        import fitz
        from PIL import Image

        doc = fitz.open(pdf_path)
        images = []
        try:
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for page_index, page in enumerate(doc):
                page_images = []
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        info = doc.extract_image(xref)
                        embedded = Image.open(io.BytesIO(info["image"])).convert("RGB")
                    except Exception:
                        continue
                    if embedded.width >= 200 and embedded.height >= 200:
                        page_images.append(self._prepare_scan_image(embedded))

                pix = page.get_pixmap(matrix=matrix, alpha=False)
                rendered = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                rendered = self._prepare_scan_image(rendered)
                if not page_images or self._blank_ratio(rendered) < 0.93:
                    page_images.insert(0, rendered)
                if not page_images:
                    page_images.append(rendered)
                print(
                    f"   page {page_index + 1}: {len(page_images)} image(s), "
                    f"blank_ratio={self._blank_ratio(page_images[0]):.2f}"
                )
                images.extend(page_images)
        finally:
            doc.close()
        if not images:
            raise Exception("PDF has no pages or embedded images to read")
        return images

    def _configure_tesseract(self) -> None:
        """Point pytesseract at the usual Windows install path when needed."""
        import pytesseract
        import shutil

        if shutil.which("tesseract"):
            return
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ):
            if os.path.exists(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                return

    def _extract_with_ocr(self, pdf_path: str) -> Tuple[str, int]:
        """OCR via Tesseract on PyMuPDF page images. AWS Textract is optional."""
        images = self._render_pdf_images(pdf_path, dpi=180)
        page_count = len(images)

        aws_key = getattr(config, "AWS_ACCESS_KEY_ID", None)
        if aws_key and not str(aws_key).startswith("your-"):
            try:
                return self._ocr_images_with_textract(images), page_count
            except Exception as textract_error:
                print(f"⚠️  AWS Textract not available: {textract_error}")

        return self._ocr_images_with_tesseract(images), page_count

    def _ocr_images_with_textract(self, images) -> str:
        import boto3

        textract = boto3.client(
            "textract",
            region_name=getattr(config, "AWS_REGION", None) or "us-east-1",
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        extracted_text = ""
        for page_num, image in enumerate(images, 1):
            print(f"   Textract processing page {page_num}/{len(images)}...")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            try:
                response = textract.detect_document_text(Document={"Bytes": buffer.getvalue()})
                page_text = "\n".join(
                    item["Text"] for item in response.get("Blocks", []) if item.get("BlockType") == "LINE"
                )
            except Exception as exc:
                print(f"   ⚠️  Textract failed on page {page_num}: {exc}")
                page_text = ""
            extracted_text += f"\n\n--- Page {page_num} ---\n\n{page_text}"
        return extracted_text.strip()

    def _ocr_images_with_tesseract(self, images) -> str:
        try:
            import pytesseract
        except ImportError as exc:
            raise Exception("Tesseract OCR requires: pip install pytesseract pillow") from exc

        self._configure_tesseract()
        extracted_text = ""
        for page_num, image in enumerate(images, 1):
            print(f"   Tesseract processing page {page_num}/{len(images)}...")
            try:
                page_text = pytesseract.image_to_string(image, lang="eng")
            except Exception as exc:
                print(f"   ⚠️  Tesseract failed on page {page_num}: {exc}")
                page_text = ""
            extracted_text += f"\n\n--- Page {page_num} ---\n\n{page_text}"
        return extracted_text.strip()

    def _extract_with_gpt_vision(self, pdf_path: str, batch_size: int = 1) -> Tuple[str, int]:
        """Transcribe scanned pages with GPT-4o vision, one image at a time."""
        images = self._render_pdf_images(pdf_path, dpi=200)
        page_count = len(images)
        transcribed = []

        for index, image in enumerate(images, 1):
            print(f"   GPT vision transcribing image {index} of {page_count}...")
            buffer = io.BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=80)
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"This is image {index} of {page_count} from a commercial lease. "
                                "Transcribe every visible word verbatim: headings, parties, dates, "
                                "rent, NNN/CAM, options, and clauses. If the image is blank, say BLANK_PAGE. "
                                "Return plain text only."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii"),
                                "detail": "high",
                            },
                        },
                    ],
                }],
                temperature=0,
                max_tokens=4000,
            )
            message = response.choices[0].message
            page_text = (message.content or getattr(message, "refusal", None) or "").strip()
            if not page_text:
                print(f"   ⚠️  Vision returned empty content for image {index}")
                continue
            if page_text.upper() == "BLANK_PAGE":
                print(f"   ⚠️  Vision says image {index} is blank")
                continue
            transcribed.append(f"--- Image {index} ---\n{page_text}")

        if not transcribed:
            raise Exception(
                f"GPT-4o vision saw {page_count} image(s) but transcribed no text. "
                "The PDF pages may be blank, encrypted, or your OpenAI key may not allow vision."
            )
        return "\n\n".join(transcribed).strip(), page_count
    
    def detect_pii(self, text: str) -> List[str]:
        """
        Detect potential PII in text before sending to OpenAI.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            List of PII types detected
        """
        pii_detected = []
        
        # SSN pattern
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            pii_detected.append("Social Security Number")
        
        # Credit card pattern
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', text):
            pii_detected.append("Credit Card Number")
        
        # Bank account pattern
        if re.search(r'\b\d{10,12}\b', text):
            pii_detected.append("Potential Bank Account Number")
        
        return pii_detected
    
    def extract_fields_with_gpt4(self, lease_text: str, property_address: str = None, tenant_name: str = None) -> Dict:
        """
        Extract all 84 lease fields using GPT-4.
        
        Args:
            lease_text: Full text of the lease document
            property_address: Optional property address hint
            tenant_name: Optional tenant name hint
            
        Returns:
            Dictionary of extracted fields with confidence scores
        """
        
        # Determine how much text to send (GPT-4o has 128K token context, ~500K chars)
        # Reserve space for prompt (~3K chars) and response (~15K chars)
        max_lease_chars = 480000
        lease_text_to_send = lease_text[:max_lease_chars] if len(lease_text) > max_lease_chars else lease_text
        
        if len(lease_text) > max_lease_chars:
            print(f"⚠️  Lease text truncated from {len(lease_text):,} to {max_lease_chars:,} characters")
        
        # Build the extraction prompt
        prompt = f"""You are a commercial real estate lease abstraction expert with 20 years of experience. Extract the following information from this lease agreement with precision and accuracy.

For each field, provide:
1. The extracted value (or "NOT FOUND" if not present in the document)
2. A confidence score: 
   - HIGH (90-100%): Field explicitly stated, clear and unambiguous
   - MEDIUM (60-89%): Field implied or calculated, reasonably certain
   - LOW (<60%): Field uncertain, ambiguous, or requires interpretation
3. The source text snippet where you found it (if applicable)
4. Any clarifying notes

IMPORTANT INSTRUCTIONS:
- If a field is genuinely not mentioned in the lease, mark it as "NOT FOUND" with LOW confidence
- Use exact dates in YYYY-MM-DD format
- Include units for all measurements (sq ft, months, %, $, etc.)
- For rent schedules, show the exact monthly amount and ALL rent periods/years if escalating
- For responsibilities, specify "Landlord", "Tenant", or "Shared"
- Extract COMPLETE clauses - do not truncate mid-sentence
- Be thorough but precise - don't invent information
- For long clauses, capture the FULL text in the value field

Fields to extract:
{chr(10).join(f"{i+1}. {field}" for i, field in enumerate(self.lease_fields))}

Context (do NOT copy these into the JSON unless the same fact appears in the lease text below):
{f"Uploader-entered property address: {property_address}" if property_address else ""}
{f"Uploader-entered tenant name: {tenant_name}" if tenant_name else ""}

Lease Document Text ({len(lease_text_to_send):,} characters):
{lease_text_to_send}

Return your response as a JSON object with this exact structure:
{{
  "field_name": {{
    "value": "extracted value or NOT FOUND",
    "confidence": "HIGH|MEDIUM|LOW",
    "source_snippet": "relevant text from lease (first 200 chars)",
    "notes": "any clarifications or reasoning"
  }}
}}

CRITICAL: Return ONLY the JSON object, no additional text or explanation.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert lease abstraction specialist with 20 years of experience in commercial real estate. Extract data accurately and provide confidence scores. Extract COMPLETE clauses without truncation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=16000,  # Increased to allow full extraction of all 84 fields
            )
            
            # Parse the JSON response
            response_text = response.choices[0].message.content
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            extracted_fields = json.loads(response_text)
            
            return extracted_fields
        
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse GPT-4 response as JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"GPT-4 extraction failed: {str(e)}")
    
    def calculate_confidence_score(self, confidence_str: str) -> float:
        """
        Convert confidence string to numeric score.
        
        Args:
            confidence_str: "HIGH", "MEDIUM", "LOW", or "NOT_FOUND"
            
        Returns:
            Numeric confidence score (0.0 to 1.0)
        """
        confidence_map = {
            "HIGH": 0.95,
            "MEDIUM": 0.75,
            "LOW": 0.45,
            "NOT_FOUND": 0.0,
        }
        
        return confidence_map.get(confidence_str.upper(), 0.5)
    
    def extract_and_add_critical_dates(self, lease_id: str, extracted_fields: Dict, supabase_client):
        """
        Extract critical dates from lease fields and add them to critical_dates table.
        
        Args:
            lease_id: Lease UUID
            extracted_fields: Dictionary of extracted lease fields
            supabase_client: Supabase client instance
        """
        from datetime import datetime
        
        # Mapping of field names to critical date types
        critical_date_mappings = {
            "Lease Expiration Date": "Lease Expiration",
            "Renewal Notice Deadline": "Renewal Notice Deadline",
            "Termination Notice Deadline": "Termination Notice Deadline",
            "Early Termination Right": "Termination Option Deadline",
        }
        
        dates_added = 0
        
        for field_name, date_type in critical_date_mappings.items():
            if field_name not in extracted_fields:
                continue
            
            field_data = extracted_fields[field_name]
            
            # Get the value
            if isinstance(field_data, dict):
                value = field_data.get("value", "NOT FOUND")
                confidence = field_data.get("confidence", "LOW")
                notes = field_data.get("notes", "")
            else:
                value = str(field_data)
                confidence = "LOW"
                notes = ""
            
            # Skip if not found or low confidence
            if value == "NOT FOUND" or confidence == "LOW":
                continue
            
            # Try to parse the date
            try:
                # Try different date formats
                date_value = None
                for date_format in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y"]:
                    try:
                        date_value = datetime.strptime(value.split()[0] if " " in value else value, date_format).date()
                        break
                    except:
                        continue
                
                if not date_value:
                    # Try parsing with dateutil if available
                    try:
                        from dateutil import parser
                        date_value = parser.parse(value).date()
                    except:
                        continue
                
                # Add to critical_dates table
                date_record = {
                    "lease_id": lease_id,
                    "date_type": date_type,
                    "date_value": date_value.isoformat(),
                    "description": f"Auto-extracted from lease: {notes}" if notes else f"Auto-extracted from {field_name}",
                    "notification_intervals": [90, 60, 30, 14, 7, 1],
                    "notifications_sent": [],
                    "is_active": True
                }
                
                supabase_client.table("critical_dates").insert(date_record).execute()
                dates_added += 1
                print(f"  ✓ Added {date_type}: {date_value.isoformat()}")
                
            except Exception as e:
                print(f"  ⚠ Could not parse date for {field_name}: {value} ({e})")
                continue
        
        if dates_added == 0:
            print(f"  ℹ️ No critical dates found in extracted fields")
        else:
            print(f"  ✓ Added {dates_added} critical date(s)")
    
    def process_lease(
        self,
        pdf_path: str,
        client_id: str,
        supabase_client,
        property_address: str = None,
        tenant_name: str = None,
        filename: str = None
    ) -> Tuple[str, Dict]:
        """
        Complete end-to-end lease processing pipeline.
        
        Args:
            pdf_path: Path to PDF file
            client_id: Client UUID
            supabase_client: Supabase client instance
            property_address: Optional property address
            tenant_name: Optional tenant name
            filename: Optional filename
            
        Returns:
            Tuple of (lease_id, extracted_fields)
        """
        
        print(f"[1/6] Extracting text from PDF: {pdf_path}")
        lease_text, page_count = self.extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(lease_text)} characters from {page_count} pages")
        if not is_extractable_text(lease_text):
            raise Exception(
                "The PDF did not yield readable lease text. "
                "This is usually a scanned/image PDF. Install Tesseract and Poppler "
                "(or set AWS Textract keys) and re-upload so OCR can run."
            )
        
        print(f"[2/6] Scanning for PII...")
        pii_detected = self.detect_pii(lease_text)
        if pii_detected:
            print(f"⚠ PII detected: {', '.join(pii_detected)}")
        else:
            print(f"✓ No PII detected")
        
        print(f"[3/6] Creating lease record in database...")
        lease_data = {
            "client_id": client_id,
            "filename": filename or os.path.basename(pdf_path),
            "property_address": property_address or "Address not provided",
            "tenant_name": tenant_name or "Tenant not provided",
            "status": "PROCESSING",
            "page_count": page_count,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        lease_response = supabase_client.table("leases").insert(lease_data).execute()
        lease_id = lease_response.data[0]["id"]
        print(f"✓ Lease created with ID: {lease_id}")
        
        print(f"[4/6] Extracting fields with GPT-4 (this takes 20-40 seconds)...")
        extracted_fields = self.extract_fields_with_gpt4(lease_text, property_address, tenant_name)
        found_count = count_found_fields(extracted_fields)
        print(f"✓ GPT returned {len(extracted_fields)} field slots, {found_count} with values")
        if found_count < MIN_FOUND_FIELDS:
            supabase_client.table("leases").update({
                "status": "FLAGGED",
                "extracted_data": extracted_fields,
            }).eq("id", lease_id).execute()
            raise Exception(
                f"Abstraction failed: only {found_count} of {len(self.lease_fields)} "
                "fields had values. The model did not receive a readable lease body "
                "(common with scanned PDFs when OCR is skipped). Re-upload after "
                "installing Tesseract + Poppler or AWS Textract. "
                "Do not treat this lease as extracted."
            )
        
        print(f"[5/6] Saving extracted fields to database...")
        field_number = 1
        for field_name, field_data in extracted_fields.items():
            if isinstance(field_data, dict):
                value = field_data.get("value", "NOT FOUND")
                confidence_str = field_data.get("confidence", "LOW")
                source_snippet = field_data.get("source_snippet", "")
                notes = field_data.get("notes", "")
            else:
                value = str(field_data)
                confidence_str = "LOW"
                source_snippet = ""
                notes = ""
            
            confidence_score = self.calculate_confidence_score(confidence_str)
            
            field_record = {
                "lease_id": lease_id,
                "field_name": field_name,
                "field_number": field_number,
                "raw_value": value,
                "confidence": confidence_str,
                "confidence_score": confidence_score,
                "source_text": source_snippet[:500] if source_snippet else "",
                "notes": notes,
                "reviewed": False,
            }
            
            supabase_client.table("extracted_fields").insert(field_record).execute()
            field_number += 1
        
        print(f"✓ Saved {field_number - 1} fields")
        
        print(f"[6/7] Updating lease status to READY FOR REVIEW...")
        supabase_client.table("leases").update({
            "status": "READY FOR REVIEW",
            "extracted_data": extracted_fields,
        }).eq("id", lease_id).execute()
        print(f"✓ Lease status updated")
        
        print(f"[7/8] Extracting and adding critical dates...")
        try:
            self.extract_and_add_critical_dates(lease_id, extracted_fields, supabase_client)
            print(f"✓ Critical dates extracted and added")
        except Exception as e:
            print(f"⚠ Failed to extract critical dates: {e}")
        
        print(f"[8/8] Seeding Amendment Resolution Graph™ clause history...")
        try:
            from seed_lease_history import seed_base_lease_clause_history
            
            # Get commencement date for history seeding
            commencement_field = extracted_fields.get("Lease Commencement Date", {})
            if isinstance(commencement_field, dict):
                commencement_date = commencement_field.get("value", datetime.utcnow().strftime("%Y-%m-%d"))
            else:
                commencement_date = commencement_field or datetime.utcnow().strftime("%Y-%m-%d")
            
            # Parse date if needed
            if len(commencement_date) > 10:
                commencement_date = commencement_date[:10]
            
            records_created = seed_base_lease_clause_history(
                lease_id=lease_id,
                extracted_fields=extracted_fields,
                lease_commencement_date=commencement_date,
                supabase_client=supabase_client
            )
            print(f"✓ Seeded {records_created} base clause history records")
        except Exception as e:
            print(f"⚠ Failed to seed clause history: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"✓ Processing complete!")
        
        return lease_id, extracted_fields


# Command-line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python extraction_pipeline.py <pdf_path> <client_id> [property_address] [tenant_name]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    client_id = sys.argv[2]
    property_address = sys.argv[3] if len(sys.argv) > 3 else None
    tenant_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    # Initialize Supabase
    from supabase import create_client
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # Run pipeline
    pipeline = LeaseExtractionPipeline()
    
    try:
        lease_id, fields = pipeline.process_lease(
            pdf_path,
            client_id,
            supabase,
            property_address,
            tenant_name
        )
        
        print(f"\n{'='*80}")
        print(f"SUCCESS! Lease ID: {lease_id}")
        print(f"{'='*80}")
        print(f"\nExtracted {len(fields)} fields. Go to the Review page to inspect them.")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"ERROR: {str(e)}")
        print(f"{'='*80}")
        sys.exit(1)
