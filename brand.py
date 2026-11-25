"""Veriterm visual identity for PDFs, emails, and the Streamlit app."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRAND_DIR = ROOT / "brand"
LOGO_PATH = BRAND_DIR / "veriterm-logo.png"
LOGO_DARK_PATH = BRAND_DIR / "veriterm-logo-dark.png"
MARK_PATH = BRAND_DIR / "veriterm-mark.png"

NAVY = "#0B1F3A"
NAVY_MID = "#1B3A5C"
STEEL = "#8A9AAB"
NAVY_LIGHT = "#E8EEF4"
BUTTON = "#1B3A5C"


def email_header_html(subtitle: str) -> str:
    """Navy lockup used at the top of customer emails."""
    return f"""
            <div style="background:{NAVY}; color:#ffffff; padding:28px 24px; text-align:center; border-radius:8px 8px 0 0;">
                <div style="letter-spacing:0.28em; font-size:22px; font-weight:700;">VERITERM</div>
                <div style="letter-spacing:0.18em; font-size:11px; color:{STEEL}; margin-top:8px;">CONTRACT INTELLIGENCE</div>
                <p style="margin:14px 0 0; font-size:16px; font-weight:normal;">{subtitle}</p>
            </div>
    """
