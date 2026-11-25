"""Customer-facing copy uses Veriterm, not LeaseAI."""

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from brand import LOGO_PATH, MARK_PATH, email_header_html  # noqa: E402
from cam_pdf_report import generate_cam_pdf_report  # noqa: E402
from lease_report import generate_lease_abstract_pdf  # noqa: E402


def _pdf_text(pdf_bytes: bytes) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


class ConfigBrandTests(unittest.TestCase):
    def test_app_and_company_names(self):
        self.assertEqual(config.APP_NAME, "Veriterm")
        self.assertEqual(config.COMPANY_NAME, "Veriterm Contract Intelligence Inc.")
        self.assertEqual(config.COMPANY_TAGLINE, "Clearer terms. Brighter outcomes.")
        self.assertEqual(config.SENDER_NAME, "Veriterm")
        self.assertEqual(config.SUPPORT_EMAIL, "hello@veriterm.com")

    def test_logo_files_exist(self):
        self.assertTrue(LOGO_PATH.is_file(), f"missing {LOGO_PATH}")
        self.assertTrue(MARK_PATH.is_file(), f"missing {MARK_PATH}")
        self.assertGreater(LOGO_PATH.stat().st_size, 1000)

    def test_email_header_lockup(self):
        html = email_header_html("Your lease abstract is ready")
        self.assertIn("VERITERM", html)
        self.assertIn("CONTRACT INTELLIGENCE", html)
        self.assertIn("#0B1F3A", html)
        self.assertNotIn("LeaseAI", html)
        self.assertNotIn("#667eea", html)


class PdfBrandTests(unittest.TestCase):
    def test_lease_abstract_says_veriterm(self):
        pdf_bytes = generate_lease_abstract_pdf(
            {
                "property_address": "100 Brand Street",
                "tenant_name": "Acme Tenant LLC",
            },
            {
                "Base Rent": {"value": "$10,000 / month", "confidence": "HIGH"},
            },
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        text = _pdf_text(pdf_bytes)
        self.assertIn("Veriterm", text)
        self.assertIn("Clearer terms. Brighter outcomes.", text)
        self.assertIn("Veriterm Contract Intelligence Inc.", text)
        self.assertNotIn("LeaseAI", text)
        self.assertNotIn("KitschCo", text)

    def test_cam_workpaper_says_veriterm(self):
        pdf_bytes = generate_cam_pdf_report(
            {"property_address": "100 Brand Street", "tenant_name": "Acme Tenant LLC"},
            {
                "reconciliation_year": 2024,
                "landlord_total_charges": 100000,
                "landlord_tenant_share": 20000,
                "calculated_tenant_share": 18000,
                "variance_amount": 2000,
                "excluded_building_charges": 10000,
                "allowable_building_charges": 90000,
                "cam_cap_applied": False,
            },
            [
                {
                    "description": "Janitorial",
                    "amount": 5000,
                    "category": "MAINTENANCE",
                    "flag": "OK",
                    "reason": "",
                }
            ],
            {"tenant_prorata_share": 0.20, "has_cam_cap": False},
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        text = _pdf_text(pdf_bytes)
        self.assertIn("VERITERM", text.upper())
        self.assertIn("Veriterm applies the lease", text)
        self.assertIn("CAM terms Veriterm used", text)
        self.assertNotIn("LeaseAI", text)


class EmailBrandTests(unittest.TestCase):
    def test_cam_email_copy_uses_veriterm(self):
        try:
            import email_delivery
        except ModuleNotFoundError as exc:
            self.skipTest(f"email stack not installed: {exc}")

        fake_response = MagicMock(status_code=202)
        with patch.object(email_delivery, "SendGridAPIClient") as client_cls, \
                patch.object(email_delivery.config, "SENDGRID_API_KEY", "sg-test-key"):
            client_cls.return_value.send.return_value = fake_response
            sent = email_delivery.send_cam_report_email(
                recipient_email="cfo@example.test",
                recipient_name="Jordan Hale",
                property_address="100 Brand Street",
                tenant_name="Acme Tenant LLC",
                year=2024,
                pdf_bytes=b"%PDF-1.4 test",
                billed_share=20000,
                allowed_share=18000,
                variance_amount=2000,
                recommendation="CHALLENGE",
            )
        self.assertTrue(sent)
        message = client_cls.return_value.send.call_args[0][0]
        payload = str(message.get())
        self.assertIn("Veriterm", payload)
        self.assertIn("VERITERM", payload)
        self.assertNotIn("LeaseAI", payload)

    def test_email_modules_do_not_hardcode_leaseai_in_bodies(self):
        for name in ("email_delivery.py", "email_notifications.py", "email_templates.py"):
            source = (ROOT / name).read_text()
            self.assertNotIn("LeaseAI compared", source, name)
            self.assertNotIn("LeaseAI portal", source, name)
            self.assertNotIn("The LeaseAI Team", source, name)
            self.assertNotIn("support@leaseai.com", source, name)
            self.assertNotIn("#667eea", source, name)


class TwoFactorIssuerTests(unittest.TestCase):
    def test_default_issuer_is_veriterm(self):
        source = (ROOT / "two_factor_auth.py").read_text()
        self.assertIn("config.APP_NAME", source)
        self.assertNotIn('issuer: str = "LeaseAI"', source)
        self.assertNotIn("issuer_name=\"LeaseAI\"", source)
        self.assertNotIn("issuer_name='LeaseAI'", source)


if __name__ == "__main__":
    unittest.main()
