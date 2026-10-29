import os
from unittest.mock import patch

import openai_key


def test_get_openai_api_key_uses_env_when_secrets_missing():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-from-env"}, clear=False):
        assert openai_key.get_openai_api_key() == "sk-test-from-env"


def test_get_openai_api_key_survives_missing_streamlit_secrets():
    class Boom:
        def __getitem__(self, key):
            raise RuntimeError("No secrets found. Valid paths for a secrets.toml file")

    fake_st = type("st", (), {"secrets": Boom()})
    fake_config = type("config", (), {"OPENAI_API_KEY": "sk-from-config"})
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        with patch.dict("sys.modules", {"streamlit": fake_st, "config": fake_config}):
            assert openai_key.get_openai_api_key() == "sk-from-config"


def test_get_openai_api_key_returns_empty_for_placeholders():
    fake_config = type("config", (), {"OPENAI_API_KEY": "your-openai-key-here"})
    with patch.dict(os.environ, {"OPENAI_API_KEY": "your-openai-key-here"}, clear=False):
        with patch.dict("sys.modules", {"config": fake_config}):
            assert openai_key.get_openai_api_key() == ""


if __name__ == "__main__":
    test_get_openai_api_key_uses_env_when_secrets_missing()
    test_get_openai_api_key_survives_missing_streamlit_secrets()
    test_get_openai_api_key_returns_empty_for_placeholders()
    print("test_openai_key_fallback.py: all tests passed")
