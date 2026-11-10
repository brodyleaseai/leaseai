"""Re-processing the same amendment number must replace, not insert."""

import unittest

from amendment_processor_v2 import AmendmentProcessorV2


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.action = "select"
        self.filters = []
        self.payload = None
        self.limit_n = None
        self.order_by = None

    def select(self, *args, **kwargs):
        self.action = "select"
        return self

    def insert(self, payload):
        self.action = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, count):
        self.limit_n = count
        return self

    def order(self, column, desc=False, **kwargs):
        self.order_by = (column, desc)
        return self

    def _matches(self, row):
        return all(row.get(column) == value for column, value in self.filters)

    def execute(self):
        if self.action == "insert":
            row = dict(self.payload)
            row.setdefault("id", f"new-{len(self.rows) + 1}")
            self.rows.append(row)
            return FakeResponse([row])
        matched = [row for row in self.rows if self._matches(row)]
        if self.action == "update":
            for row in matched:
                row.update(self.payload)
            return FakeResponse(matched)
        if self.action == "delete":
            remaining = [row for row in self.rows if not self._matches(row)]
            self.rows[:] = remaining
            return FakeResponse(matched)
        rows = list(matched)
        if self.order_by:
            column, desc = self.order_by
            rows.sort(key=lambda row: row.get(column) if row.get(column) is not None else 0, reverse=desc)
        if self.limit_n:
            rows = rows[: self.limit_n]
        return FakeResponse(rows)


class FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeTable(self.tables.setdefault(name, []))


class ReprocessTests(unittest.TestCase):
    def test_replaces_existing_amendment_number_instead_of_inserting(self):
        tables = {
            "amendments": [
                {
                    "id": "amd-3",
                    "lease_id": "lease-1",
                    "amendment_number": 3,
                    "status": "READY FOR REVIEW",
                }
            ],
            "amendment_clauses": [
                {
                    "id": "clause-old",
                    "amendment_id": "amd-3",
                    "clause_type": "Base Rent",
                    "new_value": "old extract",
                }
            ],
            "lease_clause_history": [
                {
                    "id": "hist-0",
                    "lease_id": "lease-1",
                    "clause_type": "Base Rent",
                    "version_number": 0,
                    "source_document_id": "lease-1",
                    "is_current": False,
                    "effective_to": "2028-10-01",
                },
                {
                    "id": "hist-3",
                    "lease_id": "lease-1",
                    "clause_type": "Base Rent",
                    "version_number": 3,
                    "source_document_id": "amd-3",
                    "is_current": True,
                    "effective_to": None,
                },
            ],
        }
        client = FakeSupabase(tables)
        processor = AmendmentProcessorV2.__new__(AmendmentProcessorV2)
        amendment_id, replaced = processor._save_amendment_record(
            "lease-1",
            3,
            {
                "lease_id": "lease-1",
                "amendment_number": 3,
                "status": "PROCESSING",
                "extracted_data": {"amendment_text": "Third Amendment"},
                "created_at": "2026-11-05T00:00:00",
            },
            client,
        )
        self.assertTrue(replaced)
        self.assertEqual(amendment_id, "amd-3")
        self.assertEqual(len(tables["amendments"]), 1)
        self.assertEqual(tables["amendments"][0]["status"], "PROCESSING")
        self.assertEqual(tables["amendment_clauses"], [])
        self.assertEqual([row["id"] for row in tables["lease_clause_history"]], ["hist-0"])
        self.assertTrue(tables["lease_clause_history"][0]["is_current"])
        self.assertIsNone(tables["lease_clause_history"][0]["effective_to"])

    def test_inserts_when_amendment_number_is_new(self):
        tables = {"amendments": [], "amendment_clauses": [], "lease_clause_history": []}
        client = FakeSupabase(tables)
        processor = AmendmentProcessorV2.__new__(AmendmentProcessorV2)
        amendment_id, replaced = processor._save_amendment_record(
            "lease-1",
            3,
            {"lease_id": "lease-1", "amendment_number": 3, "status": "PROCESSING"},
            client,
        )
        self.assertFalse(replaced)
        self.assertEqual(len(tables["amendments"]), 1)
        self.assertEqual(tables["amendments"][0]["id"], amendment_id)


class AmendmentNumberTests(unittest.TestCase):
    def test_ui_number_overrides_extracted_first_amendment(self):
        processor = AmendmentProcessorV2.__new__(AmendmentProcessorV2)
        self.assertEqual(
            processor._resolve_amendment_number({"value": "First Amendment"}, 2),
            2,
        )
        self.assertEqual(processor._parse_amendment_number("Second Amendment"), 2)


if __name__ == "__main__":
    unittest.main()
