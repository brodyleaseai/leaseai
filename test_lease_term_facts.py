"""De-identified lease-term warehouse."""

import unittest

from lease_term_facts import (
    build_term_facts,
    export_anonymized_facts,
    export_row,
    parse_market,
    summarize_facts,
    sync_lease_term_facts,
)


def _field(name, value, reviewed=None, confidence="HIGH"):
    return {
        "field_name": name,
        "raw_value": value,
        "reviewed_value": reviewed,
        "confidence": confidence,
    }


HARBOURVIEW_FIELDS = [
    _field("Tenant Legal Name", "Pacific Arc Robotics Inc."),
    _field("Landlord Legal Name", "Cedar Quay Holdings Ltd."),
    _field("Property Civic Address", "4100 Harbourview Parkway, Vancouver, BC"),
    _field("Premises Square Footage (RSF)", "18,000 rentable square feet"),
    _field("Base Rent Year 1 (monthly)", "$39,750.00"),
    _field("Lease Commencement Date", "2024-04-01"),
    _field("Lease Expiration Date", "2034-03-31"),
    _field("Lease Term (Total Months)", "120 months"),
    _field("Annual Escalation Rate or Cap", "3%"),
    _field("Annual Escalation Type (Fixed / CPI / Percentage)", "Percentage"),
    _field("CAM Annual Increase Cap (%)", "NOT FOUND"),
    _field("Number of Renewal Options", "1"),
    _field("Renewal Option Term Length", "5 years"),
    _field("Renewal Notice Deadline", "no later than nine (9) months"),
    _field("Security Deposit Amount", "$108,000.00"),
    _field("Building Class", "A"),
    _field("Lease Type (Gross / Net / Modified Gross)", "Net"),
    _field("Governing Law Jurisdiction", "British Columbia"),
]


class ParserTests(unittest.TestCase):
    def test_market_keeps_city_drops_street(self):
        market = parse_market("8800 Riverfront Dr, Richmond, BC")
        self.assertEqual(market["locality"], "Richmond")
        self.assertEqual(market["region"], "BC")
        self.assertEqual(market["country"], "CA")

    def test_street_only_is_not_stored_as_city(self):
        market = parse_market("4100 Harbourview Parkway")
        self.assertIsNone(market["locality"])
        self.assertIsNone(market["region"])


class FactBuilderTests(unittest.TestCase):
    def test_types_numbers_and_strips_parties(self):
        lease = {
            "id": "lease-hv",
            "client_id": "client-1",
            "status": "APPROVED",
            "tenant_name": "Pacific Arc Robotics Inc.",
            "property_address": "4100 Harbourview Parkway, Vancouver, BC",
        }
        fact = build_term_facts(lease, HARBOURVIEW_FIELDS, as_of="2026-11-12")
        self.assertEqual(fact["rsf"], 18000)
        self.assertEqual(fact["monthly_rent"], 39750.0)
        self.assertEqual(fact["annual_rent"], 477000.0)
        self.assertEqual(fact["rent_per_rsf_year"], 26.5)
        self.assertEqual(fact["escalation_pct"], 3.0)
        self.assertEqual(fact["commencement_year"], 2024)
        self.assertEqual(fact["term_months"], 120)
        self.assertEqual(fact["renewal_term_months"], 60)
        self.assertEqual(fact["locality"], "Vancouver")
        self.assertEqual(fact["region"], "BC")
        exported = export_row(fact)
        self.assertNotIn("lease_id", exported)
        self.assertNotIn("client_id", exported)
        blob = " ".join(str(value) for value in exported.values())
        self.assertNotIn("Pacific Arc", blob)
        self.assertNotIn("Cedar Quay", blob)
        self.assertNotIn("4100", blob)
        self.assertNotIn("Harbourview Parkway", blob)

    def test_current_clause_history_overrides_extract(self):
        lease = {"id": "lease-hv", "status": "APPROVED"}
        history = [
            {"clause_type": "Premises Description", "clause_value": "20,400 RSF", "is_current": True},
            {"clause_type": "Base Rent", "clause_value": "$42,500.00", "is_current": True},
        ]
        fact = build_term_facts(lease, HARBOURVIEW_FIELDS, history_rows=history)
        self.assertEqual(fact["rsf"], 20400)
        self.assertEqual(fact["monthly_rent"], 42500.0)
        self.assertEqual(fact["rent_per_rsf_year"], 25.0)

    def test_reviewed_value_wins(self):
        fact = build_term_facts(
            {"id": "x", "status": "APPROVED"},
            [_field("Premises Square Footage (RSF)", "10,000", reviewed="20,400")],
        )
        self.assertEqual(fact["rsf"], 20400)


class ExportConsentTests(unittest.TestCase):
    def test_export_skips_customers_who_did_not_opt_in(self):
        class _Result:
            def __init__(self, data):
                self.data = data

        class _Table:
            def __init__(self, name, rows):
                self.name = name
                self.rows = rows

            def select(self, *args, **kwargs):
                return self

            def execute(self):
                if self.name == "lease_term_facts_export":
                    raise RuntimeError("Could not find the table 'public.lease_term_facts_export' in the schema cache")
                return _Result(self.rows)

        class _Client:
            def __init__(self):
                self.tables = {
                    "lease_term_facts": [
                        {
                            "lease_id": "secret",
                            "client_id": "c-no",
                            "rsf": 10000,
                            "rent_per_rsf_year": 30.0,
                        },
                        {
                            "lease_id": "secret-2",
                            "client_id": "c-yes",
                            "rsf": 18000,
                            "rent_per_rsf_year": 26.5,
                            "locality": "Vancouver",
                        },
                    ],
                    "clients": [
                        {"id": "c-no", "allow_anonymized_corpus": False},
                        {"id": "c-yes", "allow_anonymized_corpus": True},
                    ],
                }

            def table(self, name):
                return _Table(name, self.tables[name])

        rows = export_anonymized_facts(_Client())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rsf"], 18000)
        self.assertNotIn("lease_id", rows[0])
        self.assertEqual(summarize_facts(rows)["leases"], 1)
        self.assertEqual(summarize_facts(rows)["avg_rent_per_rsf_year"], 26.5)


class SyncSkipTests(unittest.TestCase):
    def test_missing_table_is_quiet(self):
        class _Boom:
            def table(self, name):
                raise RuntimeError("Could not find the table 'public.lease_term_facts' in the schema cache")

        self.assertIsNone(sync_lease_term_facts(_Boom(), "lease-1"))


if __name__ == "__main__":
    unittest.main()
