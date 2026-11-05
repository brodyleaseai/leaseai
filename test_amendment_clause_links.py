"""Related-clause cascade for governing amendment terms."""

import unittest

from amendment_clause_links import (
    apply_related_clause_updates,
    derive_premises_description,
    derive_renewal_notice,
    derive_rent_escalations,
    derive_rent_schedule,
    expand_related_modifications,
    extract_order_of_precedence,
    extract_structural_clauses,
    is_execution_clause,
    parse_rate_periods,
    parse_rsf,
)


SECOND_AMENDMENT_RENT = """
5. BASE RENT. From April 1, 2027 to March 31, 2035, Tenant shall pay annual Base Rent
for the entire Premises, currently comprising 13,500 rentable square feet, at the following
rates: April 1, 2027–March 31, 2028: $27.25 per rentable square foot per annum;
April 1, 2028–March 31, 2029: $28.07; April 1, 2029–March 31, 2030: $28.91;
April 1, 2030–March 31, 2031: $29.78; April 1, 2031–March 31, 2032: $30.67;
April 1, 2032–March 31, 2033: $31.59; April 1, 2033–March 31, 2034: $32.54;
and April 1, 2034–March 31, 2035: $33.52. Annual Base Rent shall be paid in twelve
equal monthly instalments in advance. The rates in this Section are fixed dollar rates and
replace, not supplement, any annual percentage escalation formula. No additional 3%
escalation shall be applied.
"""

NOTICE_TEXT = (
    'The words “not later than nine (9) months” in Section 15 of the Lease are deleted '
    "and replaced with “not later than twelve (12) months”."
)

ORIGINAL_SCHEDULE = (
    "Year 1 (April 1, 2025–March 31, 2026): $24.00/RSF/year = $24,000.00/month; "
    "Year 10 (April 1, 2034–March 31, 2035): $31.31/RSF/year = $31,310.00/month"
)


class ParserTests(unittest.TestCase):
    def test_parses_second_amendment_rates_and_rsf(self):
        self.assertEqual(parse_rsf(SECOND_AMENDMENT_RENT), 13500)
        periods = parse_rate_periods(SECOND_AMENDMENT_RENT)
        self.assertEqual(len(periods), 8)
        self.assertEqual(periods[0]["annual_rate"], 27.25)
        self.assertEqual(periods[-1]["annual_rate"], 33.52)

    def test_derives_monthly_schedule_on_13500_rsf(self):
        schedule = derive_rent_schedule(SECOND_AMENDMENT_RENT)
        self.assertIn("Year 1 (April 1, 2027–March 31, 2028)", schedule)
        self.assertIn("$27.25/RSF/year = $30,656.25/month", schedule)
        self.assertIn("$33.52/RSF/year = $37,710.00/month", schedule)
        self.assertEqual(derive_rent_escalations(SECOND_AMENDMENT_RENT), "None — fixed dollar rates replace any percentage escalation")
        self.assertEqual(derive_premises_description(SECOND_AMENDMENT_RENT), "13,500 sq ft")
        self.assertEqual(derive_renewal_notice(NOTICE_TEXT), "12 months before the Expiry Date")


class ExpandTests(unittest.TestCase):
    def test_base_rent_adds_schedule_and_escalation(self):
        expanded = expand_related_modifications(
            [
                {
                    "clause_type": "Base Rent",
                    "modification_type": "SUPERSEDES",
                    "new_value": SECOND_AMENDMENT_RENT,
                    "original_value": "$24,000",
                    "effective_date": "2027-04-01",
                }
            ],
            existing_originals={
                "Rent Schedule": ORIGINAL_SCHEDULE,
                "Rent Escalations": "3%",
            },
        )
        types = [row["clause_type"] for row in expanded]
        self.assertEqual(types[:3], ["Base Rent", "Rent Schedule", "Rent Escalations"])
        schedule = next(row for row in expanded if row["clause_type"] == "Rent Schedule")
        self.assertIn("$30,656.25/month", schedule["new_value"])
        self.assertEqual(schedule["original_value"], ORIGINAL_SCHEDULE)
        self.assertEqual(schedule["linked_from"], "Base Rent")


class ModelCascadeTests(unittest.TestCase):
    def test_moves_schedule_b_rent_off_the_original_lease(self):
        clauses = apply_related_clause_updates(
            [
                {
                    "clause_type": "Base Rent",
                    "changed": True,
                    "original_value": "$24,000",
                    "governing_value": SECOND_AMENDMENT_RENT,
                    "governing_label": "Amendment No. 2 (2027-02-12)",
                    "governing_amendment_number": 2,
                    "effective_from": "2027-04-01",
                },
                {
                    "clause_type": "Rent Schedule",
                    "changed": False,
                    "original_value": ORIGINAL_SCHEDULE,
                    "governing_value": ORIGINAL_SCHEDULE,
                    "governing_label": "Original lease",
                },
                {
                    "clause_type": "Rent Escalations",
                    "changed": False,
                    "original_value": "3%",
                    "governing_value": "3%",
                    "governing_label": "Original lease",
                },
                {
                    "clause_type": "CAM Charges",
                    "changed": False,
                    "original_value": "Tenant pays its share",
                    "governing_value": "Tenant pays its share",
                },
            ]
        )
        by_type = {clause["clause_type"]: clause for clause in clauses}
        self.assertTrue(by_type["Rent Schedule"]["changed"])
        self.assertIn("$37,710.00/month", by_type["Rent Schedule"]["governing_value"])
        self.assertEqual(by_type["Rent Schedule"]["linked_from"], "Base Rent")
        self.assertTrue(by_type["Rent Escalations"]["changed"])
        self.assertIn("fixed dollar rates", by_type["Rent Escalations"]["governing_value"])
        self.assertFalse(by_type["CAM Charges"]["changed"])

    def test_third_amendment_rebases_schedule_on_12800_rsf(self):
        third_rent = (
            "From and after October 1, 2028, Base Rent shall be calculated using the "
            "then-applicable rate multiplied by 12,800 rentable square feet, rather than "
            "13,500 rentable square feet. For clarity, the applicable rate from April 1, "
            "2028 to March 31, 2029 remains $28.07 per rentable square foot per annum; "
            "only the rentable area used in the calculation changes."
        )
        clauses = apply_related_clause_updates(
            [
                {
                    "clause_type": "Base Rent",
                    "changed": True,
                    "original_value": "$24,000",
                    "governing_value": third_rent,
                    "governing_label": "Amendment No. 3 (2028-09-20)",
                    "governing_amendment_number": 3,
                    "effective_from": "2028-10-01",
                    "versions": [
                        {"clause_value": "$24,000"},
                        {"clause_value": SECOND_AMENDMENT_RENT},
                        {"clause_value": third_rent},
                    ],
                },
                {
                    "clause_type": "Premises Description",
                    "changed": True,
                    "original_value": "12,000 sq ft",
                    "governing_value": "From and after the Surrender Effective Date, the Premises shall comprise 12,800 rentable square feet.",
                    "governing_label": "Amendment No. 3 (2028-09-20)",
                    "governing_amendment_number": 3,
                    "effective_from": "2028-10-01",
                },
                {
                    "clause_type": "Rent Schedule",
                    "changed": True,
                    "original_value": ORIGINAL_SCHEDULE,
                    "governing_value": derive_rent_schedule(SECOND_AMENDMENT_RENT),
                    "governing_label": "Amendment No. 2 (2027-02-12)",
                    "governing_amendment_number": 2,
                    "effective_from": "2027-04-01",
                },
                {
                    "clause_type": "Rent Escalations",
                    "changed": True,
                    "original_value": "3%",
                    "governing_value": "None — fixed dollar rates replace any percentage escalation",
                    "governing_amendment_number": 2,
                },
            ]
        )
        schedule = next(clause for clause in clauses if clause["clause_type"] == "Rent Schedule")
        self.assertIn("From October 1, 2028 on 12,800 RSF", schedule["governing_value"])
        self.assertIn("$28.07/RSF/year = $29,941.33/month", schedule["governing_value"])
        self.assertIn("$33.52/RSF/year = $35,754.67/month", schedule["governing_value"])
        self.assertNotIn("$30,656.25/month", schedule["governing_value"])
        self.assertNotIn("$24,000.00/month", schedule["governing_value"])
        self.assertEqual(schedule["governing_amendment_number"], 3)


class StructuralClauseTests(unittest.TestCase):
    def test_extracts_order_of_precedence_and_skips_execution(self):
        text = """
7. ORDER OF PRECEDENCE
If this Third Amendment conflicts with the Second Amendment, First Amendment, or original Lease, this Third Amendment
governs to the extent of the conflict, but only from the applicable effective date stated herein. The Second Amendment
continues to govern the Base Rent rates and renewal notice period except as expressly modified by this Third Amendment. All
other provisions remain in force.
8. EXECUTION
Executed as of the date first written above.
LANDLORD: NORTHSHORE MERIDIAN PROPERTIES LTD.
"""
        precedence = extract_order_of_precedence(text)
        self.assertIn("this Third Amendment governs", precedence)
        self.assertIn("Second Amendment continues to govern the Base Rent rates", precedence)
        self.assertNotIn("LANDLORD", precedence)
        extras = extract_structural_clauses(text, "2028-10-01")
        self.assertEqual([row["clause_type"] for row in extras], ["Order of Precedence"])
        self.assertTrue(is_execution_clause("Execution", "Executed as of the date first written above."))
        self.assertFalse(is_execution_clause("Order of Precedence", extras[0]["new_value"]))


if __name__ == "__main__":
    unittest.main()
