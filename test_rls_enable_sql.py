"""Guard the public-schema RLS script against reopening anon access."""

import re
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parent / "database_security_enable_rls_all_public.sql"
PERMISSIONS_FIX = Path(__file__).parent / "fix_amendment_permissions.sql"


class EnableRlsScriptTests(unittest.TestCase):
    def test_script_enables_rls_on_all_public_tables(self):
        sql = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ENABLE ROW LEVEL SECURITY", sql)
        self.assertIn("relkind = 'r'", sql)
        self.assertIn("nspname = 'public'", sql)
        self.assertIn("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, PUBLIC", sql)
        self.assertIn("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, PUBLIC", sql)
        self.assertIn("service_role", sql)
        self.assertNotRegex(
            sql,
            re.compile(r"^GRANT ALL ON .* TO anon", re.MULTILINE),
        )

    def test_amendment_permissions_no_longer_grant_anon(self):
        sql = PERMISSIONS_FIX.read_text(encoding="utf-8")
        self.assertNotIn("TO anon,", sql)
        self.assertNotIn("TO anon ", sql)
        self.assertIn("service_role", sql)


if __name__ == "__main__":
    unittest.main()
