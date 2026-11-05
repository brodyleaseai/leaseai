"""Source citations on client reports."""

import unittest
from io import BytesIO

from lease_report import generate_lease_abstract_pdf
from report_sources import (
    clause_source,
    detect_page,
    document_label,
    field_source,
    fields_from_review_rows,
    format_source_line,
    source_exhibit_rows,
    with_page_prefix,
)


class HelperTests(unittest.TestCase):
    def test_detect_page_from_explicit_and_excerpt(self):
        self.assertEqual(detect_page("", 12), "12")
        self.assertEqual(detect_page("Page 7. Tenant shall pay Base Rent"), "7")
        self.assertEqual(detect_page("--- Page 14 --- Base Rent"), "14")
        self.assertIsNone(detect_page("no page here"))

    def test_document_label_names_amendments(self):
        self.assertEqual(document_label("BASE_LEASE"), "Original lease")
        self.assertEqual(
            document_label("AMENDMENT", 2, "2027-02-12"),
            "Amendment No. 2 (2027-02-12)",
        )

    def test_field_source_keeps_gpt_snippet_and_page(self):
        source = field_source(
            {
                "value": "$9,000.00 per month",
                "source_snippet": "Page 4. Tenant shall pay Base Rent of $9,000.00 per month.",
                "confidence": "HIGH",
            }
        )
        self.assertEqual(source["page"], "4")
        self.assertIn("$9,000.00", source["excerpt"])
        self.assertIn("p. 4", format_source_line(source))
        self.assertIn("Original lease", format_source_line(source))

    def test_fields_from_review_rows_do_not_drop_source_text(self):
        mapped = fields_from_review_rows(
            [
                {
                    "field_name": "Base Rent",
                    "raw_value": "$8,550.08",
                    "reviewed_value": "$9,000.00",
                    "confidence": "HIGH",
                    "source_text": "Page 4. Tenant shall pay Base Rent of $9,000.00 per month.",
                }
            ]
        )
        self.assertEqual(mapped["Base Rent"]["value"], "$9,000.00")
        self.assertIn("Page 4", mapped["Base Rent"]["source_text"])
        exhibit = source_exhibit_rows(mapped)
        self.assertEqual(exhibit[0]["page"], "4")
        self.assertIn("$9,000.00", exhibit[0]["excerpt"])

    def test_derived_clause_names_parent(self):
        source = clause_source(
            {
                "clause_type": "Rent Schedule",
                "governing_value": "April 1, 2028–March 31, 2029: $29,941.33/month",
                "governing_label": "Amendment No. 3 (2028-09-20)",
                "governing_source_text": (
                    "Page 2. Base Rent shall be calculated using the then-applicable "
                    "rate multiplied by 12,800 rentable square feet."
                ),
                "linked_from": "Base Rent",
            },
            "governing",
        )
        line = format_source_line(source)
        self.assertIn("Amendment No. 3", line)
        self.assertIn("derived from Base Rent", line)
        self.assertIn("12,800", line)

    def test_with_page_prefix_stores_page_in_existing_column(self):
        self.assertEqual(
            with_page_prefix("Tenant shall pay Base Rent of $9,000", 4),
            "Page 4. Tenant shall pay Base Rent of $9,000",
        )
        self.assertEqual(
            with_page_prefix("Page 4. Tenant shall pay Base Rent of $9,000", 4),
            "Page 4. Tenant shall pay Base Rent of $9,000",
        )


class LeaseAbstractPdfTests(unittest.TestCase):
    def test_pdf_includes_source_exhibit(self):
        pdf_bytes = generate_lease_abstract_pdf(
            {
                "property_address": "8800 Riverfront Dr",
                "tenant_name": "Juniper Coast Analytics Inc.",
            },
            {
                "Base Rent": {
                    "value": "$9,000.00 per month",
                    "confidence": "HIGH",
                    "source_text": "Page 4. Tenant shall pay Base Rent of $9,000.00 per month.",
                },
                "Premises Square Footage (RSF)": {
                    "value": "13,500",
                    "confidence": "HIGH",
                    "source_snippet": "the Premises comprise 13,500 rentable square feet",
                },
            },
        )
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages)
        self.assertIn("Source Exhibit", text)
        self.assertIn("Page 4", text)
        self.assertIn("$9,000.00", text)
        self.assertIn("13,500 rentable square feet", text)
        self.assertIn("auditor, lender, or buyer", text.lower())


if __name__ == "__main__":
    unittest.main()
