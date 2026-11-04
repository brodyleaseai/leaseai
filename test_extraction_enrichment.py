"""Tests for rent-schedule and field enrichment after GPT extraction."""

import unittest

from extraction_enrichment import (
    build_full_rent_schedule,
    enrich_extracted_fields,
    monthly_from_annual_rate,
    parse_annual_rate_periods,
    parse_premises_rsf,
)


NORTHSHORE_SECTION_5 = """
Landlord leases to Tenant approximately 12,000 rentable square feet on the third floor
of the building municipally known as 8800 Riverfront Drive, Richmond, British Columbia.
5. BASE RENT
Tenant shall pay annual base rent in equal monthly instalments. Base Rent is calculated
on 12,000 rentable square feet at the following rates: April 1, 2025–March 31, 2026:
$24.00 per rentable square foot per annum; April 1, 2026–March 31, 2027: $24.72; April 1,
2027–March 31, 2028: $25.46; April 1, 2028–March 31, 2029: $26.22; April 1, 2029–March 31,
2030: $27.01; April 1, 2030–March 31, 2031: $27.82; April 1, 2031–March 31, 2032: $28.65;
April 1, 2032–March 31, 2033: $29.51; April 1, 2033–March 31, 2034: $30.40; and April 1,
2034–March 31, 2035: $31.31. The annual increases are intended to be approximately three
percent (3%) compounded on each April 1. If a discrepancy arises between the stated
dollar rate and the stated percentage, the stated dollar rate governs.
This Commercial Net Lease Agreement is made as of March 14, 2025 between
Northshore Meridian Properties Ltd., 880 West Pender Street, Suite 1450, Vancouver,
and Juniper Coast Analytics Inc. Landlord shall provide base building HVAC during
Building standard hours. Renewal Base Rent shall be the then-current fair market net rent.
"""


class ParserTests(unittest.TestCase):
    def test_parses_all_ten_northshore_rates(self):
        rsf = parse_premises_rsf(NORTHSHORE_SECTION_5)
        periods = parse_annual_rate_periods(NORTHSHORE_SECTION_5)
        self.assertEqual(rsf, 12000)
        self.assertEqual(len(periods), 10)
        self.assertEqual(periods[0]["annual_rate"], 24.00)
        self.assertEqual(periods[4]["annual_rate"], 27.01)
        self.assertEqual(periods[9]["annual_rate"], 31.31)
        self.assertEqual(monthly_from_annual_rate(12000, 24.00), 24000.00)
        self.assertEqual(monthly_from_annual_rate(12000, 24.72), 24720.00)
        self.assertEqual(monthly_from_annual_rate(12000, 31.31), 31310.00)

    def test_schedule_lists_every_year(self):
        periods = parse_annual_rate_periods(NORTHSHORE_SECTION_5)
        schedule, first_five = build_full_rent_schedule(periods, 12000)
        self.assertIn("Year 1", schedule)
        self.assertIn("Year 10", schedule)
        self.assertIn("$24,000.00/month", schedule)
        self.assertIn("$31,310.00/month", schedule)
        self.assertEqual(first_five[0], "$24,000.00")
        self.assertEqual(first_five[4], "$27,010.00")


class EnrichmentTests(unittest.TestCase):
    def test_fills_not_found_full_schedule_and_related_fields(self):
        gpt = {
            "Base Rent Year 1 (monthly)": {"value": "$24,000.00", "confidence": "HIGH"},
            "Base Rent Year 2 (monthly)": {"value": "$24,720.00", "confidence": "HIGH"},
            "Base Rent Year 3 (monthly)": {"value": "$25,460.00", "confidence": "HIGH"},
            "Base Rent Year 4 (monthly)": {"value": "$26,220.00", "confidence": "HIGH"},
            "Base Rent Year 5 (monthly)": {"value": "$27,010.00", "confidence": "HIGH"},
            "Full Rent Schedule (all years)": {"value": "NOT FOUND", "confidence": "LOW"},
            "Annual Escalation Type (Fixed / CPI / Percentage)": {
                "value": "NOT FOUND",
                "confidence": "LOW",
            },
            "Annual Escalation Rate or Cap": {"value": "NOT FOUND", "confidence": "LOW"},
            "Lease Type (Gross / Net / Modified Gross)": {"value": "NOT FOUND", "confidence": "LOW"},
            "Free Rent Period (months)": {"value": "NOT FOUND", "confidence": "LOW"},
            "HVAC Responsibility (Landlord / Tenant)": {"value": "NOT FOUND", "confidence": "LOW"},
            "Renewal Rent Basis (FMV / Fixed / CPI)": {"value": "NOT FOUND", "confidence": "LOW"},
            "Suite / Unit Number": {"value": "Suite 1450", "confidence": "HIGH"},
        }
        filled = enrich_extracted_fields(gpt, NORTHSHORE_SECTION_5)
        schedule = filled["Full Rent Schedule (all years)"]["value"]
        self.assertNotEqual(schedule, "NOT FOUND")
        self.assertIn("Year 10", schedule)
        self.assertEqual(filled["Full Rent Schedule (all years)"]["confidence"], "HIGH")
        self.assertEqual(filled["Annual Escalation Rate or Cap"]["value"], "3%")
        self.assertEqual(filled["Annual Escalation Type (Fixed / CPI / Percentage)"]["value"], "Percentage")
        self.assertEqual(filled["Lease Type (Gross / Net / Modified Gross)"]["value"], "Net")
        self.assertEqual(filled["Free Rent Period (months)"]["value"], "0 months")
        self.assertEqual(filled["HVAC Responsibility (Landlord / Tenant)"]["value"], "Landlord")
        self.assertEqual(filled["Renewal Rent Basis (FMV / Fixed / CPI)"]["value"], "FMV")
        self.assertEqual(filled["Suite / Unit Number"]["value"], "NOT FOUND")

    def test_assembles_schedule_from_year_fields_when_table_missing(self):
        gpt = {
            "Base Rent Year 1 (monthly)": {"value": "$8,550.08", "confidence": "HIGH"},
            "Base Rent Year 2 (monthly)": {"value": "$8,806.58", "confidence": "HIGH"},
            "Full Rent Schedule (all years)": {"value": "NOT FOUND", "confidence": "LOW"},
        }
        filled = enrich_extracted_fields(gpt, "Monthly rent of $8,550.08")
        self.assertIn("Year 1: $8,550.08", filled["Full Rent Schedule (all years)"]["value"])
        self.assertIn("Year 2: $8,806.58", filled["Full Rent Schedule (all years)"]["value"])

    def test_completes_northshore_from_stored_fields_without_lease_text(self):
        stored = {
            "Landlord Registered Address": {
                "raw_value": "880 West Pender Street, Suite 1450, Vancouver, British Columbia V6C 2T8",
                "confidence": "HIGH",
            },
            "Landlord Contact / Notice Address": {
                "raw_value": "880 West Pender Street, Suite 1450, Vancouver, British Columbia V6C 2T8",
                "confidence": "HIGH",
            },
            "Property Civic Address": {
                "raw_value": "8800 Riverfront Drive, Richmond, British Columbia V6X 1Y2",
                "confidence": "HIGH",
            },
            "Premises Square Footage (RSF)": {"raw_value": "12,000 sq ft", "confidence": "HIGH"},
            "Floor(s) Occupied": {"raw_value": "Third floor", "confidence": "HIGH"},
            "Suite / Unit Number": {"raw_value": "Suite 1450", "confidence": "HIGH"},
            "Lease Type (Gross / Net / Modified Gross)": {"raw_value": "NOT FOUND", "confidence": "LOW"},
            "Net Lease Type (Single / Double / Triple)": {"raw_value": "NOT FOUND", "confidence": "LOW"},
            "Lease Commencement Date": {"raw_value": "2025-04-01", "confidence": "HIGH"},
            "Lease Expiration Date": {"raw_value": "2035-03-31", "confidence": "HIGH"},
            "Lease Term (Total Months)": {"raw_value": "120 months", "confidence": "HIGH"},
            "Base Rent Year 1 (monthly)": {"raw_value": "$24,000.00", "confidence": "HIGH"},
            "Base Rent Year 2 (monthly)": {"raw_value": "$24,720.00", "confidence": "HIGH"},
            "Base Rent Year 3 (monthly)": {"raw_value": "$25,460.00", "confidence": "HIGH"},
            "Base Rent Year 4 (monthly)": {"raw_value": "$26,220.00", "confidence": "HIGH"},
            "Base Rent Year 5 (monthly)": {"raw_value": "$27,010.00", "confidence": "HIGH"},
            "Full Rent Schedule (all years)": {"raw_value": "NOT FOUND", "confidence": "LOW"},
            "Free Rent Period (months)": {"raw_value": "NOT FOUND", "confidence": "LOW"},
            "Annual Escalation Type (Fixed / CPI / Percentage)": {
                "raw_value": "NOT FOUND",
                "confidence": "LOW",
            },
            "Annual Escalation Rate or Cap": {"raw_value": "NOT FOUND", "confidence": "LOW"},
            "CAM / Operating Cost Charges": {
                "raw_value": (
                    "Tenant shall pay its proportionate share of Operating Costs, property "
                    "taxes, insurance costs, utilities not separately metered, and other "
                    "recoverable expenses"
                ),
                "confidence": "HIGH",
            },
            "Property Tax Responsibility": {"raw_value": "Tenant", "confidence": "HIGH"},
            "Property Insurance Responsibility": {"raw_value": "Tenant", "confidence": "HIGH"},
            "HVAC Responsibility (Landlord / Tenant)": {"raw_value": "NOT FOUND", "confidence": "LOW"},
            "HVAC Maintenance Obligation": {
                "raw_value": (
                    "Landlord shall provide base building HVAC during Building standard "
                    "hours, being 8:00 a.m. to 6:00 p.m. Monday through Friday, excluding "
                    "statutory holidays."
                ),
                "confidence": "HIGH",
            },
        }
        filled = enrich_extracted_fields(stored)
        schedule = filled["Full Rent Schedule (all years)"]["value"]
        self.assertIn("Year 1: $24,000.00", schedule)
        self.assertIn("Year 6: $27,820.00", schedule)
        self.assertIn("Year 10: $31,310.00", schedule)
        self.assertEqual(filled["Annual Escalation Rate or Cap"]["value"], "3%")
        self.assertEqual(filled["Annual Escalation Type (Fixed / CPI / Percentage)"]["value"], "Percentage")
        self.assertEqual(filled["Lease Type (Gross / Net / Modified Gross)"]["value"], "Net")
        self.assertEqual(filled["Net Lease Type (Single / Double / Triple)"]["value"], "Triple")
        self.assertEqual(filled["Free Rent Period (months)"]["value"], "0 months")
        self.assertEqual(filled["HVAC Responsibility (Landlord / Tenant)"]["value"], "Landlord")
        self.assertEqual(filled["Suite / Unit Number"]["value"], "NOT FOUND")


if __name__ == "__main__":
    unittest.main()
