"""Regression tests for Amendment Graph upload remaining available per-lease."""

import unittest
from pathlib import Path
from unittest.mock import patch

from amendment_graph_helpers import clause_types_from_history, html_text, lease_option_label


PAGE_PATH = Path(__file__).parent / "pages" / "3_🔗_Amendment_Graph.py"

LEASE_EMPTY = {
    "id": "lease-empty",
    "property_address": "100 New Street",
    "tenant_name": "Fresh Tenant LLC",
}
LEASE_HISTORY = {
    "id": "lease-history",
    "property_address": "200 Old Street",
    "tenant_name": "Established Tenant Inc",
}
LEASE_ROUTE2 = {
    "id": "lease-route2",
    "property_address": "Route 2",
    "tenant_name": "Route 2 Tenant",
}


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._rows = [row for row in self._rows if row.get(column) == value]
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        return FakeResponse(self._rows)


class FakeSupabase:
    def __init__(self, tables, rpcs=None, rpc_error=None, explode_history_star=False):
        self._tables = tables
        self._rpcs = rpcs or {}
        self._rpc_error = rpc_error
        self._explode_history_star = explode_history_star

    def table(self, name):
        if name == "lease_clause_history" and self._explode_history_star:
            return ExplodingStarQuery(self._tables.get(name, []))
        return FakeQuery(self._tables.get(name, []))

    def rpc(self, name, params):
        if self._rpc_error:
            raise RuntimeError(self._rpc_error)
        rows = list(self._rpcs.get(name, []))
        lease_id = params.get("p_lease_id")
        if lease_id:
            rows = [row for row in rows if row.get("lease_id") == lease_id]
        return FakeQuery(rows)


class ExplodingStarQuery(FakeQuery):
    def select(self, *args, **kwargs):
        cols = args[0] if args else "*"
        if cols == "*":
            raise RuntimeError("Route 2 clause history payload failed")
        return super().select(*args, **kwargs)


def _client_for(leases, history_rows=None, amendments=None):
    return FakeSupabase(
        tables={
            "leases": leases,
            "lease_clause_history": history_rows or [],
            "amendment_clauses": [],
        },
        rpcs={"get_amendment_chain": amendments or []},
    )


class HelperTests(unittest.TestCase):
    def test_html_text_survives_braces_and_markup(self):
        rendered = html_text("Rent is {$8,550.08} <script>alert(1)</script>")
        self.assertIn("&#123;", rendered)
        self.assertIn("&#125;", rendered)
        self.assertNotIn("<script>", rendered)
        # Safe to interpolate into an f-string after escaping.
        self.assertEqual(f"<div>{rendered}</div>", f"<div>{rendered}</div>")

    def test_html_text_empty_is_placeholder(self):
        self.assertEqual(html_text(None), "N/A")
        self.assertEqual(html_text("   "), "N/A")

    def test_clause_types_from_history_dedupes(self):
        rows = [
            {"clause_type": "Base Rent"},
            {"clause_type": "Base Rent"},
            {"clause_type": "CAM Charges"},
            {"clause_type": None},
        ]
        self.assertEqual(clause_types_from_history(rows), ["Base Rent", "CAM Charges"])
        self.assertEqual(clause_types_from_history([]), [])

    def test_lease_option_label_keeps_duplicates_distinct(self):
        a = {"id": "aaa11111-1", "property_address": "Route 2", "tenant_name": "Same"}
        b = {"id": "bbb22222-2", "property_address": "Route 2", "tenant_name": "Same"}
        self.assertNotEqual(lease_option_label(a), lease_option_label(b))


class PageSourceTests(unittest.TestCase):
    def test_query_engine_empty_state_does_not_stop_the_page(self):
        source = PAGE_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("st.stop()"), 1)
        self.assertIn('render_amendment_upload(selected_lease_id, "tab")', source)
        self.assertNotIn('render_amendment_upload(selected_lease_id, "sidebar")', source)
        tab3_idx = source.find("# TAB 3:")
        tab4_idx = source.find("# TAB 4:")
        self.assertGreater(tab3_idx, 0)
        self.assertGreater(tab4_idx, 0)
        self.assertLess(tab4_idx, tab3_idx)
        self.assertNotIn("st.stop()", source[tab3_idx:])

    def test_old_st_stop_pattern_hides_the_uploader(self):
        """Reproduce the previous Query Engine empty-state bug in isolation."""
        from streamlit.testing.v1 import AppTest

        script = (
            "import streamlit as st\n"
            "tab1, tab2 = st.tabs(['Query Engine', 'Upload Amendment'])\n"
            "with tab1:\n"
            "    clause_types = []\n"
            "    if not clause_types:\n"
            "        st.warning('No clause history available. Upload amendments first.')\n"
            "        st.stop()\n"
            "with tab2:\n"
            "    st.file_uploader('Upload Amendment PDF', type=['pdf'])\n"
        )
        app = AppTest.from_string(script, default_timeout=10)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 0)


class AppTests(unittest.TestCase):
    def _run_page(self, client):
        from streamlit.testing.v1 import AppTest

        patcher = patch("supabase.create_client", return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)
        app = AppTest.from_file(str(PAGE_PATH), default_timeout=15)
        app.run()
        return app

    def test_empty_clause_history_still_shows_amendment_uploader(self):
        """The just-processed lease case: no clause history yet."""
        app = self._run_page(_client_for([LEASE_EMPTY]))
        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 1)
        self.assertEqual(app.file_uploader[0].label, "Upload Amendment PDF")
        self.assertTrue(any("Resolution Abstract" in tab.label for tab in app.tabs))
        self.assertGreaterEqual(len(app.download_button), 1)

    def test_history_with_braces_does_not_kill_uploader(self):
        """A lease whose clause text contains `{` used to crash tab 2 via f-string."""
        history = [
            {
                "lease_id": "lease-history",
                "clause_type": "Base Rent",
                "version_number": 0,
                "is_current": True,
                "effective_from": "2024-01-01",
                "effective_to": None,
                "source_document_type": "BASE_LEASE",
                "modification_type": None,
                "clause_value": "Monthly rent of {$8,550.08} per {Section 4}",
            }
        ]
        app = self._run_page(_client_for([LEASE_HISTORY], history_rows=history))
        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 1)

    def test_switching_to_empty_history_lease_keeps_uploader(self):
        history = [
            {
                "lease_id": "lease-history",
                "clause_type": "Base Rent",
                "version_number": 0,
                "is_current": True,
                "effective_from": "2024-01-01",
                "effective_to": None,
                "source_document_type": "BASE_LEASE",
                "modification_type": None,
                "clause_value": "Year 1 rent",
            }
        ]
        client = _client_for([LEASE_HISTORY, LEASE_EMPTY], history_rows=history)
        app = self._run_page(client)
        self.assertFalse(app.exception)
        empty_label = lease_option_label(LEASE_EMPTY)
        lease_box = next(box for box in app.selectbox if box.label == "Choose a lease:")
        lease_box.set_value(empty_label)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 1)

    def test_route2_chain_rpc_failure_keeps_uploader(self):
        client = FakeSupabase(
            tables={
                "leases": [LEASE_ROUTE2],
                "lease_clause_history": [],
                "amendment_clauses": [],
            },
            rpc_error="Route 2 amendment chain failed",
        )
        app = self._run_page(client)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 1)
        self.assertTrue(any(box.label == "Choose a lease:" for box in app.selectbox))

    def test_route2_history_star_query_failure_keeps_uploader(self):
        history = [
            {
                "lease_id": "lease-route2",
                "clause_type": "Base Rent",
                "version_number": 0,
                "is_current": True,
                "effective_from": "2024-01-01",
                "effective_to": None,
                "source_document_type": "BASE_LEASE",
                "modification_type": None,
                "clause_value": "Year 1 rent",
            }
        ]
        client = FakeSupabase(
            tables={
                "leases": [LEASE_ROUTE2],
                "lease_clause_history": history,
                "amendment_clauses": [],
            },
            explode_history_star=True,
        )
        app = self._run_page(client)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.file_uploader), 1)


if __name__ == "__main__":
    unittest.main()
