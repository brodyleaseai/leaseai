"""Computed rent schedule is separate from extracted HIGH quotes."""

import unittest
from datetime import date

from computed_rent_schedule import (
    COMPUTED_FIELD,
    META_KEY,
    apply_computed_rent_schedule,
    computed_monthly,
    plan_rent_schedule,
)
from lease_report import generate_lease_abstract_pdf


def _ironwood_fields(**overrides):
    fields = {
        "Base Rent Year 1 (monthly)": {
            "value": "$18,666.67",
            "confidence": "HIGH",
            "source_snippet": "Base Rent Year 1 (monthly): $18,666.67.",
        },
        "Base Rent Year 2 (monthly)": {
            "value": "$19,133.33",
            "confidence": "HIGH",
            "source_snippet": (
                "Full Rent Schedule (all years): Year 1 $224,000.00, "
                "increasing 2.5% annually for the remainder of the ten-year term."
            ),
        },
        "Base Rent Year 3 (monthly)": {
            "value": "$19,611.67",
            "confidence": "HIGH",
            "source_snippet": (
                "Full Rent Schedule (all years): Year 1 $224,000.00, "
                "increasing 2.5% annually for the remainder of the ten-year term."
            ),
        },
        "Full Rent Schedule (all years)": {
            "value": "Year 1 $224,000.00, increasing 2.5% annually for the remainder of the ten-year term.",
            "confidence": "HIGH",
            "source_snippet": (
                "Full Rent Schedule (all years): Year 1 $224,000.00, "
                "increasing 2.5% annually for the remainder of the ten-year term."
            ),
        },
        "Annual Escalation Type (Fixed / CPI / Percentage)": {
            "value": "Fixed",
            "confidence": "HIGH",
            "source_snippet": "fixed two and one-half percent (2.5%) Annual Escalation Type",
        },
        "Annual Escalation Rate or Cap": {
            "value": "2.5%",
            "confidence": "HIGH",
            "source_snippet": "Annual Escalation Rate or Cap of 2.5%.",
        },
        "Rent Commencement Date": {
            "value": "2022-04-01",
            "confidence": "HIGH",
            "source_snippet": "Rent Commencement Date: April 1, 2022.",
        },
        "Lease Commencement Date": {
            "value": "2022-03-01",
            "confidence": "HIGH",
            "source_snippet": "Lease Commencement Date: March 1, 2022.",
        },
        "Lease Expiration Date": {
            "value": "2032-02-28",
            "confidence": "HIGH",
            "source_snippet": "Lease Expiration Date: February 28, 2032.",
        },
        "Lease Term (Total Months)": {
            "value": "120 months",
            "confidence": "HIGH",
            "source_snippet": "Lease Term (Total Months): 120 months.",
        },
        "Landlord Legal Name": {
            "value": "Ironwood Retail Partners, LLC",
            "confidence": "HIGH",
            "source_snippet": "The Landlord Legal Name is Ironwood Retail Partners, LLC.",
        },
    }
    fields.update(overrides)
    return fields


class MathTests(unittest.TestCase):
    def test_compounds_monthly_half_up_to_the_cent(self):
        self.assertEqual(computed_monthly(18666.67, 2.5, 1), 18666.67)
        self.assertEqual(computed_monthly(18666.67, 2.5, 2), 19133.34)
        self.assertEqual(computed_monthly(18666.67, 2.5, 3), 19611.67)


class IronwoodPlanTests(unittest.TestCase):
    def test_ten_year_schedule_uses_rent_commencement_and_binds_last_stub(self):
        plan = plan_rent_schedule(_ironwood_fields())
        self.assertTrue(plan["computed"])
        self.assertEqual(len(plan["rows"]), 10)
        self.assertEqual(plan["rows"][0]["start"], date(2022, 4, 1))
        self.assertEqual(plan["rows"][0]["end"], date(2023, 3, 31))
        self.assertEqual(plan["rows"][0]["basis"], "Extracted")
        self.assertEqual(plan["rows"][0]["monthly"], 18666.67)
        self.assertEqual(plan["rows"][1]["basis"], "Calculated")
        self.assertEqual(plan["rows"][1]["monthly"], 19133.34)
        self.assertEqual(plan["rows"][-1]["year"], 10)
        self.assertEqual(plan["rows"][-1]["start"], date(2031, 4, 1))
        self.assertEqual(plan["rows"][-1]["end"], date(2032, 2, 28))
        self.assertEqual(plan["rows"][-1]["months"], 11)
        self.assertIn("2.5%", plan["method"])
        self.assertIn("rent commencement", plan["method"])

    def test_unstated_year_two_is_filled_as_calculated(self):
        updated = apply_computed_rent_schedule(_ironwood_fields())
        year2 = updated["Base Rent Year 2 (monthly)"]
        self.assertEqual(year2["value"], "$19,133.34")
        self.assertEqual(year2["confidence"], "COMPUTED")
        self.assertIn("Base Rent Year 1", year2["derived_from"])
        self.assertIn(
            "Year 1 $224,000.00, increasing 2.5% annually",
            updated["Full Rent Schedule (all years)"]["value"],
        )
        self.assertIn("Year 10 |", updated[COMPUTED_FIELD]["value"])
        self.assertEqual(updated[COMPUTED_FIELD]["confidence"], "COMPUTED")
        self.assertEqual(len(updated[META_KEY]["rows"]), 10)

    def test_not_found_years_are_filled_from_year_one_formula(self):
        fields = _ironwood_fields()
        for year in range(2, 6):
            fields[f"Base Rent Year {year} (monthly)"] = {
                "value": "NOT FOUND",
                "confidence": "LOW",
                "source_snippet": "",
            }
        updated = apply_computed_rent_schedule(fields)
        self.assertEqual(updated["Base Rent Year 2 (monthly)"]["value"], "$19,133.34")
        self.assertEqual(updated["Base Rent Year 2 (monthly)"]["confidence"], "COMPUTED")
        self.assertEqual(updated["Base Rent Year 5 (monthly)"]["confidence"], "COMPUTED")
        self.assertTrue(updated[META_KEY]["computed"])
        self.assertEqual(len(updated[META_KEY]["rows"]), 10)

    def test_stated_year_two_stays_extracted(self):
        fields = _ironwood_fields()
        fields["Base Rent Year 2 (monthly)"] = {
            "value": "$19,133.34",
            "confidence": "HIGH",
            "source_snippet": "Base Rent Year 2 (monthly): $19,133.34.",
        }
        updated = apply_computed_rent_schedule(fields)
        self.assertEqual(updated["Base Rent Year 2 (monthly)"]["value"], "$19,133.34")
        self.assertEqual(updated["Base Rent Year 2 (monthly)"]["confidence"], "HIGH")
        self.assertEqual(updated[META_KEY]["rows"][1]["basis"], "Extracted")
        self.assertEqual(updated[META_KEY]["rows"][2]["basis"], "Calculated")


class SkipTests(unittest.TestCase):
    def test_cpi_is_not_expanded(self):
        fields = _ironwood_fields()
        fields["Annual Escalation Type (Fixed / CPI / Percentage)"] = {
            "value": "CPI",
            "confidence": "HIGH",
            "source_snippet": "increases annually by CPI",
        }
        plan = plan_rent_schedule(fields)
        self.assertFalse(plan["computed"])
        self.assertIn("CPI", plan["reason"])

    def test_missing_dates_are_not_guessed(self):
        fields = _ironwood_fields()
        fields["Rent Commencement Date"]["value"] = "NOT FOUND"
        fields["Lease Commencement Date"]["value"] = "NOT FOUND"
        plan = plan_rent_schedule(fields)
        self.assertFalse(plan["computed"])
        self.assertIn("anniversary", plan["reason"])


class AbstractPdfTests(unittest.TestCase):
    def test_pdf_shows_computed_table_not_invented_high_year_two(self):
        pdf_bytes = generate_lease_abstract_pdf(
            {
                "property_address": "4800 East Colfax Avenue, Denver, Colorado 80220",
                "tenant_name": "Pinnacle Grocery Company",
            },
            _ironwood_fields(),
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        text = _pdf_text(pdf_bytes)
        self.assertIn("Base Rent Schedule", text)
        self.assertIn("19,133.34", text)
        self.assertIn("Calculated", text)
        self.assertIn("Calculated: $19,133.34", text)
        self.assertNotIn("Not stated in the lease", text)
        self.assertIn("Apr 1, 2031", text)
        self.assertIn("2.5%", text)
        self.assertNotIn("$19,133.33", text)
        self.assertNotRegex(text, r"Base Rent Year 2 \(Monthly\)\s+NOT FOUND")

    def test_pdf_fills_not_found_year_slots_from_report_two(self):
        fields = _ironwood_fields()
        for year in range(2, 6):
            fields[f"Base Rent Year {year} (monthly)"] = {
                "value": "NOT FOUND",
                "confidence": "LOW",
                "source_snippet": "",
            }
        text = _pdf_text(generate_lease_abstract_pdf(
            {
                "property_address": "4800 East Colfax Avenue, Denver, Colorado 80220",
                "tenant_name": "Pinnacle Grocery Company",
            },
            fields,
        ))
        self.assertIn("Base Rent Schedule", text)
        self.assertIn("CALCULATED", text)
        self.assertIn("Calculated: $19,133.34", text)
        self.assertIn("Apr 1, 2031", text)
        self.assertIn("23,312.11", text)
        self.assertNotRegex(text, r"Base Rent Year 2 \(Monthly\)\s+NOT FOUND")


def _pdf_text(pdf_bytes: bytes) -> str:
    import tempfile
    from pathlib import Path

    import pdfplumber

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(pdf_bytes)
        path = Path(handle.name)
    try:
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return "\n".join(pages)
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
