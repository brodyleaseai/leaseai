"""Login should not dump a raw Supabase 401 JSON blob."""

import unittest
from unittest.mock import MagicMock, patch

from auth_module import AuthManager
from config import is_placeholder_secret, read_secret


class PlaceholderTests(unittest.TestCase):
    def test_dummy_keys_are_placeholders(self):
        self.assertTrue(is_placeholder_secret("your-service-role-key-here"))
        self.assertTrue(is_placeholder_secret("your-anon-key-here"))
        self.assertTrue(is_placeholder_secret(""))
        self.assertTrue(is_placeholder_secret(None))

    def test_jwt_like_keys_are_not_placeholders(self):
        self.assertFalse(
            is_placeholder_secret(
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
            )
        )


class ReadSecretTests(unittest.TestCase):
    def test_env_wins_over_default(self):
        with patch.dict("os.environ", {"SUPABASE_SERVICE_KEY": "eyJ-env-key"}, clear=False):
            self.assertEqual(read_secret("SUPABASE_SERVICE_KEY", "your-service-role-key-here"), "eyJ-env-key")


class LoginMessageTests(unittest.TestCase):
    def test_invalid_api_key_is_readable(self):
        class Session(dict):
            def __getattr__(self, name):
                try:
                    return self[name]
                except KeyError as exc:
                    raise AttributeError(name) from exc

            def __setattr__(self, name, value):
                self[name] = value

        client = MagicMock()
        client.table.side_effect = Exception(
            "{'message': 'JSON could not be generated', 'code': 401, "
            "'hint': 'Refer to full message for details', "
            "'details': 'b\\'{\"message\":\"Invalid API key\"}\\''}"
        )
        with patch("auth_module.st") as st_mod:
            st_mod.session_state = Session()
            auth = AuthManager(client)
            ok, role, message, needs_2fa = auth.login("admin@test.com", "secret")
        self.assertFalse(ok)
        self.assertIsNone(role)
        self.assertFalse(needs_2fa)
        self.assertIn("SUPABASE_SERVICE_KEY", message)
        self.assertNotIn("JSON could not be generated", message)


if __name__ == "__main__":
    unittest.main()
