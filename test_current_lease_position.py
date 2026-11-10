"""Current Lease Position: extracted vs calculated vs review required."""

import unittest
from io import BytesIO

from amendment_report import build_amendment_resolution_model
from current_lease_position import (
    STATUS_AMENDED,
    STATUS_CALCULATED,
    STATUS_EXTRACTED,
    STATUS_REVIEW,
    build_current_lease_position,
    generate_current_lease_position_pdf,
    position_filename,
)


def _rows(model):
    return {row["field"]: row for row in model["rows"]}


def _pdf_text(model):
    pdf_bytes = generate_current_lease_position_pdf(model)
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages)


class OriginalLeaseTests(unittest.TestCase):
    def test_extracted_terms_are_not_labeled_calculated(self):
        resolution = build_amendment_resolution_model(
            {"property_address": "100 Main", "tenant_name": "Original Tenant"},
            [],
            [
                {
                    "clause_type": "Base Rent",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": "$8,000.00 per month",
                    "is_current": True,
                    "effective_from": "2024-01-01",
                },
                {
                    "clause_type": "Premises Description",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": "10,000 sq ft",
                    "is_current": True,
                    "effective_from": "2024-01-01",
                },
                {
                    "clause_type": "Permitted Use",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": "Office",
                    "is_current": True,
                    "effective_from": "2024-01-01",
                },
            ],
            as_of="2026-11-10",
        )
        model = build_current_lease_position(resolution)
        rows = _rows(model)
        self.assertEqual(rows["Base Rent (stated)"]["status"], STATUS_EXTRACTED)
        self.assertEqual(rows["Premises / RSF"]["status"], STATUS_EXTRACTED)
        self.assertNotIn("Permitted Use", rows)
        self.assertEqual(model["value"]["deliverable_name"], "Current Lease Position")
        self.assertEqual(position_filename(model), "Current-Lease-Position-Original-Tenant-2026-11-10.pdf")


class CalculatedRentTests(unittest.TestCase):
    def test_rate_times_rsf_is_calculated_not_stated(self):
        third_rent = (
            "Base Rent shall be calculated using the then-applicable rate multiplied by 12,800 "
            "rentable square feet. The applicable rate from April 1, 2028 to March 31, 2029 remains $28.07."
        )
        resolution = build_amendment_resolution_model(
            {
                "property_address": "8800 Riverfront Dr, Richmond, BC",
                "tenant_name": "Juniper Coast Analytics Inc.",
            },
            [
                {
                    "amendment_id": "amd-3",
                    "amendment_number": 3,
                    "amendment_date": "2028-09-20",
                    "effective_date": "2028-10-01",
                    "status": "READY FOR REVIEW",
                    "modified_clauses": ["Base Rent", "Premises Description"],
                }
            ],
            [
                {
                    "clause_type": "Base Rent",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": "$24,000",
                    "is_current": False,
                    "effective_from": "2025-04-01",
                },
                {
                    "clause_type": "Base Rent",
                    "version_number": 3,
                    "source_document_type": "AMENDMENT",
                    "source_document_id": "amd-3",
                    "clause_value": third_rent,
                    "is_current": True,
                    "effective_from": "2028-10-01",
                    "modification_type": "MODIFIES",
                },
                {
                    "clause_type": "Premises Description",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": "13,500 sq ft",
                    "is_current": False,
                    "effective_from": "2025-04-01",
                },
                {
                    "clause_type": "Premises Description",
                    "version_number": 3,
                    "source_document_type": "AMENDMENT",
                    "source_document_id": "amd-3",
                    "clause_value": "the Premises shall comprise 12,800 rentable square feet.",
                    "is_current": True,
                    "effective_from": "2028-10-01",
                    "modification_type": "MODIFIES",
                },
            ],
            as_of="2028-10-01",
            amendment_clauses=[
                {
                    "amendment_id": "amd-3",
                    "clause_type": "Base Rent",
                    "modification_type": "MODIFIES",
                    "original_value": "$24,000",
                    "new_value": third_rent,
                    "effective_date": "2028-10-01",
                },
                {
                    "amendment_id": "amd-3",
                    "clause_type": "Premises Description",
                    "modification_type": "MODIFIES",
                    "original_value": "13,500 sq ft",
                    "new_value": "the Premises shall comprise 12,800 rentable square feet.",
                    "effective_date": "2028-10-01",
                },
            ],
        )
        model = build_current_lease_position(resolution)
        rows = _rows(model)
        self.assertEqual(rows["Base Rent (stated)"]["status"], STATUS_AMENDED)
        self.assertEqual(rows["Annual Base Rent"]["status"], STATUS_CALCULATED)
        self.assertEqual(rows["Monthly Base Rent"]["status"], STATUS_CALCULATED)
        self.assertEqual(rows["Annual Base Rent"]["current_value"], "$359,296.00")
        self.assertEqual(rows["Monthly Base Rent"]["current_value"], "$29,941.33")
        self.assertIn("12,800", rows["Annual Base Rent"]["calculation"])
        self.assertIn("$28.07", rows["Annual Base Rent"]["calculation"])
        self.assertIn("not a dollar amount expressly stated", rows["Annual Base Rent"]["notes"])
        text = _pdf_text(model)
        self.assertIn("Current Lease Position", text)
        self.assertIn("Calculated", text)
        self.assertIn("$29,941.33", text)
        self.assertIn("not a legal opinion", text.lower())
        self.assertIn("12,800", text)


class ReviewFlagTests(unittest.TestCase):
    def test_rate_without_rsf_is_review_required(self):
        resolution = build_amendment_resolution_model(
            {"property_address": "Ambiguous Plaza", "tenant_name": "Review Tenant"},
            [
                {
                    "amendment_id": "amd-1",
                    "amendment_number": 1,
                    "amendment_date": "2027-04-01",
                    "modified_clauses": ["Base Rent"],
                }
            ],
            [
                {
                    "clause_type": "Base Rent",
                    "version_number": 1,
                    "source_document_type": "AMENDMENT",
                    "source_document_id": "amd-1",
                    "clause_value": "Base rent shall be $30.10 per square foot per annum.",
                    "is_current": True,
                    "effective_from": "2027-04-01",
                    "modification_type": "MODIFIES",
                }
            ],
            as_of="2027-04-01",
        )
        model = build_current_lease_position(resolution)
        rows = _rows(model)
        self.assertEqual(rows["Annual Base Rent"]["status"], STATUS_REVIEW)
        self.assertTrue(any("RSF is missing" in flag for flag in model["review_flags"]))

    def test_stated_total_mismatch_is_review_required(self):
        resolution = build_amendment_resolution_model(
            {"property_address": "Mismatch Center", "tenant_name": "Mismatch Tenant"},
            [],
            [
                {
                    "clause_type": "Base Rent",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": (
                        "Annual Base Rent is $500,000 per annum at $30.10 per rentable square foot "
                        "per annum for the entire Premises comprising 19,000 rentable square feet."
                    ),
                    "is_current": True,
                    "effective_from": "2027-04-01",
                },
                {
                    "clause_type": "Premises Description",
                    "version_number": 0,
                    "source_document_type": "BASE_LEASE",
                    "clause_value": "19,000 rentable square feet",
                    "is_current": True,
                    "effective_from": "2027-04-01",
                },
            ],
            as_of="2027-04-01",
        )
        model = build_current_lease_position(resolution)
        rows = _rows(model)
        self.assertEqual(rows["Annual Base Rent"]["current_value"], "$571,900.00")
        self.assertEqual(rows["Annual Base Rent"]["status"], STATUS_REVIEW)
        self.assertTrue(any("does not match" in flag for flag in model["review_flags"]))


if __name__ == "__main__":
    unittest.main()
