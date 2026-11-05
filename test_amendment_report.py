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

    def test_recovers_co_diagnostics_changes_when_history_collapsed(self):
        """Exhibit A listed 3 modifications; Schedule A must not drop CAM/Holdover."""
        collapsed_history = [
            {
                "clause_type": "CAM Cap",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": (
                    "The controllable component of CAM / Operating Cost Charges shall be "
                    "capped on an annual basis. The CAM Annual Increase Cap shall not "
                    "exceed 3.5% per annum, calculated on a cumulative and compounded "
                    "basis year-over-year."
                ),
                "is_current": True,
                "effective_from": "2025-01-01",
            },
            {
                "clause_type": "Holdover Provisions",
                "version_number": 1,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-1",
                "clause_value": (
                    "Effective immediately, if Tenant holds over past the Lease Expiration "
                    "Date without express written consent from Landlord, the Holdover "
                    "Provision Rate shall be adjusted downward from 150% to 125% of the "
                    "last active month's Base Rent."
                ),
                "is_current": True,
                "effective_from": "2025-01-01",
                "modification_type": "MODIFIES",
            },
            {
                "clause_type": "Security Deposit",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "$2,500.00",
                "is_current": False,
                "effective_from": "2023-10-01",
            },
            {
                "clause_type": "Security Deposit",
                "version_number": 1,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-1",
                "clause_value": (
                    "Effective as of the Effective Date, the Security Deposit Amount shall "
                    "be reduced from two thousand five hundred dollars ($2,500.00) down to "
                    "one thousand five hundred dollars ($1,500.00). Landlord shall refund "
                    "the excess balance of one thousand dollars ($1,000.00) to Tenant "
                    "within thirty (30) days of the execution of this First Amendment."
                ),
                "is_current": True,
                "effective_from": "2025-01-01",
                "modification_type": "MODIFIES",
            },
            {
                "clause_type": "Utilities",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "Tenant",
                "is_current": True,
                "effective_from": "2023-10-01",
            },
        ]
        recorded = [
            {
                "amendment_id": "amd-1",
                "clause_type": "CAM Cap",
                "modification_type": "SUPERSEDES",
                "original_value": "5%",
                "new_value": (
                    "The controllable component of CAM / Operating Cost Charges shall be "
                    "capped on an annual basis. The CAM Annual Increase Cap shall not "
                    "exceed 3.5% per annum, calculated on a cumulative and compounded "
                    "basis year-over-year."
                ),
                "effective_date": "2025-01-01",
            },
            {
                "amendment_id": "amd-1",
                "clause_type": "Holdover Provisions",
                "modification_type": "MODIFIES",
                "original_value": (
                    "If Tenant holds over past expiration without written consent, the "
                    "holdover rent shall be 150% of the last active month's Base Rent, "
                    "requiring a minimum of 30 days prior notice."
                ),
                "new_value": (
                    "Effective immediately, if Tenant holds over past the Lease Expiration "
                    "Date without express written consent from Landlord, the Holdover "
                    "Provision Rate shall be adjusted downward from 150% to 125% of the "
                    "last active month's Base Rent."
                ),
                "effective_date": "2025-01-01",
            },
            {
                "amendment_id": "amd-1",
                "clause_type": "Security Deposit",
                "modification_type": "MODIFIES",
                "original_value": "$2,500.00",
                "new_value": (
                    "Effective as of the Effective Date, the Security Deposit Amount shall "
                    "be reduced from two thousand five hundred dollars ($2,500.00) down to "
                    "one thousand five hundred dollars ($1,500.00)."
                ),
                "effective_date": "2025-01-01",
            },
        ]
        amendments = [
            {
                "amendment_id": "amd-1",
                "amendment_number": 1,
                "amendment_date": "2025-01-02",
                "status": "READY FOR REVIEW",
                "modified_clauses": ["CAM Cap", "Holdover Provisions", "Security Deposit"],
            }
        ]
        model = build_amendment_resolution_model(
            {
                "property_address": "3215 S 300 W, Salt Lake City, Utah",
                "tenant_name": "CO-DIAGNOSTICS, INC.",
            },
            amendments,
            collapsed_history,
            as_of="2026-11-04",
            amendment_clauses=recorded,
        )
        changed = {clause["clause_type"]: clause for clause in model["changed_clauses"]}
        self.assertEqual(
            set(changed),
            {"CAM Cap", "Holdover Provisions", "Security Deposit"},
        )
        self.assertEqual(changed["CAM Cap"]["original_value"], "5%")
        self.assertIn("3.5%", changed["CAM Cap"]["governing_value"])
        self.assertEqual(changed["CAM Cap"]["change_summary"], "5% → 3.5%")
        self.assertEqual(changed["Holdover Provisions"]["change_summary"], "150% → 125%")
        self.assertEqual(changed["Security Deposit"]["change_summary"], "$2,500.00 → $1,500.00")
        self.assertEqual([c["clause_type"] for c in model["unchanged_clauses"]], ["Utilities"])
        self.assertEqual(model["unchanged_clauses"][0]["governing_value"], "Tenant")

        text = _pdf_text(model)
        self.assertIn("1. CAM Cap", text)
        self.assertIn("2. Holdover Provisions", text)
        self.assertIn("3. Security Deposit", text)
        self.assertIn("5%", text)
        self.assertIn("3.5%", text)
        self.assertIn("150%", text)
        self.assertIn("125%", text)
        self.assertNotIn("side-by-side", text.lower())


def _pdf_text(model):
    from io import BytesIO

    pdf_bytes = generate_amendment_resolution_pdf(model)
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages)


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
        self.assertIn("Changed:", text)
        self.assertIn("$8,550.08 → $9,000.00", text)
        self.assertIn("1. Base Rent", text)
        self.assertIn("Original lease", text)
        self.assertIn("Now governed by Amendment No. 1", text)
        self.assertIn("Exhibit A", text)
        self.assertIn("still governed by the original lease", text.lower())
        self.assertIn("not a legal opinion", text.lower())

    def test_northshore_second_amendment_rebuilds_rent_schedule(self):
        history = HISTORY + [
            {
                "clause_type": "Rent Schedule",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": (
                    "Year 1 (April 1, 2025–March 31, 2026): $24.00/RSF/year = $24,000.00/month; "
                    "Year 10 (April 1, 2034–March 31, 2035): $31.31/RSF/year = $31,310.00/month"
                ),
                "is_current": True,
                "effective_from": "2025-04-01",
            },
            {
                "clause_type": "Rent Escalations",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "3%",
                "is_current": True,
                "effective_from": "2025-04-01",
            },
            {
                "clause_type": "Premises Description",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "12,000 sq ft",
                "is_current": True,
                "effective_from": "2025-04-01",
            },
            {
                "clause_type": "Renewal Notice Deadline",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "9 months before the Expiry Date",
                "is_current": True,
                "effective_from": "2025-04-01",
            },
        ]
        amendments = [
            {
                "amendment_id": "amd-1",
                "amendment_number": 1,
                "amendment_date": "2026-06-18",
                "status": "READY FOR REVIEW",
                "modified_clauses": ["Expansion of Premises"],
            },
            {
                "amendment_id": "amd-2",
                "amendment_number": 2,
                "amendment_date": "2027-02-12",
                "status": "READY FOR REVIEW",
                "modified_clauses": ["Base Rent", "Renewal Options"],
            },
        ]
        recorded = [
            {
                "amendment_id": "amd-1",
                "clause_type": "Expansion of Premises",
                "modification_type": "ADDS",
                "original_value": "Not stated - amendment only provides new value",
                "new_value": (
                    "From and after the Expansion Effective Date, the Premises comprise "
                    "13,500 rentable square feet in total."
                ),
                "effective_date": "2026-07-01",
            },
            {
                "amendment_id": "amd-2",
                "clause_type": "Base Rent",
                "modification_type": "SUPERSEDES",
                "original_value": "$24,000",
                "new_value": (
                    "5. BASE RENT. From April 1, 2027 to March 31, 2035, Tenant shall pay "
                    "annual Base Rent for the entire Premises, currently comprising 13,500 "
                    "rentable square feet, at the following rates: April 1, 2027–March 31, 2028: "
                    "$27.25 per rentable square foot per annum; April 1, 2028–March 31, 2029: "
                    "$28.07; April 1, 2029–March 31, 2030: $28.91; April 1, 2030–March 31, 2031: "
                    "$29.78; April 1, 2031–March 31, 2032: $30.67; April 1, 2032–March 31, 2033: "
                    "$31.59; April 1, 2033–March 31, 2034: $32.54; and April 1, 2034–March 31, "
                    "2035: $33.52. The rates in this Section are fixed dollar rates and replace, "
                    "not supplement, any annual percentage escalation formula. No additional 3% "
                    "escalation shall be applied."
                ),
                "effective_date": "2027-04-01",
            },
            {
                "amendment_id": "amd-2",
                "clause_type": "Renewal Options",
                "modification_type": "MODIFIES",
                "original_value": "1",
                "new_value": 'The words “not later than twelve (12) months”',
                "effective_date": "2027-04-01",
            },
        ]
        history = [
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
                "version_number": 2,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-2",
                "clause_value": recorded[1]["new_value"],
                "is_current": True,
                "effective_from": "2027-04-01",
                "modification_type": "SUPERSEDES",
            },
            {
                "clause_type": "Renewal Options",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": "1",
                "is_current": False,
                "effective_from": "2025-04-01",
            },
            {
                "clause_type": "Renewal Options",
                "version_number": 2,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-2",
                "clause_value": recorded[2]["new_value"],
                "is_current": True,
                "effective_from": "2027-04-01",
                "modification_type": "MODIFIES",
            },
        ] + history[2:]
        model = build_amendment_resolution_model(
            {
                "property_address": "8800 Riverfront Dr, Richmond, BC",
                "tenant_name": "Juniper Coast Analytics Inc.",
            },
            amendments,
            history,
            as_of="2026-11-05",
            amendment_clauses=recorded,
        )
        changed = {clause["clause_type"]: clause for clause in model["changed_clauses"]}
        unchanged = {clause["clause_type"] for clause in model["unchanged_clauses"]}
        self.assertIn("Rent Schedule", changed)
        self.assertIn("$30,656.25/month", changed["Rent Schedule"]["governing_value"])
        self.assertIn("$37,710.00/month", changed["Rent Schedule"]["governing_value"])
        self.assertNotIn("$24,000.00/month", changed["Rent Schedule"]["governing_value"])
        self.assertEqual(changed["Rent Schedule"]["linked_from"], "Base Rent")
        self.assertIn("fixed dollar rates", changed["Rent Escalations"]["governing_value"])
        self.assertEqual(changed["Premises Description"]["governing_value"], "13,500 sq ft")
        self.assertEqual(
            changed["Renewal Notice Deadline"]["governing_value"],
            "12 months before the Expiry Date",
        )
        self.assertNotIn("Rent Schedule", unchanged)
        self.assertNotIn("Rent Escalations", unchanged)
        self.assertNotIn("Premises Description", unchanged)
        self.assertNotIn("Renewal Notice Deadline", unchanged)

        text = _pdf_text(model)
        self.assertIn("$30,656.25", text)
        self.assertIn("13,500 sq ft", text)
        self.assertIn("12 months before the Expiry Date", text)
        self.assertIn("linked from Base Rent", text)
        self.assertIn("$24,000.00 → $30,656.25", text)
        schedule_b = text.split("Schedule B")[-1]
        self.assertNotIn("Rent Schedule", schedule_b)
        self.assertNotIn("9 months before the Expiry Date", schedule_b)

    def test_third_amendment_updates_schedule_and_includes_precedence(self):
        second_rent = (
            "5. BASE RENT. From April 1, 2027 to March 31, 2035, Tenant shall pay annual Base Rent "
            "for the entire Premises, currently comprising 13,500 rentable square feet, at the following "
            "rates: April 1, 2027–March 31, 2028: $27.25 per rentable square foot per annum; "
            "April 1, 2028–March 31, 2029: $28.07; April 1, 2029–March 31, 2030: $28.91; "
            "April 1, 2030–March 31, 2031: $29.78; April 1, 2031–March 31, 2032: $30.67; "
            "April 1, 2032–March 31, 2033: $31.59; April 1, 2033–March 31, 2034: $32.54; "
            "and April 1, 2034–March 31, 2035: $33.52. The rates in this Section are fixed dollar rates "
            "and replace, not supplement, any annual percentage escalation formula. No additional 3% "
            "escalation shall be applied."
        )
        third_rent = (
            "Base Rent shall be calculated using the then-applicable rate multiplied by 12,800 "
            "rentable square feet. The applicable rate from April 1, 2028 to March 31, 2029 remains $28.07."
        )
        third_text = """
7. ORDER OF PRECEDENCE
If this Third Amendment conflicts with the Second Amendment, First Amendment, or original Lease, this Third Amendment
governs to the extent of the conflict. The Second Amendment continues to govern the Base Rent rates and renewal notice period except as expressly modified by this Third Amendment. All other provisions remain in force.
8. EXECUTION
Executed as of the date first written above.
"""
        history = [
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
                "version_number": 2,
                "source_document_type": "AMENDMENT",
                "source_document_id": "amd-2",
                "clause_value": second_rent,
                "is_current": False,
                "effective_from": "2027-04-01",
                "modification_type": "SUPERSEDES",
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
                "clause_value": "12,000 sq ft",
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
            {
                "clause_type": "Rent Schedule",
                "version_number": 0,
                "source_document_type": "BASE_LEASE",
                "clause_value": (
                    "Year 1 (April 1, 2025–March 31, 2026): $24.00/RSF/year = $24,000.00/month; "
                    "Year 10 (April 1, 2034–March 31, 2035): $31.31/RSF/year = $31,310.00/month"
                ),
                "is_current": True,
                "effective_from": "2025-04-01",
            },
        ]
        amendments = [
            {
                "amendment_id": "amd-2",
                "amendment_number": 2,
                "amendment_date": "2027-02-12",
                "status": "READY FOR REVIEW",
                "modified_clauses": ["Base Rent"],
            },
            {
                "amendment_id": "amd-3",
                "amendment_number": 3,
                "amendment_date": "2028-09-20",
                "effective_date": "2028-10-01",
                "status": "READY FOR REVIEW",
                "modified_clauses": ["Base Rent", "Premises Description"],
                "extracted_data": {"amendment_text": third_text},
            },
        ]
        recorded = [
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
                "original_value": "12,000 sq ft",
                "new_value": "the Premises shall comprise 12,800 rentable square feet.",
                "effective_date": "2028-10-01",
            },
        ]
        model = build_amendment_resolution_model(
            {
                "property_address": "8800 Riverfront Dr, Richmond, BC",
                "tenant_name": "Juniper Coast Analytics Inc.",
            },
            amendments,
            history,
            as_of="2026-11-05",
            amendment_clauses=recorded,
        )
        changed = {clause["clause_type"]: clause for clause in model["changed_clauses"]}
        self.assertIn("Rent Schedule", changed)
        self.assertIn("$29,941.33/month", changed["Rent Schedule"]["governing_value"])
        self.assertIn("$35,754.67/month", changed["Rent Schedule"]["governing_value"])
        self.assertIn("12,800 RSF", changed["Rent Schedule"]["governing_value"])
        self.assertNotIn("$31,310.00/month", changed["Rent Schedule"]["governing_value"])
        self.assertIn("Order of Precedence", changed)
        self.assertIn("Third Amendment governs", changed["Order of Precedence"]["governing_value"])
        text = _pdf_text(model)
        self.assertIn("$29,941.33", text)
        self.assertIn("Order of Precedence", text)
        self.assertNotIn("Executed as of the date first written", text)
        self.assertNotIn("Rent Schedule", text.split("Schedule B")[-1])


if __name__ == "__main__":
    unittest.main()
