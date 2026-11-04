"""Tests for the ASC 842 / IFRS 16 compliance report."""

import json
import unittest
from io import BytesIO

from asc842_report import (
    build_asc842_report_model,
    build_asc842_report_package,
    generate_asc842_compliance_pdf,
    journal_entry_rows,
    lease_inputs_from_calculation,
    report_filename,
)


LEASE = {
    "property_address": "3215 S 300 W, Salt Lake City, Utah",
    "tenant_name": "CO-DIAGNOSTICS, INC.",
}

INPUTS = {
    "commencement_date": "2024-01-01",
    "end_date": "2026-12-31",
    "monthly_payment": 2500,
    "discount_rate": 0.05,
    "initial_direct_costs": 1000,
    "lease_incentives": 500,
    "prepayments": 2500,
    "annual_rent_increases": 0.03,
}


def _pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages)


class ModelTests(unittest.TestCase):
    def test_rebuilds_from_saved_calculation_json(self):
        calc = {
            "calculation_data": json.dumps(INPUTS),
            "discount_rate": 5.0,
            "lease_classification": "OPERATING",
        }
        rebuilt = lease_inputs_from_calculation(calc)
        self.assertEqual(rebuilt["monthly_payment"], 2500)
        self.assertEqual(rebuilt["discount_rate"], 0.05)

    def test_normalizes_journal_lines(self):
        rows = journal_entry_rows(
            {
                "lines": [
                    {"account": "ROU Asset - Lease", "debit": 100, "credit": 0},
                    {"account": "Lease Liability", "debit": 0, "credit": 100},
                ]
            }
        )
        self.assertEqual(rows[0]["debit"], 100)
        self.assertEqual(rows[1]["credit"], 100)

    def test_model_has_client_measurements(self):
        model = build_asc842_report_model(LEASE, lease_inputs=INPUTS, prepared_for="Controller")
        self.assertEqual(model["prepared_for"], "Controller")
        self.assertGreater(model["initial_liability"], 0)
        self.assertGreater(model["initial_rou_asset"], 0)
        self.assertEqual(model["classification"], "OPERATING")
        self.assertTrue(model["liability_schedule"])
        self.assertTrue(model["monthly_journal_entries"])
        self.assertIn("maturity_analysis", model["disclosures"])
        self.assertGreater(model["disclosures"]["balance_sheet_impact"]["non_current_liability"], 0)
        self.assertAlmostEqual(
            model["disclosures"]["balance_sheet_impact"]["current_liability"]
            + model["disclosures"]["balance_sheet_impact"]["non_current_liability"],
            model["initial_liability"],
            places=2,
        )
        self.assertEqual(
            report_filename(model),
            f"ASC842-IFRS16-Compliance-Report-Controller-{model['as_of']}.pdf",
        )


class PdfTests(unittest.TestCase):
    def test_pdf_contains_classification_and_schedules(self):
        package = build_asc842_report_package(LEASE, lease_inputs=INPUTS, prepared_for="Controller")
        self.assertTrue(package["pdf_bytes"].startswith(b"%PDF"))
        self.assertIn("opening_balance", package["liability_csv"])
        text = _pdf_text(package["pdf_bytes"])
        self.assertIn("ASC 842 / IFRS 16 Compliance Report", text)
        self.assertIn("CO-DIAGNOSTICS, INC.", text)
        self.assertIn("3215 S 300 W", text)
        self.assertIn("OPERATING", text)
        self.assertIn("Initial measurement", text)
        self.assertIn("Maturity analysis", text)
        self.assertIn("journal entry", text.lower())
        self.assertIn("not a legal opinion", text.lower())
        self.assertGreater(len(package["liability_csv"].splitlines()), 12)
        self.assertGreater(len(package["rou_csv"].splitlines()), 12)


if __name__ == "__main__":
    unittest.main()
