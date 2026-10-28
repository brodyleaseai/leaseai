"""Tests for lease delete helpers."""

from lease_delete import CHILD_TABLES, delete_lease, delete_leases


class _FakeQuery:
    def __init__(self, store, table):
        self.store = store
        self.table_name = table
        self._ids = []
        self._column = None

    def delete(self):
        return self

    def in_(self, column, ids):
        self._column = column
        self._ids = list(ids)
        return self

    def execute(self):
        if self.table_name not in self.store:
            raise Exception(f'does not exist: {self.table_name}')
        before = len(self.store[self.table_name])
        self.store[self.table_name] = [
            row for row in self.store[self.table_name]
            if str(row.get(self._column)) not in {str(i) for i in self._ids}
        ]
        return type("R", (), {"data": []})()


class _FakeSB:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return _FakeQuery(self.store, name)


def test_delete_leases_removes_children_and_lease():
    store = {
        "extracted_fields": [{"lease_id": "a", "id": 1}, {"lease_id": "b", "id": 2}],
        "critical_dates": [{"lease_id": "a"}],
        "leases": [{"id": "a"}, {"id": "b"}],
    }
    count = delete_leases(_FakeSB(store), ["a"])
    assert count == 1
    assert store["leases"] == [{"id": "b"}]
    assert store["extracted_fields"] == [{"lease_id": "b", "id": 2}]
    assert store["critical_dates"] == []


def test_delete_lease_skips_missing_child_tables():
    store = {"leases": [{"id": "x"}]}
    assert delete_lease(_FakeSB(store), "x") == 1
    assert store["leases"] == []


def test_delete_leases_no_ids():
    assert delete_leases(_FakeSB({"leases": []}), []) == 0


def test_child_tables_include_extracted_fields():
    assert "extracted_fields" in CHILD_TABLES
    assert "critical_dates" in CHILD_TABLES


if __name__ == "__main__":
    test_delete_leases_removes_children_and_lease()
    test_delete_lease_skips_missing_child_tables()
    test_delete_leases_no_ids()
    test_child_tables_include_extracted_fields()
    print("test_lease_delete.py: all tests passed")
