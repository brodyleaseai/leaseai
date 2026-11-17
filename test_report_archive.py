"""Generated-report archive and complete CAM workpaper persistence."""

import sys
import unittest
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from report_archive import (  # noqa: E402
    REPORT_KIND_CAM_WORKPAPER,
    REPORT_KIND_LEASE_ABSTRACT,
    cam_reconciliation_record,
    fetch_stored_report,
    line_item_record,
    persist_cam_reconciliation,
    persist_generated_report,
    sha256_bytes,
)


class FakeExecute:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self._op = "select"
        self._payload = None
        self._filters = []
        self._on_conflict = None
        self._order = None

    def select(self, *_args, **_kwargs):
        self._op = "select"
        return self

    def insert(self, record):
        self._op = "insert"
        self._payload = record
        return self

    def upsert(self, record, on_conflict=None):
        self._op = "upsert"
        self._payload = record
        self._on_conflict = on_conflict
        return self

    def update(self, record):
        self._op = "update"
        self._payload = record
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def order(self, column, desc=False):
        self._order = (column, desc)
        return self

    def _rows(self):
        return self.db.setdefault(self.table, [])

    def _match(self, row):
        return all(row.get(key) == value for key, value in self._filters)

    def execute(self):
        rows = self._rows()
        if self._op == "insert":
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for rec in payload:
                row = dict(rec)
                row.setdefault("id", str(uuid.uuid4()))
                rows.append(row)
                inserted.append(row)
            return FakeExecute(inserted)
        if self._op == "upsert":
            rec = dict(self._payload)
            keys = [part.strip() for part in (self._on_conflict or "id").split(",") if part.strip()]
            for existing in rows:
                if keys and all(existing.get(key) == rec.get(key) for key in keys):
                    existing.update(rec)
                    existing.setdefault("id", str(uuid.uuid4()))
                    return FakeExecute([existing])
            rec.setdefault("id", str(uuid.uuid4()))
            rows.append(rec)
            return FakeExecute([rec])
        if self._op == "update":
            updated = []
            for row in rows:
                if self._match(row):
                    row.update(self._payload)
                    updated.append(row)
            return FakeExecute(updated)
        if self._op == "delete":
            kept = []
            deleted = []
            for row in rows:
                if self._match(row):
                    deleted.append(row)
                else:
                    kept.append(row)
            self.db[self.table] = kept
            return FakeExecute(deleted)
        matched = [row for row in rows if self._match(row)]
        if self._order:
            column, desc = self._order
            matched.sort(key=lambda row: row.get(column) or "", reverse=bool(desc))
        return FakeExecute(matched)


class FakeBucket:
    def __init__(self, storage, name):
        self.storage = storage
        self.name = name

    def upload(self, path, data, options=None):
        if self.storage.fail_storage:
            raise RuntimeError("Bucket not found")
        self.storage.files[(self.name, path)] = bytes(data)
        return {"path": path}

    def download(self, path):
        if self.storage.fail_storage:
            raise RuntimeError("Bucket not found")
        data = self.storage.files.get((self.name, path))
        if data is None:
            raise RuntimeError("not found")
        return data


class FakeStorage:
    def __init__(self, fail_storage=False):
        self.files = {}
        self.buckets = set()
        self.fail_storage = fail_storage
        self.storage_url = "https://example.supabase.co/storage/v1"

    def from_(self, name):
        return FakeBucket(self, name)

    def create_bucket(self, name, options=None):
        if self.fail_storage:
            raise RuntimeError("cannot create bucket")
        self.buckets.add(name)
        return {"name": name}


class FakeSB:
    def __init__(self, fail_storage=False):
        self.db = {
            "leases": [
                {
                    "id": "lease-ironwood",
                    "client_id": "client-1",
                    "property_address": "4100 Ironwood Parkway",
                    "tenant_name": "Ironwood Grocery LLC",
                }
            ],
            "cam_reconciliations": [],
            "cam_line_items": [],
            "generated_reports": [],
        }
        self.storage = FakeStorage(fail_storage=fail_storage)

    def table(self, name):
        return FakeQuery(self.db, name)


def _ironwood_results():
    return {
        "lease_id": "lease-ironwood",
        "recon_year": 2024,
        "statement_date": date(2025, 3, 15),
        "landlord_total": 144600,
        "tenant_share_billed": 144600,
        "calculated_share": 100000,
        "variance": 44600,
        "variance_percentage": 44.6,
        "excluded_building_charges": 44600,
        "allowable_building_charges": 100000,
        "cam_cap_applied": False,
        "estimated_cam_paid": 84000,
        "landlord_trueup_billed": 60600,
        "lease_remaining_due": 16000,
        "calculations": [{"step": "pro-rata", "result": 100000}],
    }


def _ironwood_lines():
    return [
        {
            "category": "CAPITAL",
            "description": "Roof replacement",
            "amount": 40000,
            "should_challenge": True,
            "is_excluded": True,
            "dispute_reason": "Capital improvement excluded",
            "recommended_action": "CHALLENGE",
            "calculated_amount": 0,
            "variance_amount": 40000,
        },
        {
            "category": "UTILITIES",
            "description": "Electric",
            "amount": 12000,
            "should_challenge": False,
            "calculated_amount": 12000,
            "variance_amount": 0,
        },
    ]


class PersistGeneratedReportTests(unittest.TestCase):
    def test_archives_lease_abstract_pdf_under_lease_and_kind(self):
        sb = FakeSB()
        pdf = b"%PDF-abstract-ironwood"
        saved = persist_generated_report(
            sb,
            lease_id="lease-ironwood",
            kind=REPORT_KIND_LEASE_ABSTRACT,
            pdf_bytes=pdf,
            filename="Lease Abstract - Ironwood Grocery.pdf",
            user_id="user-1",
        )
        self.assertTrue(saved["pdf_stored"])
        self.assertEqual(saved["content_sha256"], sha256_bytes(pdf))
        row = sb.db["generated_reports"][0]
        self.assertEqual(row["report_kind"], REPORT_KIND_LEASE_ABSTRACT)
        self.assertEqual(row["client_id"], "client-1")
        self.assertEqual(row["lease_id"], "lease-ironwood")
        self.assertIn("LEASE_ABSTRACT", row["storage_path"])
        stored = sb.storage.files[(row["storage_bucket"], row["storage_path"])]
        self.assertEqual(stored, pdf)


class PersistCamWorkpaperTests(unittest.TestCase):
    def test_saves_settlement_line_items_and_pdf(self):
        sb = FakeSB()
        pdf = b"%PDF-cam-ironwood-workpaper"
        saved = persist_cam_reconciliation(
            sb,
            lease_id="lease-ironwood",
            results=_ironwood_results(),
            line_items=_ironwood_lines(),
            pdf_bytes=pdf,
            filename="CAM_Workpaper_Ironwood_2024.pdf",
            user_id="user-1",
        )
        self.assertEqual(saved["line_item_count"], 2)
        self.assertEqual(saved["lease_remaining_due"], 16000.0)
        self.assertEqual(saved["estimated_cam_paid"], 84000.0)
        self.assertTrue(saved["pdf_stored"])

        recon = sb.db["cam_reconciliations"][0]
        self.assertEqual(recon["estimated_cam_paid"], 84000.0)
        self.assertEqual(recon["lease_remaining_due"], 16000.0)
        self.assertEqual(recon["calculated_total_charges"], 100000.0)
        self.assertEqual(recon["generated_report_id"], saved["generated_report_id"])
        self.assertTrue(recon["reconciliation_report_url"])

        lines = sb.db["cam_line_items"]
        self.assertEqual(len(lines), 2)
        roof = next(item for item in lines if "Roof" in (item["description"] or ""))
        self.assertTrue(roof["should_challenge"])
        self.assertEqual(roof["recommended_action"], "CHALLENGE")
        electric = next(item for item in lines if item["category"] == "UTILITIES")
        self.assertEqual(electric["variance_amount"], 0.0)
        self.assertFalse(electric["should_challenge"])

        fetched = fetch_stored_report(sb, reconciliation_id=saved["reconciliation_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["pdf_bytes"], pdf)
        self.assertEqual(fetched["row"]["report_kind"], REPORT_KIND_CAM_WORKPAPER)

    def test_upsert_replaces_same_lease_year_and_line_items(self):
        sb = FakeSB()
        first = persist_cam_reconciliation(
            sb,
            lease_id="lease-ironwood",
            results=_ironwood_results(),
            line_items=_ironwood_lines(),
            pdf_bytes=b"%PDF-one",
            filename="one.pdf",
        )
        updated = dict(_ironwood_results())
        updated["lease_remaining_due"] = 0
        updated["estimated_cam_paid"] = 100000
        second = persist_cam_reconciliation(
            sb,
            lease_id="lease-ironwood",
            results=updated,
            line_items=_ironwood_lines()[:1],
            pdf_bytes=b"%PDF-two",
            filename="two.pdf",
        )
        self.assertEqual(first["reconciliation_id"], second["reconciliation_id"])
        self.assertEqual(len(sb.db["cam_reconciliations"]), 1)
        self.assertEqual(sb.db["cam_reconciliations"][0]["lease_remaining_due"], 0.0)
        self.assertEqual(len(sb.db["cam_line_items"]), 1)
        self.assertEqual(len(sb.db["generated_reports"]), 2)

    def test_storage_failure_still_saves_numbers_and_lines(self):
        sb = FakeSB(fail_storage=True)
        saved = persist_cam_reconciliation(
            sb,
            lease_id="lease-ironwood",
            results=_ironwood_results(),
            line_items=_ironwood_lines(),
            pdf_bytes=b"%PDF-missing-bucket",
            filename="CAM.pdf",
        )
        self.assertFalse(saved["pdf_stored"])
        self.assertEqual(len(sb.db["cam_reconciliations"]), 1)
        self.assertEqual(len(sb.db["cam_line_items"]), 2)
        self.assertEqual(len(sb.db["generated_reports"]), 1)
        self.assertIn("storage_error", sb.db["generated_reports"][0]["metadata"])


class MappingTests(unittest.TestCase):
    def test_recon_record_uses_allowable_not_landlord_total(self):
        record = cam_reconciliation_record("lease-ironwood", _ironwood_results(), "user-1")
        self.assertEqual(record["calculated_total_charges"], 100000.0)
        self.assertEqual(record["lease_remaining_due"], 16000.0)
        self.assertEqual(record["dispute_status"], "CHALLENGE_DRAFTED")

    def test_line_item_maps_engine_flags(self):
        row = line_item_record("recon-1", _ironwood_lines()[0], 0)
        self.assertTrue(row["should_challenge"])
        self.assertTrue(row["is_excluded"])
        self.assertEqual(row["landlord_amount"], 40000.0)


if __name__ == "__main__":
    unittest.main()
