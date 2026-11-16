"""
LeaseAI Configuration
Centralized configuration for environment variables and API keys.

SECURITY: Never commit real API keys to git or share them in chat!
Update the placeholder values below with your actual keys locally.
"""
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, will use system environment variables only
    pass

_PLACEHOLDER_SECRETS = {
    "",
    "your-anon-key-here",
    "your-service-role-key-here",
    "your-openai-key-here",
    "your-sendgrid-key-here",
    "sk_test_your-stripe-key-here",
    "pk_test_your-stripe-key-here",
    "whsec_your-webhook-secret-here",
}


def is_placeholder_secret(value) -> bool:
    """True when a config value is missing or still the committed dummy."""
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lower = text.lower()
    if lower in _PLACEHOLDER_SECRETS:
        return True
    if lower.startswith("your-") and lower.endswith("-here"):
        return True
    return False


def _streamlit_secret(name: str):
    """Read Streamlit secrets without crashing when secrets.toml is absent."""
    try:
        import streamlit as st
        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return None
        try:
            value = secrets[name]
        except Exception:
            try:
                value = secrets.get(name)
            except Exception:
                return None
        return value
    except Exception:
        return None


def read_secret(name: str, default: str = "") -> str:
    """Prefer a real env/.env value, then Streamlit secrets, then default."""
    env_val = os.getenv(name)
    if env_val is not None and not is_placeholder_secret(env_val):
        return env_val
    file_val = _streamlit_secret(name)
    if file_val is not None and not is_placeholder_secret(file_val):
        return str(file_val).strip()
    if env_val is not None:
        return env_val
    return default


# Supabase Configuration
SUPABASE_URL = read_secret("SUPABASE_URL", "https://nttwaqptwfwchedsqqem.supabase.co")
SUPABASE_KEY = read_secret("SUPABASE_KEY", "your-anon-key-here")  # Replace with your actual anon key
SUPABASE_SERVICE_KEY = read_secret("SUPABASE_SERVICE_KEY", "your-service-role-key-here")  # Replace with your actual service role key

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")

# SendGrid Configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "your-sendgrid-key-here")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "brody@kitschco.com")
SENDER_EMAIL = "brody@kitschco.com"  # Deprecated, use SENDGRID_FROM_EMAIL
SENDER_NAME = "Brody - LeaseAI"

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_your-stripe-key-here")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_your-stripe-key-here")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_your-webhook-secret-here")

# Application Configuration
APP_NAME = "LeaseAI"
COMPANY_NAME = "KitschCo"
COMPANY_LOCATION = "Vancouver, BC"
APP_URL = os.getenv("APP_URL", "https://leaseai.streamlit.app")  # Update with your actual deployed URL
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
EXTRACTION_TIMEOUT_SECONDS = int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "300"))
LEASEAI_ENV = os.getenv("LEASEAI_ENV", "development")

# AWS Configuration (for Textract OCR)
# Optional: Leave empty to use Tesseract fallback or AWS CLI default credentials
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)  # Set via environment variable or AWS CLI
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)  # Set via environment variable or AWS CLI
