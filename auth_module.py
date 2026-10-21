"""
Authentication Module for LeaseAI
Handles user authentication and role-based access control.
"""
import streamlit as st
from supabase import Client


class AuthManager:
    """Manages authentication and user sessions."""
    
    def __init__(self, supabase_client: Client):
        """
        Initialize the authentication manager.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        
        # Initialize session state
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "user_role" not in st.session_state:
            st.session_state.user_role = None
        if "user_id" not in st.session_state:
            st.session_state.user_id = None
        if "user_email" not in st.session_state:
            st.session_state.user_email = None
        if "user_name" not in st.session_state:
            st.session_state.user_name = None
    
    def login(self, username: str, password: str, totp_code: str = None) -> tuple[bool, str, str, bool]:
        """
        Authenticate user credentials and determine role.
        
        Args:
            username: User's email or username
            password: User's password
            totp_code: Optional 6-digit TOTP code for 2FA
            
        Returns:
            Tuple of (success: bool, role: str, message: str, needs_2fa: bool)
        """
        try:
            # Check admin users table first
            admin_response = self.supabase.table("admin_users").select("*").eq("email", username).execute()
            
            if admin_response.data and len(admin_response.data) > 0:
                admin = admin_response.data[0]
                
                # Simple password check (in production, use proper hashing)
                if admin.get("password") == password:
                    # Check if 2FA is enabled
                    totp_enabled = admin.get("totp_enabled", False)
                    totp_secret = admin.get("totp_secret")
                    
                    if totp_enabled and totp_secret:
                        # 2FA is enabled, need to verify code
                        if totp_code:
                            # Verify TOTP code
                            from two_factor_auth import TwoFactorAuth
                            tfa = TwoFactorAuth(self.supabase)
                            
                            if tfa.verify_token(totp_secret, totp_code):
                                # 2FA verified, complete login
                                st.session_state.authenticated = True
                                st.session_state.user_role = "admin"
                                st.session_state.user_id = admin.get("id")
                                st.session_state.user_email = admin.get("email")
                                st.session_state.user_name = admin.get("name", "Admin")
                                
                                return True, "admin", "Admin login successful", False
                            else:
                                return False, None, "Invalid 2FA code", False
                        else:
                            # Need 2FA code
                            return False, None, "2FA code required", True
                    else:
                        # No 2FA, complete login
                        st.session_state.authenticated = True
                        st.session_state.user_role = "admin"
                        st.session_state.user_id = admin.get("id")
                        st.session_state.user_email = admin.get("email")
                        st.session_state.user_name = admin.get("name", "Admin")
                        
                        return True, "admin", "Admin login successful", False
            
            # Check clients table
            client_response = self.supabase.table("clients").select("*").eq("email", username).execute()
            
            if client_response.data and len(client_response.data) > 0:
                client = client_response.data[0]
                
                # Simple password check (in production, use proper hashing)
                if client.get("password") == password:
                    # Check if 2FA is enabled
                    totp_enabled = client.get("totp_enabled", False)
                    totp_secret = client.get("totp_secret")
                    
                    if totp_enabled and totp_secret:
                        # 2FA is enabled, need to verify code
                        if totp_code:
                            # Verify TOTP code
                            from two_factor_auth import TwoFactorAuth
                            tfa = TwoFactorAuth(self.supabase)
                            
                            if tfa.verify_token(totp_secret, totp_code):
                                # 2FA verified, complete login
                                st.session_state.authenticated = True
                                st.session_state.user_role = "client"
                                st.session_state.user_id = client.get("id")
                                st.session_state.user_email = client.get("email")
                                st.session_state.user_name = client.get("company_name", "Client")
                                
                                return True, "client", "Client login successful", False
                            else:
                                return False, None, "Invalid 2FA code", False
                        else:
                            # Need 2FA code
                            return False, None, "2FA code required", True
                    else:
                        # No 2FA, complete login
                        st.session_state.authenticated = True
                        st.session_state.user_role = "client"
                        st.session_state.user_id = client.get("id")
                        st.session_state.user_email = client.get("email")
                        st.session_state.user_name = client.get("company_name", "Client")
                        
                        return True, "client", "Client login successful", False
            
            return False, None, "Invalid credentials", False
            
        except Exception as e:
            return False, None, f"Login error: {str(e)}", False
    
    def logout(self):
        """Clear authentication session."""
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_name = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return st.session_state.get("authenticated", False)
    
    def get_role(self) -> str:
        """Get current user's role."""
        return st.session_state.get("user_role", None)
    
    def is_admin(self) -> bool:
        """Check if current user is admin."""
        return st.session_state.get("user_role") == "admin"
    
    def is_client(self) -> bool:
        """Check if current user is client."""
        return st.session_state.get("user_role") == "client"
    
    def get_user_id(self) -> int:
        """Get current user's ID."""
        return st.session_state.get("user_id")
    
    def get_user_name(self) -> str:
        """Get current user's display name."""
        return st.session_state.get("user_name", "User")
    
    def render_login_page(self):
        """Render the login form."""
        st.title(f"🔐 {st.session_state.get('app_name', 'LeaseAI')} Login")
        st.markdown("---")
        
        # Check if we need 2FA code
        needs_2fa = st.session_state.get("needs_2fa_verification", False)
        pending_username = st.session_state.get("pending_2fa_username")
        pending_password = st.session_state.get("pending_2fa_password")
        
        if needs_2fa and pending_username and pending_password:
            # Show 2FA verification form
            st.info("🔐 Two-Factor Authentication Required")
            st.markdown(f"Please enter the 6-digit code from your authenticator app for **{pending_username}**")
            
            with st.form("2fa_form"):
                totp_code = st.text_input(
                    "Verification Code",
                    max_chars=6,
                    placeholder="000000"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    submit = st.form_submit_button("Verify & Login", use_container_width=True, type="primary")
                
                with col2:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)
                
                if cancel:
                    # Clear 2FA session state
                    st.session_state.needs_2fa_verification = False
                    st.session_state.pending_2fa_username = None
                    st.session_state.pending_2fa_password = None
                    st.rerun()
                
                if submit:
                    if len(totp_code) == 6:
                        success, role, message, still_needs_2fa = self.login(
                            pending_username, 
                            pending_password, 
                            totp_code
                        )
                        
                        if success:
                            # Clear 2FA session state
                            st.session_state.needs_2fa_verification = False
                            st.session_state.pending_2fa_username = None
                            st.session_state.pending_2fa_password = None
                            
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("⚠️ Please enter a 6-digit code")
        
        else:
            # Show normal login form
            with st.form("login_form"):
                username = st.text_input("Email", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if not username or not password:
                        st.error("Please enter both email and password")
                    else:
                        success, role, message, needs_2fa = self.login(username, password)
                        
                        if needs_2fa:
                            # Store credentials and show 2FA form
                            st.session_state.needs_2fa_verification = True
                            st.session_state.pending_2fa_username = username
                            st.session_state.pending_2fa_password = password
                            st.rerun()
                        elif success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


def require_auth(auth_manager: AuthManager, allowed_roles: list = None):
    """
    Decorator-style function to require authentication.
    
    Args:
        auth_manager: AuthManager instance
        allowed_roles: List of allowed roles (e.g., ["admin", "client"])
    
    Returns:
        True if authenticated and authorized, False otherwise
    """
    if not auth_manager.is_authenticated():
        return False
    
    if allowed_roles:
        current_role = auth_manager.get_role()
        if current_role not in allowed_roles:
            st.error(f"Access denied. Required role: {', '.join(allowed_roles)}")
            return False
    
    return True
