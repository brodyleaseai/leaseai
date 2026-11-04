"""Tests for the client Amendment Resolution report."""

import unittest
from io import BytesIO

from amendment_report import (
    abstract_filename,
    amendment_label,
    build_amendment_resolution_model,
    generate_amendment_resolution_pdf,
    summarize_clause_change,
)


LEASE = {
    "id": "lease-route2",
    "property_address": "Route 2 Retail Center",
    "tenant_name": "Route 2 Tenant LLC",
}

HISTORY = [
    {
        "clause_type": "Base Rent",
        "version_number": 0,
        "source_document_type": "BASE_LEASE",
        "clause_value": "$8,550.08 per month",
        "is_current": False,
        "effective_from": "2023-01-01",
        "modification_type": None,
    },
    {
        "clause_type": "Base Rent",
        "version_number": 1,
        "source_document_type": "AMENDMENT",
        "source_document_id": "amd-1",
        "clause_value": "$9,000.00 per month",
        "is_current": True,
        "effective_from": "2024-06-01",
        "modification_type": "MODIFIES",
    },
    {
        "clause_type": "Permitted Use",
        "version_number": 0,
        "source_document_type": "BASE_LEASE",
        "clause_value": "Retail sales",
        "is_current": True,
        "effective_from": "2023-01-01",
        "modification_type": None,
    },
]

AMENDMENTS = [
    {
        "amendment_id": "amd-1",
        "amendment_number": 1,
        "amendment_date": "2024-06-01",
        "status": "READY FOR REVIEW",
        "modified_clauses": ["Base Rent"],
    }
]


class ModelTests(unittest.TestCase):
    def test_separates_changed_and_original_governing_clauses(self):
        model = build_amendment_resolution_model(LEASE, AMENDMENTS, HISTORY, as_of="2026-11-03")
        self.assertEqual(model["property_address"], "Route 2 Retail Center")
        self.assertEqual(len(model["amendments"]), 1)
        self.assertEqual([c["clause_type"] for c in model["changed_clauses"]], ["Base Rent"])
        self.assertEqual([c["clause_type"] for c in model["unchanged_clauses"]], ["Permitted Use"])
        rent = model["changed_clauses"][0]
        self.assertEqual(rent["original_value"], "$8,550.08 per month")
        self.assertEqual(rent["governing_value"], "$9,000.00 per month")
        self.assertEqual(rent["governing_source"], "AMENDMENT")
        self.assertEqual(rent["governing_label"], "Amendment No. 1 (2024-06-01)")
        self.assertEqual(rent["change_summary"], "$8,550.08 → $9,000.00")
        self.assertEqual(rent["change_number"], 1)
        value = model["value"]
        self.assertEqual(value["deliverable_name"], "Amendment Resolution Abstract")
        self.assertEqual(value["amendments_resolved"], 1)
        self.assertEqual(value["clauses_superseded"], 1)
        self.assertEqual(value["clauses_still_original"], 1)
        self.assertEqual(value["clauses_tracked"], 2)
        self.assertEqual(value["prepared_for"], "Route 2 Tenant LLC")
        self.assertIn("controlling lease language", value["statement"])

    def test_prepared_for_override_and_filename(self):
        model = build_amendment_resolution_model(
            LEASE, AMENDMENTS, HISTORY, as_of="2026-11-03", prepared_for="Northland Capital"
        )
        self.assertEqual(model["value"]["prepared_for"], "Northland Capital")
        self.assertEqual(
            abstract_filename(model),
            "Amendment-Resolution-Abstract-Northland-Capital-2026-11-03.pdf",
        )

    def test_empty_history_is_safe(self):
        model = build_amendment_resolution_model(LEASE, [], [])
        self.assertEqual(model["changed_clauses"], [])
        self.assertEqual(model["unchanged_clauses"], [])
        self.assertEqual(model["amendments"], [])
        self.assertEqual(model["value"]["amendments_resolved"], 0)

    def test_summarize_clause_change_matches_co_diagnostics_style(self):
        self.assertEqual(summarize_clause_change("5%", "cap shall not exceed 3.5% per annum"), "5% → 3.5%")
        self.assertEqual(
            summarize_clause_change(
                "holdover rent shall be 150% of the last active month's Base Rent, requiring a minimum of 30 days prior notice.",
                "Holdover Provision Rate shall be adjusted downward from 150% to 125%",
            ),
            "150% → 125%",
        )
        self.assertEqual(
            summarize_clause_change("$2,500.00", "reduced from $2,500.00 down to $1,500.00"),
            "$2,500.00 → $1,500.00",
        )
        self.assertEqual(amendment_label(1, "2025-01-02"), "Amendment No. 1 (2025-01-02)")


class PdfTests(unittest.TestCase):
    def test_pdf_contains_original_and_governing_language(self):
        model = build_amendment_resolution_model(LEASE, AMENDMENTS, HISTORY, as_of="2026-11-03")
        pdf_bytes = generate_amendment_resolution_pdf(model)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)

        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Amendment Resolution Abstract", text)
        self.assertIn("controlling lease language", text)
        self.assertIn("Route 2 Retail Center", text)
        self.assertIn("$8,550.08", text)
        self.assertIn("$9,000.00", text)
        self.assertIn("Permitted Use", text)
        self.assertIn("Schedule A", text)
        self.assertIn("Amendment No. 1", text)
        self.assertIn("What changed", text)
        self.assertIn("$8,550.08 → $9,000.00", text)
        self.assertIn("Change 1 of 1", text)
        self.assertIn("Exhibit A", text)
        self.assertIn("still governed by the original lease", text.lower())
        self.assertIn("not a legal opinion", text.lower())


if __name__ == "__main__":
    unittest.main()
