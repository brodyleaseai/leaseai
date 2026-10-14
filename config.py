"""
LeaseAI Configuration
Centralized configuration for environment variables and API keys.

SECURITY: Never commit real API keys to git or share them in chat!
Update the placeholder values below with your actual keys locally.
"""
import os

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nttwaqptwfwchedsqqem.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key-here")  # Replace with your actual anon key
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "your-service-role-key-here")  # Replace with your actual service role key

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

# AWS Configuration (for Textract OCR)
# Optional: Leave empty to use Tesseract fallback or AWS CLI default credentials
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)  # Set via environment variable or AWS CLI
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)  # Set via environment variable or AWS CLI
