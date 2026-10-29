"""Resolve the OpenAI key without requiring a Streamlit secrets.toml file."""

from __future__ import annotations

import os

_PLACEHOLDERS = {
    "",
    "your-openai-key-here",
    "your-actual-openai-key-here",
}


def get_openai_api_key() -> str:
    """Use .env / config.py first; only read st.secrets if that file exists.

    `st.secrets.get(...)` still loads secrets.toml and raises
    StreamlitSecretNotFoundError when the file is missing. Lease upload already
    works from config.OPENAI_API_KEY; CAM extraction should too.
    """
    env = (os.getenv("OPENAI_API_KEY") or "").strip()
    if env and env not in _PLACEHOLDERS:
        return env
    try:
        import config
        text = (getattr(config, "OPENAI_API_KEY", "") or "").strip()
        if text and text not in _PLACEHOLDERS:
            return text
    except Exception:
        pass
    try:
        import streamlit as st
        text = str(st.secrets["OPENAI_API_KEY"]).strip()
        if text and text not in _PLACEHOLDERS:
            return text
    except Exception:
        pass
    return ""
