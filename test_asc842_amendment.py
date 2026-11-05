"""ASC 842 commencement vs post-amendment remeasurement."""

import unittest

from amendment_clause_links import derive_rent_schedule
from amendment_report import build_amendment_resolution_model
from asc842_amendment import (
    KIND_CONSIDERATION,
    KIND_PARTIAL_TERMINATION,
    MODE_REMEASUREMENT,
    build_measurement,
    classify_modification,
    history_as_of,
    resolution_as_of,
    run_amended_calculation,
)
from asc842_cashflows import (
    escalate_flat_payments,
    overlay_payments,
    parse_schedule_rows,
    payments_from_schedule_text,
    remaining_payments,
)
from asc842_engine import ASC842ComplianceEngine
from test_amendment_clause_links import SECOND_AMENDMENT_RENT


LEASE = {
    "property_address": "Northshore — 1080 W River St",
    "tenant_name": "Northshore Tenant",
}

ORIGINAL_SCHEDULE = (
    "Year 1 (April 1, 2025–March 31, 2026): $24.00/RSF/year = $24,000.00/month; "
    "Year 2 (April 1, 2026–March 31, 2027): $24.72/RSF/year = $24,720.00/month"
)

THIRD_RENT = (
    "From and after October 1, 2028, Base Rent shall be calculated using the "
    "then-applicable rate multiplied by 12,800 rentable square feet, rather than "
    "13,500 rentable square feet. For clarity, the applicable rate from April 1, "
    "2028 to March 31, 2029 remains $28.07 per rentable square foot per annum; "
    "only the rentable area used in the calculation changes."
)

THIRD_PREMISES = (
    "From and after the Surrender Effective Date, the Premises shall comprise "
    "12,800 rentable square feet. Tenant shall surrender 700 rentable square feet."
)

AMENDMENTS = [
    {
        "amendment_id": "amd-2",
        "amendment_number": 2,
        "amendment_date": "2027-02-12",
        "effective_date": "2027-04-01",
        "status": "Active",
        "modified_clauses": ["Base Rent", "Premises Description"],
    },
    {
        "amendment_id": "amd-3",
        "amendment_number": 3,
        "amendment_date": "2028-09-20",
        "effective_date": "2028-10-01",
        "status": "Active",
        "modified_clauses": ["Base Rent", "Premises Description"],
    },
]

HISTORY = [
    {
        "clause_type": "Base Rent",
        "clause_value": "$24,000 per month",
        "source_document_type": "BASE_LEASE",
        "version_number": 0,
        "effective_from": "2025-04-01",
        "is_current": False,
    },
    {
        "clause_type": "Base Rent",
        "clause_value": SECOND_AMENDMENT_RENT,
        "source_document_type": "AMENDMENT",
        "source_document_id": "amd-2",
        "version_number": 2,
        "effective_from": "2027-04-01",
        "is_current": False,
    },
    {
        "clause_type": "Base Rent",
        "clause_value": THIRD_RENT,
        "source_document_type": "AMENDMENT",
        "source_document_id": "amd-3",
        "version_number": 3,
        "effective_from": "2028-10-01",
        "is_current": True,
    },
    {
        "clause_type": "Premises Description",
        "clause_value": "12,000 rentable square feet",
        "source_document_type": "BASE_LEASE",
        "version_number": 0,
        "effective_from": "2025-04-01",
        "is_current": False,
    },
    {
        "clause_type": "Premises Description",
        "clause_value": "13,500 rentable square feet",
        "source_document_type": "AMENDMENT",
        "source_document_id": "amd-2",
        "version_number": 2,
        "effective_from": "2027-04-01",
        "is_current": False,
    },
    {
        "clause_type": "Premises Description",
        "clause_value": THIRD_PREMISES,
        "source_document_type": "AMENDMENT",
        "source_document_id": "amd-3",
        "version_number": 3,
        "effective_from": "2028-10-01",
        "is_current": True,
    },
    {
        "clause_type": "Rent Schedule",
        "clause_value": ORIGINAL_SCHEDULE,
        "source_document_type": "BASE_LEASE",
        "version_number": 0,
        "effective_from": "2025-04-01",
        "is_current": False,
    },
    {
        "clause_type": "Rent Schedule",
        "clause_value": derive_rent_schedule(SECOND_AMENDMENT_RENT),
        "source_document_type": "AMENDMENT",
        "source_document_id": "amd-2",
        "version_number": 2,
        "effective_from": "2027-04-01",
        "is_current": True,
    },
]


class CashflowParseTests(unittest.TestCase):
    def test_parses_year_rows_and_expands_months(self):
        text = derive_rent_schedule(SECOND_AMENDMENT_RENT)
        rows = parse_schedule_rows(text)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["monthly"], 30656.25)
        payments = payments_from_schedule_text(text)
        self.assertEqual(payments[0]["date"], "2027-04-01")
        self.assertEqual(payments[0]["amount"], 30656.25)
        self.assertEqual(payments[-1]["date"], "2035-03-01")
        self.assertEqual(len(payments), 96)

    def test_third_amendment_remaining_starts_at_29941(self):
        clauses = build_amendment_resolution_model(
            LEASE, AMENDMENTS, HISTORY, as_of="2028-10-01"
        )["clauses"]
        schedule = next(row for row in clauses if row["clause_type"] == "Rent Schedule")
        remaining = remaining_payments(
            payments_from_schedule_text(schedule["governing_value"]),
            "2028-10-01",
        )
        self.assertEqual(remaining[0]["amount"], 29941.33)
        self.assertEqual(remaining[0]["date"], "2028-10-01")
        self.assertEqual(remaining[-1]["amount"], 35754.67)
        self.assertEqual(len(remaining), 78)

    def test_overlay_lets_amendment_win_on_overlap(self):
        base = escalate_flat_payments(24000, "2025-04-01", "2027-06-01", 0.03)
        overlay = [{"date": "2027-04-01", "amount": 30656.25}]
        merged = overlay_payments(base, overlay)
        self.assertEqual(merged[0]["amount"], 24000.0)
        april = next(row for row in merged if row["date"] == "2027-04-01")
        self.assertEqual(april["amount"], 30656.25)


class ClassificationTests(unittest.TestCase):
    def test_third_amendment_is_partial_termination(self):
        current = resolution_as_of(LEASE, AMENDMENTS, HISTORY, "2028-10-01")
        prior = resolution_as_of(LEASE, AMENDMENTS, HISTORY, "2028-09-30")
        classified = classify_modification(current, prior)
        self.assertEqual(classified["kind"], KIND_PARTIAL_TERMINATION)
        self.assertEqual(classified["prior_rsf"], 13500)
        self.assertEqual(classified["governing_rsf"], 12800)
        self.assertEqual(classified["surrendered_rsf"], 700)
        self.assertAlmostEqual(classified["scope_reduction_ratio"], 700 / 13500, places=5)
        self.assertEqual(classified["modification_date"], "2028-10-01")

    def test_as_of_before_third_keeps_13500(self):
        current = resolution_as_of(LEASE, AMENDMENTS, HISTORY, "2027-06-01")
        self.assertEqual(len(current["amendments"]), 1)
        premises = next(
            row for row in current["clauses"] if row["clause_type"] == "Premises Description"
        )
        self.assertIn("13,500", premises["governing_value"])

    def test_history_as_of_drops_future_versions(self):
        kept = history_as_of(HISTORY, "2028-09-30")
        current_base_rent = next(
            row
            for row in kept
            if row["clause_type"] == "Base Rent" and row.get("is_current")
        )
        self.assertEqual(current_base_rent["version_number"], 2)


class RemeasurementTests(unittest.TestCase):
    def test_commencement_path_still_matches_engine(self):
        lease_data = {
            "commencement_date": "2024-01-01",
            "end_date": "2026-12-31",
            "monthly_payment": 5000.0,
            "discount_rate": 0.05,
            "annual_rent_increases": 0.0,
        }
        first = ASC842ComplianceEngine(lease_data).run_full_calculation()
        second = ASC842ComplianceEngine(lease_data).run_full_calculation()
        self.assertEqual(first["initial_liability"], second["initial_liability"])
        self.assertGreater(first["initial_liability"], 0)

    def test_consideration_only_has_no_surrender_gain(self):
        original = escalate_flat_payments(5000, "2024-01-01", "2026-12-01")
        revised = [{"date": row["date"], "amount": 5500.0} for row in original if row["date"] >= "2025-01-01"]
        result = run_amended_calculation(
            {
                "commencement_date": "2024-01-01",
                "end_date": "2026-12-31",
                "monthly_payment": 5000.0,
                "discount_rate": 0.05,
                "explicit_payments": original,
            },
            revised,
            modification_date="2025-01-01",
            revised_discount_rate=0.05,
            scope_reduction_ratio=0.0,
            classification={"kind": KIND_CONSIDERATION},
        )
        self.assertEqual(result["partial_termination"]["gain_loss"], 0)
        self.assertEqual(result["rou_adjustment"], result["liability_adjustment"])
        self.assertGreater(result["remeasured_liability"], result["partial_termination"]["remaining_liability"])
        self.assertEqual(result["modification_journal_entry"]["entry_type"], "LEASE_MODIFICATION")
        self.assertEqual(result["subsequent_results"]["lease_term_months"], 24)

    def test_partial_termination_reduces_balances_proportionately(self):
        original = escalate_flat_payments(1000, "2024-01-01", "2025-12-01")
        revised = [{"date": row["date"], "amount": 750.0} for row in original if row["date"] >= "2025-01-01"]
        result = run_amended_calculation(
            {
                "commencement_date": "2024-01-01",
                "end_date": "2025-12-31",
                "monthly_payment": 1000.0,
                "discount_rate": 0.05,
                "explicit_payments": original,
            },
            revised,
            modification_date="2025-01-01",
            revised_discount_rate=0.05,
            scope_reduction_ratio=0.25,
            classification={"kind": KIND_PARTIAL_TERMINATION},
        )
        carrying = result["carrying"]
        partial = result["partial_termination"]
        self.assertAlmostEqual(partial["derecognized_liability"], round(carrying["liability"] * 0.25, 2))
        self.assertAlmostEqual(partial["derecognized_rou"], round(carrying["rou"] * 0.25, 2))
        self.assertEqual(
            partial["gain_loss"],
            round(partial["derecognized_liability"] - partial["derecognized_rou"], 2),
        )
        self.assertLess(result["remeasured_liability"], carrying["liability"])
        self.assertEqual(result["subsequent_results"]["lease_term_months"], 12)

    def test_northshore_third_amendment_uses_12800_schedule(self):
        measurement = build_measurement(
            LEASE,
            AMENDMENTS,
            HISTORY,
            as_of="2028-10-01",
            mode=MODE_REMEASUREMENT,
            commencement_date="2025-04-01",
            end_date="2035-03-31",
            fallback_monthly=24000.0,
            fallback_increase=0.03,
        )
        classified = measurement["classification"]
        self.assertEqual(classified["kind"], KIND_PARTIAL_TERMINATION)
        self.assertEqual(classified["governing_rsf"], 12800)
        self.assertEqual(measurement["revised_payments"][0]["amount"], 29941.33)
        self.assertEqual(len(measurement["revised_payments"]), 78)
        self.assertLess(measurement["first_original_monthly"], measurement["first_revised_monthly"])

        original_data = {
            "commencement_date": "2025-04-01",
            "end_date": "2035-03-31",
            "monthly_payment": 24000.0,
            "discount_rate": 0.05,
            "explicit_payments": measurement["original_payments"],
        }
        commencement = ASC842ComplianceEngine(
            {
                "commencement_date": "2025-04-01",
                "end_date": "2035-03-31",
                "monthly_payment": 24000.0,
                "discount_rate": 0.05,
                "annual_rent_increases": 0.03,
            }
        ).run_full_calculation()
        result = run_amended_calculation(
            original_data,
            measurement["revised_payments"],
            modification_date=measurement["modification_date"],
            revised_discount_rate=0.05,
            scope_reduction_ratio=classified["scope_reduction_ratio"],
            classification=classified,
        )
        self.assertEqual(result["modification_date"], "2028-10-01")
        self.assertNotEqual(result["remeasured_liability"], commencement["initial_liability"])
        self.assertGreater(result["remeasured_liability"], 0)
        self.assertGreater(result["carrying"]["periods_elapsed"], 30)
        self.assertIn(
            29941.33,
            [row["payment"] for row in result["subsequent_results"]["liability_schedule"][:3]],
        )


if __name__ == "__main__":
    unittest.main()
