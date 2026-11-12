"""Source excerpts must be stored so abstract reports can cite the lease."""

import unittest

from extraction_pipeline import (
    attach_missing_excerpts,
    find_excerpt_in_lease,
    normalize_extracted_fields,
    source_excerpt_from_field,
    with_page_prefix,
)
from lease_header import display_property_address, display_tenant_name, lease_header_updates


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


class LeaseTextBackfillTests(unittest.TestCase):
    def test_quotes_surrounding_text_and_page(self):
        lease_text = (
            "--- Page 3 ---\n"
            "The Tenant is Cobalt Ridge Consulting Inc., a British Columbia company.\n"
            "Landlord is Alder Peak Properties Ltd.\n"
        )
        excerpt = find_excerpt_in_lease(lease_text, "Cobalt Ridge Consulting Inc.")
        self.assertIn("Cobalt Ridge Consulting Inc.", excerpt)
        self.assertTrue(excerpt.startswith("Page 3."))

    def test_fills_empty_gpt_snippet(self):
        lease_text = "--- Page 1 ---\nBase Rent is $12,041.67 per month commencing on the Rent Commencement Date."
        filled = attach_missing_excerpts(
            lease_text,
            {
                "Base Rent Year 1 (monthly)": {
                    "value": "$12,041.67",
                    "confidence": "HIGH",
                }
            },
        )
        self.assertIn("$12,041.67", filled["Base Rent Year 1 (monthly)"]["source_text"])
        self.assertIn("Page 1.", filled["Base Rent Year 1 (monthly)"]["source_text"])


class HeaderTests(unittest.TestCase):
    def test_replaces_bulk_placeholder_tenant(self):
        fields = {
            "Tenant Legal Name": {"value": "Cobalt Ridge Consulting Inc.", "confidence": "HIGH"},
            "Property Civic Address": {
                "value": "Suite 410, 880 West Pender Street, Vancouver, BC V6C 2T8"
            },
        }
        self.assertEqual(
            display_tenant_name({"tenant_name": "To be reviewed"}, fields),
            "Cobalt Ridge Consulting Inc.",
        )
        self.assertEqual(
            display_property_address(
                {"property_address": "01 Commercial Office Lease Alder Peak"},
                fields,
            ),
            "Suite 410, 880 West Pender Street, Vancouver, BC V6C 2T8",
        )
        self.assertEqual(
            lease_header_updates(fields)["tenant_name"],
            "Cobalt Ridge Consulting Inc.",
        )


if __name__ == "__main__":
    unittest.main()
