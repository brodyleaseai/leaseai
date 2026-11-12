"""Source excerpts must be stored so abstract reports can cite the lease."""

import unittest

from extraction_pipeline import (
    normalize_extracted_fields,
    source_excerpt_from_field,
    with_page_prefix,
)


class ExcerptHelperTests(unittest.TestCase):
    def test_prefers_source_snippet(self):
        excerpt = source_excerpt_from_field(
            {
                "value": "$39,750.00",
                "confidence": "HIGH",
                "source_snippet": "Base Rent of $39,750.00 per month",
                "source_quote": "ignore me",
            }
        )
        self.assertEqual(excerpt, "Base Rent of $39,750.00 per month")

    def test_falls_back_to_source_quote(self):
        excerpt = source_excerpt_from_field(
            {
                "value": "18,000 RSF",
                "confidence": "HIGH",
                "source_quote": "comprising 18,000 rentable square feet",
            }
        )
        self.assertEqual(excerpt, "comprising 18,000 rentable square feet")

    def test_not_found_is_not_treated_as_an_excerpt(self):
        self.assertEqual(
            source_excerpt_from_field({"value": "NOT FOUND", "source_snippet": "NOT FOUND"}),
            "",
        )


class PagePrefixTests(unittest.TestCase):
    def test_adds_page_when_missing(self):
        self.assertEqual(
            with_page_prefix("Tenant shall pay Base Rent", 7),
            "Page 7. Tenant shall pay Base Rent",
        )

    def test_does_not_duplicate_page(self):
        self.assertEqual(
            with_page_prefix("Page 7. Tenant shall pay Base Rent", 7),
            "Page 7. Tenant shall pay Base Rent",
        )


class NormalizeTests(unittest.TestCase):
    def test_copies_excerpt_onto_source_text_for_reports(self):
        normalized = normalize_extracted_fields(
            {
                "Base Rent Year 1 (monthly)": {
                    "value": "$39,750.00",
                    "confidence": "HIGH",
                    "source_snippet": "monthly Base Rent of $39,750.00",
                    "source_page": "12",
                },
                "CAM Exclusions": {
                    "value": "NOT FOUND",
                    "confidence": "LOW",
                },
            }
        )
        rent = normalized["Base Rent Year 1 (monthly)"]
        self.assertTrue(rent["source_text"].startswith("Page 12."))
        self.assertIn("$39,750.00", rent["source_text"])
        self.assertEqual(normalized["CAM Exclusions"].get("source_text"), None)


if __name__ == "__main__":
    unittest.main()
