"""
Two-Factor Authentication Module for LeaseAI
Implements TOTP-based 2FA using pyotp library
"""

import streamlit as st
import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from typing import Optional, Tuple
from supabase import Client


class TwoFactorAuth:
    """Handles TOTP-based two-factor authentication."""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize 2FA manager.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            Base32-encoded secret key
        """
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str, issuer: str = "LeaseAI") -> str:
        """
        Generate QR code for TOTP setup.
        
        Args:
            user_email: User's email address
            secret: TOTP secret key
            issuer: Application name
            
        Returns:
            Base64-encoded PNG image
        """
        # Create provisioning URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user_email, issuer_name=issuer)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret: str, token: str) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            secret: User's TOTP secret
            token: 6-digit token from authenticator app
            
        Returns:
            True if valid, False otherwise
        """
        if not secret or token is None:
            return False

        cleaned = "".join(ch for ch in str(token) if ch.isdigit())
        if len(cleaned) != 6:
            return False

        totp = pyotp.TOTP(secret)
        # Window of 2 allows +/- 60 seconds for phone vs PC clock drift
        return totp.verify(cleaned, valid_window=2)
    
    def enable_2fa(self, user_id: str, user_email: str, secret: str) -> Tuple[bool, str]:
        """
        Enable 2FA for a user.
        
        Args:
            user_id: User's ID
            user_email: User's email
            secret: TOTP secret key
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user is admin or client
            admin_response = self.supabase.table("admin_users").select("id").eq("id", user_id).execute()
            
            if admin_response.data:
                # Update admin user
                self.supabase.table("admin_users").update({
                    "totp_secret": secret,
                    "totp_enabled": True,
                    "totp_enabled_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
            else:
                # Update client user
                self.supabase.table("clients").update({
                    "totp_secret": secret,
                    "totp_enabled": True,
                    "totp_enabled_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
            
            # Log 2FA enable in audit log
            from audit_logger import AuditLogger
            logger = AuditLogger(self.supabase)
            logger.log_action(
                user_id=user_id,
                user_email=user_email,
                action_type="2FA_ENABLE",
                action_category="SECURITY",
                action_description="Two-factor authentication enabled"
            )
            
            return True, "2FA enabled successfully"
        
        except Exception as e:
            return False, f"Failed to enable 2FA: {str(e)}"
    
    def disable_2fa(self, user_id: str, user_email: str) -> Tuple[bool, str]:
        """
        Disable 2FA for a user.
        
        Args:
            user_id: User's ID
            user_email: User's email
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user is admin or client
            admin_response = self.supabase.table("admin_users").select("id").eq("id", user_id).execute()
            
            if admin_response.data:
                # Update admin user
                self.supabase.table("admin_users").update({
                    "totp_secret": None,
                    "totp_enabled": False,
                    "totp_disabled_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
            else:
                # Update client user
                self.supabase.table("clients").update({
                    "totp_secret": None,
                    "totp_enabled": False,
                    "totp_disabled_at": datetime.utcnow().isoformat()
                }).eq("id", user_id).execute()
            
            # Log 2FA disable in audit log
            from audit_logger import AuditLogger
            logger = AuditLogger(self.supabase)
            logger.log_action(
                user_id=user_id,
                user_email=user_email,
                action_type="2FA_DISABLE",
                action_category="SECURITY",
                action_description="Two-factor authentication disabled"
            )
            
            return True, "2FA disabled successfully"
        
        except Exception as e:
            return False, f"Failed to disable 2FA: {str(e)}"
    
    def get_user_2fa_status(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user has 2FA enabled.
        
        Args:
            user_id: User's ID
            
        Returns:
            Tuple of (enabled: bool, secret: Optional[str])
        """
        try:
            # Check admin users first
            admin_response = self.supabase.table("admin_users").select("totp_enabled, totp_secret").eq("id", user_id).execute()
            
            if admin_response.data:
                user = admin_response.data[0]
                return user.get("totp_enabled", False), user.get("totp_secret")
            
            # Check clients
            client_response = self.supabase.table("clients").select("totp_enabled, totp_secret").eq("id", user_id).execute()
            
            if client_response.data:
                user = client_response.data[0]
                return user.get("totp_enabled", False), user.get("totp_secret")
            
            return False, None
        
        except:
            return False, None
    
    def require_2fa_for_admins(self) -> bool:
        """
        Check if all admin users have 2FA enabled.
        
        Returns:
            True if all admins have 2FA, False otherwise
        """
        try:
            response = self.supabase.table("admin_users").select("id, email, totp_enabled").execute()
            
            if not response.data:
                return True  # No admins, requirement met
            
            admins_without_2fa = [
                admin for admin in response.data 
                if not admin.get("totp_enabled", False)
            ]
            
            return len(admins_without_2fa) == 0
        
        except:
            return False
    
    def get_admins_without_2fa(self) -> list:
        """
        Get list of admin users without 2FA enabled.
        
        Returns:
            List of admin user dictionaries
        """
        try:
            response = self.supabase.table("admin_users").select("id, email, name, totp_enabled").execute()
            
            if not response.data:
                return []
            
            return [
                admin for admin in response.data 
                if not admin.get("totp_enabled", False)
            ]
        
        except:
            return []


def render_2fa_setup_page(supabase_client: Client, user_id: str, user_email: str):
    """
    Render 2FA setup page for users.
    
    Args:
        supabase_client: Supabase client instance
        user_id: Current user's ID
        user_email: Current user's email
    """
    st.title("🔐 Two-Factor Authentication Setup")
    
    tfa = TwoFactorAuth(supabase_client)
    
    # Check current 2FA status
    is_enabled, current_secret = tfa.get_user_2fa_status(user_id)
    
    if is_enabled:
        st.success("✅ Two-factor authentication is **ENABLED** on your account")
        st.markdown("---")
        
        st.markdown("""
        ### 🔒 Your Account is Protected
        
        You will be prompted for a 6-digit code from your authenticator app each time you log in.
        
        **Recommended Authenticator Apps:**
        - Google Authenticator (iOS/Android)
        - Microsoft Authenticator (iOS/Android)
        - Authy (iOS/Android/Desktop)
        - 1Password (with TOTP support)
        """)
        
        st.markdown("---")
        
        # Disable 2FA option
        st.warning("⚠️ **Disable Two-Factor Authentication**")
        st.markdown("Disabling 2FA will make your account less secure.")
        
        disable_confirm = st.checkbox("I understand the security risks of disabling 2FA")
        
        if disable_confirm:
            if st.button("🔓 Disable 2FA", type="secondary"):
                success, message = tfa.disable_2fa(user_id, user_email)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    else:
        st.warning("⚠️ Two-factor authentication is **NOT ENABLED** on your account")
        
        st.markdown("""
        ### Why Enable 2FA?
        
        Two-factor authentication adds an extra layer of security to your account:
        - 🔒 Protects against password breaches
        - 🛡️ Prevents unauthorized access
        - ✅ Required for admin accounts
        - 📱 Works with popular authenticator apps
        
        ### How It Works
        
        1. Scan the QR code with your authenticator app
        2. Enter the 6-digit code to verify setup
        3. You'll be prompted for this code each time you log in
        """)
        
        st.markdown("---")
        
        if st.button("🔐 Enable Two-Factor Authentication", type="primary"):
            st.session_state.show_2fa_setup = True
            st.rerun()
        
        # Show setup flow if button clicked
        if st.session_state.get("show_2fa_setup", False):
            st.markdown("---")
            st.subheader("📱 Step 1: Scan QR Code")
            
            # Generate new secret if not in session
            if "2fa_secret" not in st.session_state:
                st.session_state["2fa_secret"] = tfa.generate_secret()
            
            secret = st.session_state["2fa_secret"]
            
            # Generate and display QR code
            qr_code = tfa.generate_qr_code(user_email, secret)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown(f'<img src="{qr_code}" width="300">', unsafe_allow_html=True)
            
            st.markdown("**Scan this QR code with your authenticator app:**")
            st.markdown("- Google Authenticator")
            st.markdown("- Microsoft Authenticator")
            st.markdown("- Authy")
            st.markdown("- 1Password")
            
            # Manual entry option
            with st.expander("Can't scan? Enter manually"):
                st.code(secret)
                st.caption("Enter this secret key manually in your authenticator app")
            
            st.markdown("---")
            st.subheader("✅ Step 2: Verify Setup")
            
            verification_code = st.text_input(
                "Enter 6-digit code from your authenticator app",
                max_chars=6,
                placeholder="000000"
            )
            st.caption("Use the current code. If it fails, wait for the next code and check that your iPhone and PC clocks are set automatically.")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("Verify and Enable 2FA", type="primary", use_container_width=True):
                    if tfa.verify_token(secret, verification_code):
                        success, message = tfa.enable_2fa(user_id, user_email, secret)
                        if success:
                            st.success("✅ 2FA enabled successfully!")
                            # Clear session state
                            del st.session_state["2fa_secret"]
                            del st.session_state["show_2fa_setup"]
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Invalid code. Wait for a fresh 6-digit code, confirm iPhone Date & Time is set automatically, then try again.")
            
            with col_b:
                if st.button("Cancel", use_container_width=True):
                    del st.session_state["2fa_secret"]
                    del st.session_state["show_2fa_setup"]
                    st.rerun()


def verify_2fa_login(supabase_client: Client, user_id: str, user_email: str) -> bool:
    """
    Prompt for 2FA verification during login.
    
    Args:
        supabase_client: Supabase client instance
        user_id: User's ID
        user_email: User's email
        
    Returns:
        True if verified, False otherwise
    """
    tfa = TwoFactorAuth(supabase_client)
    
    is_enabled, secret = tfa.get_user_2fa_status(user_id)
    
    if not is_enabled:
        return True  # 2FA not enabled, allow login
    
    st.markdown("### 🔐 Two-Factor Authentication Required")
    st.markdown(f"Please enter the 6-digit code from your authenticator app.")
    
    code = st.text_input(
        "Verification Code",
        max_chars=6,
        placeholder="000000",
        key="2fa_verification_code"
    )
    
    if st.button("Verify", type="primary"):
        if len(code) == 6:
            if tfa.verify_token(secret, code):
                return True
            else:
                st.error("❌ Invalid verification code")
                return False
        else:
            st.warning("⚠️ Please enter a 6-digit code")
            return False
    
    return False
