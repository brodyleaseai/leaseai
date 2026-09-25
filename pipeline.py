# LeaseAI — Ingestion Pipeline v1.0
# Usage: python pipeline.py "C:\path\to\lease.pdf" CLIENT-UUID

import os
import re
import sys
import fitz
from openai import OpenAI
from supabase import create_client
import config

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
db = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

PROMPT_PATH = os.path.join(os.path.dirname(__file__),
                           "leaseai-master-extraction-prompt-v1.0.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    EXTRACTION_PROMPT = f.read()

FIELD_NAMES = [
    "Landlord Legal Name",
    "Tenant Legal Name",
    "Property Civic Address",
    "Lease Commencement Date",
    "Lease Expiration Date",
    "Lease Term (total months)",
    "Base Rent Year 1 monthly",
    "Base Rent Year 2 monthly",
    "Base Rent Year 3 monthly",
    "Annual Rent Escalation Type",
    "Annual Escalation Rate",
    "Free Rent Period",
    "Security Deposit",
    "Number of Renewal Options",
    "Renewal Option Term Length",
    "Renewal Notice Deadline",
    "Renewal Rent Basis",
    "CAM Operating Cost Charges",
    "CAM Annual Increase Cap",
    "Tenant Improvement Allowance",
    "Permitted Use",
    "Governing Law Jurisdiction",
    "Holdover Provision",
    "Parking",
    "HVAC Responsibility",
]

PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "Social Insurance / SSN pattern"),
    (r"\b\d{16}\b",             "16-digit number (possible card)"),
    (r"\b[A-Z]{2}\d{6}\b",      "Passport number pattern"),
]


def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    pages = len(doc)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text, pages


def pii_scan(text):
    flags = []
    for pattern, label in PII_PATTERNS:
        hits = re.findall(pattern, text)
        if hits:
            flags.append(f"{label} — {len(hits)} instance(s) found")
    return flags


def normalize_confidence(raw):
    raw = raw.upper().strip()
    if "NOT" in raw and "FOUND" in raw: return "NOT_FOUND"
    if "BLANK"       in raw:            return "BLANK"
    if "CONDITIONAL" in raw:            return "CONDITIONAL"
    if "HIGH"        in raw:            return "HIGH"
    if "MEDIUM"      in raw:            return "MEDIUM"
    if "LOW"         in raw:            return "LOW"
    return "MEDIUM"


def parse_response(text):
    fields = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if "|" not in line or ":" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        colon = parts[0].index(":")
        field_name = parts[0][:colon].strip()
        raw_value  = parts[0][colon+1:].strip()
        confidence = normalize_confidence(
            parts[1].replace("CONFIDENCE:", "").strip()
        )
        source = "|".join(parts[2:]).replace("SOURCE:", "").strip()
        fields.append({
            "field_name":   field_name,
            "raw_value":    raw_value,
            "confidence":   confidence,
            "source_quote": source,
        })
    return fields


def call_gpt4o(lease_text):
    full_prompt = (
        f"{EXTRACTION_PROMPT}"
        f"\n\n--- LEASE DOCUMENT ---\n\n"
        f"{lease_text}"
    )
    response = openai_client.chat.completions.create(
        model=config.GPT_MODEL,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def create_lease_record(client_id, file_name, page_count, file_path):
    row = db.table("leases").insert({
        "client_id":  client_id,
        "file_name":  file_name,
        "file_path":  file_path,
        "page_count": page_count,
        "status":     "extracting",
    }).execute()
    return row.data[0]["id"]


def write_fields(lease_id, fields):
    rows = []
    for i, f in enumerate(fields):
        rows.append({
            "lease_id":     lease_id,
            "field_number": i + 1,
            "field_name":   f.get("field_name",
                            FIELD_NAMES[i] if i < len(FIELD_NAMES) else f"Field {i+1}"),
            "raw_value":    f.get("raw_value", ""),
            "confidence":   f.get("confidence", "MEDIUM"),
            "source_quote": f.get("source_quote", ""),
            "is_reviewed":  False,
        })
    db.table("extracted_fields").insert(rows).execute()


def set_status(lease_id, status):
    db.table("leases").update({"status": status}).eq("id", lease_id).execute()


def run(pdf_path, client_id):
    name = os.path.basename(pdf_path)
    sep  = "=" * 60

    print(f"\n{sep}")
    print(f"  LeaseAI Pipeline — {name}")
    print(f"{sep}\n")

    print("Step 1/5 — Extracting text from PDF...")
    text, pages = extract_pdf_text(pdf_path)
    print(f"           OK — {pages} pages | {len(text):,} characters")

    print("Step 2/5 — Scanning for PII...")
    flags = pii_scan(text)
    if flags:
        for fl in flags:
            print(f"           WARNING: {fl}")
    else:
        print("           OK — No PII patterns detected")

    print("Step 3/5 — Creating lease record in database...")
    lease_id = create_lease_record(client_id, name, pages, pdf_path)
    print(f"           OK — Lease ID: {lease_id}")

    print("Step 4/5 — Sending to GPT-4o (this takes 20-40 seconds)...")
    raw = call_gpt4o(text)
    fields = parse_response(raw)
    print(f"           OK — {len(fields)} fields extracted")

    print("Step 5/5 — Writing fields to database...")
    write_fields(lease_id, fields)
    set_status(lease_id, "review")
    print("           OK — All fields saved\n")

    counts = {}
    for f in fields:
        c = f.get("confidence", "MEDIUM")
        counts[c] = counts.get(c, 0) + 1

    print("  EXTRACTION SUMMARY")
    print(f"  {'─'*38}")
    for label in ["HIGH","MEDIUM","LOW","NOT_FOUND","BLANK","CONDITIONAL"]:
        n = counts.get(label, 0)
        if n:
            print(f"  {label:<18} {n}")
    print(f"  {'─'*38}")
    print(f"  Status:   READY FOR REVIEW")
    print(f"  Lease ID: {lease_id}")
    print(f"\n{sep}\n")
    return lease_id


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pipeline.py \"C:\\path\\to\\lease.pdf\" CLIENT-UUID")
        sys.exit(1)
    pdf_path  = sys.argv[1]
    client_id = sys.argv[2]
    if not os.path.exists(pdf_path):
        print(f"Error: File not found — {pdf_path}")
        sys.exit(1)
    run(pdf_path, client_id)
