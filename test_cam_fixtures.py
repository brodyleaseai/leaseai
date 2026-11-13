"""Synthetic Northridge lease + CAM statement are extractable and match the engine."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "cam"))

import scenario as S  # noqa: E402
import scenario_ironwood as IW  # noqa: E402
from cam_engine import (  # noqa: E402
    analyze_line_items,
    assemble_cam_statement,
    calculate_cam_charges,
    defaults_from_parsed_statement,
    detect_discrepancies,
    enrich_cam_provisions,
    reconcile_cam_charges,
)
from cam_gpt_extractor import extract_text_from_pdf  # noqa: E402
from cam_pdf_report import generate_cam_pdf_report  # noqa: E402


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

    def test_missing_base_amount_does_not_cap_against_this_year(self):
        result = calculate_cam_charges(S.BUILDING_TOTAL_CHARGES, {
            "tenant_prorata_share": S.TENANT_PRORATA_SHARE,
            "has_cam_cap": True,
            "cam_cap_percentage": S.CAM_CAP_PERCENTAGE,
            "cam_base_amount": None,
        })
        self.assertEqual(result["calculated_tenant_share"], S.TENANT_SHARE_BILLED)
        self.assertFalse(result["cam_cap_applied"])

    def test_reconcile_strips_exclusions_then_prorates(self):
        parsed = assemble_cam_statement(_pdf_text(S.STATEMENT_PDF))
        result = reconcile_cam_charges(
            S.BUILDING_TOTAL_CHARGES,
            S.TENANT_SHARE_BILLED,
            S.PROVISIONS_FOR_ENGINE,
            parsed["line_items"],
        )
        self.assertEqual(result["excluded_building_charges"], 379000.00)
        self.assertEqual(result["allowable_building_charges"], 821000.00)
        self.assertEqual(result["calculated_tenant_share"], 102625.00)
        self.assertEqual(result["variance_amount"], 47375.00)

    def test_enrich_reads_annual_increase_cap_field_name(self):
        merged = enrich_cam_provisions({}, {
            "CAM Annual Increase Cap (%)": "5%",
            "Premises Square Footage (RSF)": "12,500",
            "Building Total Square Footage": "100,000",
            "CAM Exclusions": "capital improvements, roof replacement, debt service",
        })
        self.assertTrue(merged["has_cam_cap"])
        self.assertEqual(merged["cam_cap_percentage"], 5.0)
        self.assertAlmostEqual(merged["tenant_prorata_share"], 0.125, places=4)

    def test_enrich_reads_base_amount_and_audit_fields(self):
        merged = enrich_cam_provisions({}, {
            "CAM Base Amount": "$100,000.00 tenant share in CAM Base Year 2023",
            "Tenant Audit Rights": "Yes. Tenant is ALLOWED to inspect.",
            "Audit Deadline": "Within 90 days of receipt of the annual CAM reconciliation",
        })
        self.assertEqual(merged["cam_base_amount"], 100000.00)
        self.assertTrue(merged["tenant_audit_right"])
        self.assertIn("90 days", merged["audit_deadline"])

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


def _northridge_workpaper_bytes():
    parsed = assemble_cam_statement(_pdf_text(S.STATEMENT_PDF))
    result = reconcile_cam_charges(
        S.BUILDING_TOTAL_CHARGES,
        S.TENANT_SHARE_BILLED,
        S.PROVISIONS_FOR_ENGINE,
        parsed["line_items"],
    )
    provisions = dict(S.PROVISIONS_FOR_ENGINE)
    provisions.update({
        "tenant_square_footage": S.PREMISES_RSF,
        "building_square_footage": S.BUILDING_RSF,
        "tenant_audit_right": S.TENANT_AUDIT_RIGHT,
        "audit_deadline": S.AUDIT_DEADLINE,
    })
    lease_data = {
        "property_address": S.PROPERTY_ADDRESS,
        "tenant_name": S.TENANT_NAME,
        "landlord_name": S.LANDLORD_NAME,
    }
    recon = {
        "reconciliation_year": S.RECONCILIATION_YEAR,
        "statement_date": S.STATEMENT_DATE,
        "landlord_total_charges": S.BUILDING_TOTAL_CHARGES,
        "landlord_tenant_share": S.TENANT_SHARE_BILLED,
        "calculated_tenant_share": result["calculated_tenant_share"],
        "variance_amount": result["variance_amount"],
        "variance_percentage": result["variance_amount"] / S.TENANT_SHARE_BILLED * 100,
        "calculations": result["calculations"],
        "excluded_building_charges": result["excluded_building_charges"],
        "allowable_building_charges": result["allowable_building_charges"],
        "cam_cap_applied": result.get("cam_cap_applied"),
    }
    return generate_cam_pdf_report(
        lease_data,
        recon,
        result["analyzed_line_items"],
        provisions,
    ), result


class CamWorkpaperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf_bytes, cls.result = _northridge_workpaper_bytes()
        cls.path = ROOT / "tests" / "fixtures" / "cam" / "_generated_workpaper.pdf"
        cls.path.write_bytes(cls.pdf_bytes)
        cls.text = _pdf_text(cls.path)

    @classmethod
    def tearDownClass(cls):
        if cls.path.exists():
            cls.path.unlink()

    def test_workpaper_is_a_pdf(self):
        self.assertTrue(self.pdf_bytes.startswith(b"%PDF"))

    def test_labels_are_tenant_share_not_landlords_charges(self):
        self.assertIn("CAM Reconciliation Workpaper", self.text)
        self.assertIn("Tenant share", self.text)
        self.assertNotIn("Landlord's Charges", self.text)
        self.assertNotIn("Calculated Per Lease", self.text)

    def test_math_and_challenge_recommendation(self):
        for needle in (
            "1,200,000.00",
            "150,000.00",
            "102,625.00",
            "47,375.00",
            "821,000.00",
            "379,000.00",
            "CHALLENGE",
            "Cascade Analytics",
            "1200 Cascade Plaza",
            "Northridge Office Partners",
        ):
            self.assertIn(needle, self.text, f"workpaper missing {needle!r}")

    def test_all_statement_lines_and_exclusion_flags(self):
        self.assertIn("Roof replacement", self.text)
        self.assertIn("Structural steel", self.text)
        self.assertIn("Depreciation", self.text)
        self.assertIn("Mortgage interest", self.text)
        self.assertIn("Legal fees", self.text)
        self.assertIn("Window washing", self.text)
        self.assertIn("HVAC maintenance", self.text)
        self.assertNotIn("Hvac", self.text)
        self.assertGreaterEqual(self.text.count("Challenge"), 5)
        self.assertGreaterEqual(self.text.count("Allow"), 18)
        self.assertIn("roof replacement is", self.text.lower())
        self.assertIn("excluded per lease terms", self.text)
        self.assertIn("$100,000.00", self.text)
        self.assertIn("Within 90 days of receipt of the annual CAM reconciliation", self.text)
        self.assertNotIn("Landlord'S", self.text)

    def test_exclusions_are_listed_once_without_title_case(self):
        description = (
            "capital improvements, structural repairs, roof replacement, depreciation, "
            "debt service, mortgage payments, legal fees relating to other tenants "
            "or to Landlord's financing"
        )
        pdf_bytes = generate_cam_pdf_report(
            {"property_address": S.PROPERTY_ADDRESS, "tenant_name": S.TENANT_NAME},
            {
                "reconciliation_year": 2025,
                "statement_date": S.STATEMENT_DATE,
                "landlord_total_charges": S.BUILDING_TOTAL_CHARGES,
                "landlord_tenant_share": S.TENANT_SHARE_BILLED,
                "calculated_tenant_share": 102625.00,
                "variance_amount": 47375.00,
                "excluded_building_charges": 379000.00,
                "allowable_building_charges": 821000.00,
                "cam_cap_applied": False,
            },
            assemble_cam_statement(_pdf_text(S.STATEMENT_PDF))["line_items"],
            {
                "tenant_prorata_share": S.TENANT_PRORATA_SHARE,
                "has_cam_cap": True,
                "cam_cap_percentage": 5.0,
                "cam_base_amount": None,
                "excluded_items": [part.strip() for part in description.split(",")],
                "exclusions_description": description,
            },
        )
        text = _pdf_text_from_bytes(pdf_bytes)
        self.assertIn("legal fees relating to other tenants", text)
        self.assertIn("Landlord's financing", text)
        self.assertNotIn("Landlord'S", text)
        self.assertNotIn("Legal Fees Relating To", text)
        self.assertIn("base-year tenant CAM amount", text)
        self.assertIn("this file", text)
        self.assertNotIn("CAM Base Amount was not stored", text)

    def test_unanalyzed_items_are_flagged_in_the_pdf(self):
        parsed = assemble_cam_statement(_pdf_text(S.STATEMENT_PDF))
        pdf_bytes = generate_cam_pdf_report(
            {"property_address": S.PROPERTY_ADDRESS, "tenant_name": S.TENANT_NAME},
            {
                "reconciliation_year": 2025,
                "statement_date": S.STATEMENT_DATE,
                "landlord_total_charges": S.BUILDING_TOTAL_CHARGES,
                "landlord_tenant_share": S.TENANT_SHARE_BILLED,
                "calculated_tenant_share": 102625.00,
                "variance_amount": 47375.00,
                "excluded_building_charges": 379000.00,
                "allowable_building_charges": 821000.00,
            },
            parsed["line_items"],
            S.PROVISIONS_FOR_ENGINE,
        )
        text = _pdf_text_from_bytes(pdf_bytes)
        self.assertIn("Challenge", text)
        self.assertIn("Roof replacement", text)


def _pdf_text_from_bytes(pdf_bytes: bytes) -> str:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(pdf_bytes)
        path = Path(handle.name)
    try:
        return _pdf_text(path)
    finally:
        path.unlink(missing_ok=True)


class CamReportEmailTests(unittest.TestCase):
    def test_send_cam_report_email_attaches_pdf(self):
        from unittest.mock import MagicMock, patch
        try:
            import email_delivery
        except ModuleNotFoundError as exc:
            self.skipTest(f"email stack not installed: {exc}")

        pdf_bytes, _result = _northridge_workpaper_bytes()
        fake_response = MagicMock(status_code=202)
        with patch.object(email_delivery, "SendGridAPIClient") as client_cls, \
                patch.object(email_delivery.config, "SENDGRID_API_KEY", "sg-test-key"):
            client_cls.return_value.send.return_value = fake_response
            sent = email_delivery.send_cam_report_email(
                recipient_email="cfo@cascade.test",
                recipient_name="Jordan Hale",
                property_address=S.PROPERTY_ADDRESS,
                tenant_name=S.TENANT_NAME,
                year=2025,
                pdf_bytes=pdf_bytes,
                billed_share=150000,
                allowed_share=102625,
                variance_amount=47375,
                recommendation="CHALLENGE",
            )
        self.assertTrue(sent)
        message = client_cls.return_value.send.call_args[0][0]
        payload = message.get()
        self.assertIn("CAM Reconciliation Workpaper", str(payload.get("subject")))
        attachments = payload.get("attachments") or []
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get("type"), "application/pdf")
        self.assertTrue(str(attachments[0].get("filename", "")).endswith(".pdf"))


class IronwoodFixtureFilesTests(unittest.TestCase):
    def test_lease_pdf_exists(self):
        self.assertTrue(IW.LEASE_PDF.is_file(), f"missing {IW.LEASE_PDF}")
        self.assertTrue(IW.LEASE_PDF.read_bytes().startswith(b"%PDF"))

    def test_statement_pdf_exists(self):
        self.assertTrue(IW.STATEMENT_PDF.is_file(), f"missing {IW.STATEMENT_PDF}")
        self.assertTrue(IW.STATEMENT_PDF.read_bytes().startswith(b"%PDF"))


class IronwoodLeaseTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _pdf_text(IW.LEASE_PDF)

    def test_parties_and_cam_terms_are_selectable_text(self):
        for needle in (
            IW.LANDLORD_NAME,
            IW.TENANT_NAME,
            IW.PROPERTY_ADDRESS,
            "8,000",
            "40,000",
            "20.00%",
            "CAM Base Year",
            "CAM Annual Increase Cap",
            "four percent (4%)",
            "CAM Exclusions",
            "parking lot reconstruction",
            "HVAC replacement",
            "roof replacement",
            "Tenant Audit Right",
            "Triple Net (NNN)",
            "Pinnacle Fresh",
        ):
            self.assertIn(needle, self.text, f"Ironwood lease PDF missing {needle!r}")
        self.assertIn("SYNTHETIC TEST DOCUMENT", self.text)
        self.assertNotIn("Cascade Analytics", self.text)
        self.assertNotIn("The Meridian Tower", self.text)


class IronwoodStatementTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _pdf_text(IW.STATEMENT_PDF)

    def test_totals_and_planted_exclusions_are_selectable_text(self):
        for needle in (
            IW.LANDLORD_NAME,
            IW.TENANT_NAME,
            "723,000.00",
            "144,600.00",
            "February 28, 2025",
            "Parking lot reconstruction",
            "Rooftop HVAC replacement",
            "Roof replacement",
            "Legal fees",
            "$90,000.00",
            "$75,000.00",
            "$50,000.00",
            "$8,000.00",
        ):
            self.assertIn(needle, self.text, f"Ironwood statement PDF missing {needle!r}")
        self.assertNotIn("Depreciation expense", self.text)
        self.assertNotIn("debt service", self.text.lower())
        self.assertNotIn("Cascade Analytics", self.text)


class IronwoodEngineMathTests(unittest.TestCase):
    def test_building_totals(self):
        self.assertEqual(IW.ALLOWABLE_BUILDING_CHARGES, 500000.00)
        self.assertEqual(IW.EXCLUDED_BUILDING_CHARGES, 223000.00)
        self.assertEqual(IW.BUILDING_TOTAL_CHARGES, 723000.00)
        self.assertEqual(IW.TENANT_SHARE_BILLED, 144600.00)
        self.assertEqual(IW.SHARE_AFTER_EXCLUSIONS, 100000.00)
        self.assertEqual(IW.CAP_CEILING, 83200.00)
        self.assertEqual(IW.CALCULATED_TENANT_SHARE, 83200.00)
        self.assertEqual(IW.VARIANCE_OVERCHARGE, 61400.00)

    def test_cap_binds_after_exclusions_are_stripped(self):
        parsed = assemble_cam_statement(_pdf_text(IW.STATEMENT_PDF))
        result = reconcile_cam_charges(
            IW.BUILDING_TOTAL_CHARGES,
            IW.TENANT_SHARE_BILLED,
            IW.PROVISIONS_FOR_ENGINE,
            parsed["line_items"],
        )
        self.assertEqual(len(parsed["line_items"]), 20)
        self.assertEqual(result["excluded_building_charges"], 223000.00)
        self.assertEqual(result["allowable_building_charges"], 500000.00)
        self.assertEqual(result["calculated_tenant_share"], 83200.00)
        self.assertEqual(result["variance_amount"], 61400.00)
        self.assertTrue(result["cam_cap_applied"])

    def test_four_planted_exclusions_are_challenged(self):
        parsed = assemble_cam_statement(_pdf_text(IW.STATEMENT_PDF))
        analyzed = analyze_line_items(parsed["line_items"], IW.PROVISIONS_FOR_ENGINE)
        challenged = [item for item in analyzed if item["should_challenge"]]
        self.assertEqual(len(challenged), 4)
        self.assertEqual(sum(item["variance"] for item in challenged), 223000.00)

    def test_step_two_defaults_match_the_statement(self):
        parsed = assemble_cam_statement(_pdf_text(IW.STATEMENT_PDF))
        defaults = defaults_from_parsed_statement(parsed)
        self.assertEqual(defaults["recon_year"], 2024)
        self.assertEqual(defaults["statement_date"].isoformat(), "2025-02-28")
        self.assertEqual(defaults["landlord_total"], 723000.00)
        self.assertEqual(defaults["tenant_share_billed"], 144600.00)


if __name__ == "__main__":
    unittest.main()
