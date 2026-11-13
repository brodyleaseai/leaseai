"""Synthetic Northridge lease + CAM statement are extractable and match the engine."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "cam"))

import scenario as S  # noqa: E402
from cam_engine import (  # noqa: E402
    analyze_line_items,
    assemble_cam_statement,
    calculate_cam_charges,
    defaults_from_parsed_statement,
    detect_discrepancies,
)
from cam_gpt_extractor import extract_text_from_pdf  # noqa: E402


def _pdf_text(path: Path) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


class FixtureFilesTests(unittest.TestCase):
    def test_lease_pdf_exists(self):
        self.assertTrue(S.LEASE_PDF.is_file(), f"missing {S.LEASE_PDF}")
        self.assertTrue(S.LEASE_PDF.read_bytes().startswith(b"%PDF"))

    def test_statement_pdf_exists(self):
        self.assertTrue(S.STATEMENT_PDF.is_file(), f"missing {S.STATEMENT_PDF}")
        self.assertTrue(S.STATEMENT_PDF.read_bytes().startswith(b"%PDF"))


class LeaseTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _pdf_text(S.LEASE_PDF)

    def test_parties_and_premises_are_selectable_text(self):
        for needle in (
            S.LANDLORD_NAME,
            S.TENANT_NAME,
            S.PROPERTY_ADDRESS,
            "12,500",
            "100,000",
            "12.50%",
            "CAM Base Year",
            "CAM Annual Increase Cap",
            "CAM Exclusions",
            "Tenant Audit Right",
            "capital improvements",
            "roof replacement",
            "debt service",
        ):
            self.assertIn(needle, self.text, f"lease PDF missing {needle!r}")

    def test_watermark_present(self):
        self.assertIn("SYNTHETIC TEST DOCUMENT", self.text)


class StatementTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _pdf_text(S.STATEMENT_PDF)

    def test_totals_and_planted_exclusions_are_selectable_text(self):
        for needle in (
            S.LANDLORD_NAME,
            S.TENANT_NAME,
            "1,200,000.00",
            "150,000.00",
            "March 15, 2026",
            "Roof replacement",
            "Structural steel",
            "Depreciation expense",
            "debt service",
            "$180,000.00",
            "Accounting / CAM Reconciliations",
        ):
            self.assertIn(needle, self.text, f"statement PDF missing {needle!r}")
        self.assertNotIn("<br", self.text)


class EngineMathTests(unittest.TestCase):
    def test_building_total_is_exactly_1_2_million(self):
        self.assertEqual(S.BUILDING_TOTAL_CHARGES, 1200000.00)
        self.assertEqual(S.TENANT_SHARE_BILLED, 150000.00)

    def test_cap_reduces_share_to_105000(self):
        result = calculate_cam_charges(S.BUILDING_TOTAL_CHARGES, S.PROVISIONS_FOR_ENGINE)
        self.assertTrue(result["cam_cap_applied"])
        self.assertEqual(result["calculated_tenant_share"], S.CALCULATED_TENANT_SHARE)

    def test_none_prorata_falls_back_to_square_footage(self):
        result = calculate_cam_charges(S.BUILDING_TOTAL_CHARGES, {
            "tenant_prorata_share": None,
            "tenant_square_footage": S.PREMISES_RSF,
            "building_square_footage": S.BUILDING_RSF,
            "has_cam_cap": True,
            "cam_cap_percentage": S.CAM_CAP_PERCENTAGE,
            "cam_base_amount": S.CAM_BASE_AMOUNT,
        })
        self.assertEqual(result["calculated_tenant_share"], S.CALCULATED_TENANT_SHARE)

    def test_none_cap_fields_do_not_crash(self):
        result = calculate_cam_charges(S.BUILDING_TOTAL_CHARGES, {
            "tenant_prorata_share": None,
            "has_cam_cap": True,
            "cam_cap_percentage": None,
            "cam_base_amount": None,
        })
        self.assertEqual(result["calculated_tenant_share"], 0.0)
        self.assertFalse(result["cam_cap_applied"])

    def test_overcharge_is_critical(self):
        analysis = detect_discrepancies(
            S.TENANT_SHARE_BILLED,
            S.CALCULATED_TENANT_SHARE,
            [],
        )
        self.assertEqual(analysis["variance_amount"], S.VARIANCE_OVERCHARGE)
        self.assertEqual(analysis["severity"], S.VARIANCE_SEVERITY)
        self.assertEqual(analysis["recommendation"], S.RECOMMENDED_ACTION)
        self.assertEqual(analysis["potential_savings"], S.VARIANCE_OVERCHARGE)

    def test_excluded_line_items_are_challenged(self):
        line_items = [
            {
                "description": description,
                "category": category,
                "landlord_amount": amount,
            }
            for description, category, amount in S.EXCLUDED_LINE_ITEMS
        ]
        analyzed = analyze_line_items(line_items, S.PROVISIONS_FOR_ENGINE)
        self.assertTrue(analyzed)
        self.assertTrue(all(item["is_excluded"] for item in analyzed))
        self.assertTrue(all(item["recommended_action"] == "CHALLENGE" for item in analyzed))
        self.assertEqual(
            sum(item["variance_amount"] for item in analyzed),
            sum(amount for _, _, amount in S.EXCLUDED_LINE_ITEMS),
        )

    def test_exclusions_flagged_from_description_when_category_is_other(self):
        line_items = [
            {
                "line_number": 19,
                "description": "Roof replacement — full membrane (capital improvement)",
                "category": "OTHER",
                "amount": 180000.00,
            }
        ]
        analyzed = analyze_line_items(line_items, S.PROVISIONS_FOR_ENGINE)
        self.assertTrue(analyzed[0]["should_challenge"])
        self.assertEqual(analyzed[0]["variance"], 180000.00)


class StatementParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = extract_text_from_pdf(str(S.STATEMENT_PDF))
        cls.parsed = assemble_cam_statement(cls.text)

    def test_extracts_both_pdf_pages(self):
        self.assertIn("Window washing", self.text)
        self.assertIn("Roof replacement", self.text)
        self.assertIn("debt service", self.text.lower())

    def test_keeps_all_23_numbered_lines(self):
        items = self.parsed["line_items"]
        self.assertEqual(len(items), 23)
        descriptions = " ".join(item["description"] for item in items)
        self.assertIn("Roof replacement", descriptions)
        self.assertIn("Structural steel", descriptions)
        self.assertIn("Depreciation", descriptions)
        self.assertIn("debt service", descriptions.lower())
        self.assertEqual(self.parsed["total_building_charges"], 1200000.00)
        self.assertEqual(self.parsed["tenant_share_billed"], 150000.00)

    def test_gpt_dropping_page_two_does_not_lose_exclusions(self):
        incomplete_gpt = {
            "line_items": self.parsed["line_items"][:18],
            "total_building_charges": 821000,
            "tenant_share_billed": 150000,
        }
        merged = assemble_cam_statement(self.text, incomplete_gpt)
        self.assertEqual(len(merged["line_items"]), 23)
        self.assertEqual(merged["total_building_charges"], 1200000.00)

    def test_step_two_defaults_match_the_statement(self):
        defaults = defaults_from_parsed_statement(self.parsed)
        self.assertEqual(defaults["recon_year"], 2025)
        self.assertEqual(defaults["statement_date"].isoformat(), "2026-03-15")
        self.assertEqual(defaults["landlord_total"], 1200000.00)
        self.assertEqual(defaults["tenant_share_billed"], 150000.00)

    def test_five_planted_exclusions_are_challenged(self):
        analyzed = analyze_line_items(self.parsed["line_items"], S.PROVISIONS_FOR_ENGINE)
        challenged = [item for item in analyzed if item["should_challenge"]]
        self.assertEqual(len(challenged), 5)
        self.assertEqual(sum(item["variance"] for item in challenged), 379000.00)


if __name__ == "__main__":
    unittest.main()
