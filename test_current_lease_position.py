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


HARBOURVIEW_PREMISES = (
    "Effective October 1, 2025 (the “Expansion Effective Date”), Landlord leases to Tenant "
    "an additional 2,400 rentable square feet on the fourth floor, identified as Suite 415 "
    "on Exhibit A (the “Expansion Space”). From that date, the Premises comprise 20,400 "
    "rentable square feet in total."
)
HARBOURVIEW_RENT = (
    "From October 1, 2025 through March 31, 2026, Base Rent attributable to the Expansion "
    "Space is $28.50 per rentable square foot per annum. From April 1, 2026 onward, the "
    "Expansion Space is charged at the same per-square-foot rate applicable to the original "
    "Premises under Section 5, as amended in writing."
)
HARBOURVIEW_DEPOSIT = (
    "Within five business days after execution, Tenant shall pay an additional deposit of "
    "$14,400.00. The total Deposit held under Section 7 shall then be $122,400.00."
)
HARBOURVIEW_SHARE = (
    "Effective October 1, 2025, Tenant’s proportionate share increases from 18.00% to "
    "20.40%, calculated as 20,400 square feet divided by 100,000 square feet."
)


def _harbourview_resolution(as_of: str):
    return build_amendment_resolution_model(
        {
            "property_address": "4100 Harbourview Parkway",
            "tenant_name": "Pacific Arc Robotics",
        },
        [
            {
                "amendment_id": "amd-1",
                "amendment_number": 1,
                "amendment_date": "2025-08-12",
                "effective_date": "2025-10-01",
                "status": "READY FOR REVIEW",
                "modified_clauses": [
                    "Base Rent",
                    "Premises Description",
                    "Proportionate Share",
                    "Security Deposit",
                ],
            }
        ],
        [
            {
                "clause_type": "Base Rent",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "$39,750.00",
                "is_current": False,
                "effective_from": "2024-04-01",
            },
            {
                "clause_type": "Base Rent",
                "version_number": 1,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-1",
                "clause_value": HARBOURVIEW_RENT,
                "is_current": True,
                "effective_from": "2025-10-01",
                "modification_type": "ADDS",
            },
            {
                "clause_type": "Premises Description",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "18,000 sq ft",
                "is_current": False,
                "effective_from": "2024-04-01",
            },
            {
                "clause_type": "Premises Description",
                "version_number": 1,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-1",
                "clause_value": HARBOURVIEW_PREMISES,
                "is_current": True,
                "effective_from": "2025-10-01",
                "modification_type": "MODIFIES",
            },
            {
                "clause_type": "Proportionate Share",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "Tenant’s proportionate share is 18.00%.",
                "is_current": False,
                "effective_from": "2024-04-01",
            },
            {
                "clause_type": "Proportionate Share",
                "version_number": 1,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-1",
                "clause_value": HARBOURVIEW_SHARE,
                "is_current": True,
                "effective_from": "2025-10-01",
                "modification_type": "SUPERSEDES",
            },
            {
                "clause_type": "Security Deposit",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "$108,000.00",
                "is_current": False,
                "effective_from": "2024-04-01",
            },
            {
                "clause_type": "Security Deposit",
                "version_number": 1,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-1",
                "clause_value": HARBOURVIEW_DEPOSIT,
                "is_current": True,
                "effective_from": "2025-10-01",
                "modification_type": "MODIFIES",
            },
            {
                "clause_type": "Commencement Date",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "2024-04-01",
                "is_current": True,
                "effective_from": "2024-04-01",
            },
            {
                "clause_type": "Rent Escalations",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "3%",
                "is_current": True,
                "effective_from": "2024-04-01",
            },
        ],
        as_of=as_of,
        prepared_for="Brody Kitsch",
        amendment_clauses=[
            {
                "amendment_id": "amd-1",
                "clause_type": "Base Rent",
                "modification_type": "ADDS",
                "original_value": "$39,750.00",
                "new_value": HARBOURVIEW_RENT,
                "effective_date": "2025-10-01",
            },
            {
                "amendment_id": "amd-1",
                "clause_type": "Premises Description",
                "modification_type": "MODIFIES",
                "original_value": "18,000 sq ft",
                "new_value": HARBOURVIEW_PREMISES,
                "effective_date": "2025-10-01",
            },
            {
                "amendment_id": "amd-1",
                "clause_type": "Proportionate Share",
                "modification_type": "SUPERSEDES",
                "original_value": "Tenant’s proportionate share is 18.00%.",
                "new_value": HARBOURVIEW_SHARE,
                "effective_date": "2025-10-01",
            },
            {
                "amendment_id": "amd-1",
                "clause_type": "Security Deposit",
                "modification_type": "MODIFIES",
                "original_value": "$108,000.00",
                "new_value": HARBOURVIEW_DEPOSIT,
                "effective_date": "2025-10-01",
            },
        ],
    )


class HarbourviewExpansionTests(unittest.TestCase):
    """4100 Harbourview Parkway First Amendment — expansion, not a whole-premises reprice."""

    def test_abstract_summaries_match_the_amendment(self):
        resolution = _harbourview_resolution("2026-11-10")
        changed = {clause["clause_type"]: clause for clause in resolution["changed_clauses"]}
        self.assertEqual(changed["Premises Description"]["change_summary"], "18,000 → 20,400")
        self.assertEqual(
            changed["Security Deposit"]["change_summary"],
            "$108,000.00 → $122,400.00",
        )
        self.assertEqual(changed["Proportionate Share"]["change_summary"], "18.00% → 20.40%")
        self.assertNotEqual(changed["Base Rent"]["change_summary"], "$39,750.00 → $28.50")
        self.assertNotIn("18,000 → 1", changed["Premises Description"]["change_summary"])
        self.assertNotIn("$14,400", changed["Security Deposit"]["change_summary"].split("→")[-1])
        schedule = changed.get("Rent Schedule")
        if schedule:
            self.assertNotIn("20,400 RSF", schedule["governing_value"] or "")
            self.assertNotIn("$48,450", schedule["governing_value"] or "")

    def test_teaser_period_adds_expansion_rent_to_original(self):
        model = build_current_lease_position(_harbourview_resolution("2025-12-01"))
        rows = _rows(model)
        # Year-2 original: $39,750 × 1.03 = $40,942.50/mo. Expansion: 2,400 × $28.50 / 12 = $5,700.
        self.assertEqual(rows["Monthly Base Rent"]["current_value"], "$46,642.50")
        self.assertEqual(rows["Annual Base Rent"]["current_value"], "$559,710.00")
        self.assertEqual(rows["Annual Base Rent"]["status"], STATUS_CALCULATED)
        self.assertIn("2,400", rows["Annual Base Rent"]["calculation"])
        self.assertIn("$28.50", rows["Annual Base Rent"]["calculation"])
        self.assertNotEqual(rows["Annual Base Rent"]["current_value"], "$581,400.00")
        self.assertNotEqual(rows["Monthly Base Rent"]["current_value"], "$48,450.00")

    def test_after_teaser_uses_section_5_rate_on_total_rsf(self):
        model = build_current_lease_position(_harbourview_resolution("2026-11-10"))
        rows = _rows(model)
        # $26.50 × 1.03^2 = $28.11385 / RSF on 20,400 RSF. Not 20,400 × $28.50.
        expected_annual = round(20400 * 26.50 * (1.03 ** 2), 2)
        expected_monthly = round(expected_annual / 12.0, 2)
        self.assertEqual(rows["Annual Base Rent"]["current_value"], f"${expected_annual:,.2f}")
        self.assertEqual(rows["Monthly Base Rent"]["current_value"], f"${expected_monthly:,.2f}")
        self.assertNotEqual(rows["Annual Base Rent"]["current_value"], "$581,400.00")
        self.assertNotEqual(rows["Monthly Base Rent"]["current_value"], "$48,450.00")
        self.assertIn("20,400", rows["Annual Base Rent"]["calculation"])
        self.assertIn("expansion teaser ended", rows["Annual Base Rent"]["calculation"])
        self.assertEqual(rows["Premises / RSF"]["status"], STATUS_AMENDED)
        self.assertIn("20,400", rows["Premises / RSF"]["current_value"])
        self.assertIn("122,400.00", rows["Security Deposit"]["current_value"])
        self.assertIn("20.40%", rows["Proportionate Share"]["current_value"])
        text = _pdf_text(model)
        self.assertIn("Current Lease Position", text)
        self.assertNotIn("$581,400.00", text)
        self.assertIn("$122,400.00", text)


if __name__ == "__main__":
    unittest.main()
