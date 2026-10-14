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
    
    def login(self, username: str, password: str) -> tuple[bool, str, str]:
        """
        Authenticate user credentials and determine role.
        
        Args:
            username: User's email or username
            password: User's password
        
        Returns:
            Tuple of (success: bool, role: str, message: str)
        """
        try:
            # Check admin users table first
            admin_response = self.supabase.table("admin_users").select("*").eq("email", username).execute()
            
            if admin_response.data and len(admin_response.data) > 0:
                admin = admin_response.data[0]
                
                # Simple password check (in production, use proper hashing)
                if admin.get("password") == password:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "admin"
                    st.session_state.user_id = admin.get("id")
                    st.session_state.user_email = admin.get("email")
                    st.session_state.user_name = admin.get("name", "Admin")
                    
                    return True, "admin", "Admin login successful"
            
            # Check clients table
            client_response = self.supabase.table("clients").select("*").eq("email", username).execute()
            
            if client_response.data and len(client_response.data) > 0:
                client = client_response.data[0]
                
                # Simple password check (in production, use proper hashing)
                if client.get("password") == password:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "client"
                    st.session_state.user_id = client.get("id")
                    st.session_state.user_email = client.get("email")
                    st.session_state.user_name = client.get("company_name", "Client")
                    
                    return True, "client", "Client login successful"
            
            return False, None, "Invalid credentials"
            
        except Exception as e:
            return False, None, f"Login error: {str(e)}"
    
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
        
        with st.form("login_form"):
            username = st.text_input("Email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both email and password")
                else:
                    success, role, message = self.login(username, password)
                    
                    if success:
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
