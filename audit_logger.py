"""
LeaseAI - Audit Logging Helper Functions
Phase 5: Security Hardening & Enterprise Readiness

Provides functions to log all sensitive actions in the system for audit trail.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import json
from supabase import Client


class AuditLogger:
    """
    Centralized audit logging for all sensitive actions.
    
    Usage:
        logger = AuditLogger(supabase_client)
        logger.log_action(
            user_id="uuid",
            user_email="user@example.com",
            action_type="LEASE_UPLOAD",
            action_category="DATA",
            resource_type="lease",
            resource_id="lease-uuid",
            action_description="User uploaded new lease document",
            new_values={"filename": "lease.pdf", "pages": 45}
        )
    """
    
    # Action categories
    CATEGORY_AUTH = "AUTH"
    CATEGORY_DATA = "DATA"
    CATEGORY_ADMIN = "ADMIN"
    CATEGORY_EXPORT = "EXPORT"
    CATEGORY_SECURITY = "SECURITY"
    
    # Common action types
    ACTION_USER_LOGIN = "USER_LOGIN"
    ACTION_USER_LOGOUT = "USER_LOGOUT"
    ACTION_USER_REGISTER = "USER_REGISTER"
    ACTION_PASSWORD_CHANGE = "PASSWORD_CHANGE"
    ACTION_2FA_ENABLE = "2FA_ENABLE"
    ACTION_2FA_DISABLE = "2FA_DISABLE"
    
    ACTION_LEASE_UPLOAD = "LEASE_UPLOAD"
    ACTION_LEASE_DELETE = "LEASE_DELETE"
    ACTION_LEASE_UPDATE = "LEASE_UPDATE"
    ACTION_LEASE_VIEW = "LEASE_VIEW"
    
    ACTION_DATA_EXPORT_CSV = "DATA_EXPORT_CSV"
    ACTION_DATA_EXPORT_PDF = "DATA_EXPORT_PDF"
    ACTION_DATA_EXPORT_EXCEL = "DATA_EXPORT_EXCEL"
    ACTION_DATA_EXPORT_YARDI = "DATA_EXPORT_YARDI"
    ACTION_DATA_EXPORT_MRI = "DATA_EXPORT_MRI"
    
    ACTION_USER_ROLE_CHANGE = "USER_ROLE_CHANGE"
    ACTION_USER_DELETE = "USER_DELETE"
    ACTION_SETTINGS_CHANGE = "SETTINGS_CHANGE"
    
    ACTION_CAM_RECONCILIATION = "CAM_RECONCILIATION"
    ACTION_CAM_DISPUTE = "CAM_DISPUTE"
    
    ACTION_HEALTH_REPORT_GENERATED = "HEALTH_REPORT_GENERATED"
    ACTION_ANOMALY_DETECTED = "ANOMALY_DETECTED"
    
    def __init__(self, supabase_client: Client):
        """Initialize audit logger with Supabase client"""
        self.sb = supabase_client
    
    def log_action(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        action_type: str,
        action_category: str,
        action_description: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
        user_role: Optional[str] = None
    ) -> Optional[str]:
        """
        Log an audit event
        
        Args:
            user_id: UUID of the user performing the action
            user_email: Email of the user
            action_type: Type of action (use ACTION_* constants)
            action_category: Category (use CATEGORY_* constants)
            action_description: Human-readable description
            resource_type: Type of resource affected (e.g., "lease", "user")
            resource_id: UUID of the resource
            resource_name: Human-readable name of the resource
            old_values: Previous state (for updates/deletes)
            new_values: New state (for creates/updates)
            ip_address: IP address of the user
            user_agent: User agent string
            session_id: Session identifier
            status: SUCCESS, FAILED, or PARTIAL
            error_message: Error details if status is FAILED
            metadata: Additional context-specific data
            user_role: Role of the user at time of action
            
        Returns:
            Audit log entry ID (UUID) or None if logging failed
        """
        
        try:
            audit_entry = {
                "user_id": user_id,
                "user_email": user_email,
                "user_role": user_role,
                "action_type": action_type,
                "action_category": action_category,
                "action_description": action_description,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "old_values": json.dumps(old_values) if old_values else None,
                "new_values": json.dumps(new_values) if new_values else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
                "status": status,
                "error_message": error_message,
                "metadata": json.dumps(metadata) if metadata else None,
                "performed_at": datetime.now().isoformat()
            }
            
            response = self.sb.table("audit_log").insert(audit_entry).execute()
            
            if response.data:
                return response.data[0].get("id")
            
            return None
        
        except Exception as e:
            # Critical: audit logging failure should not break the application
            # Log to stderr or monitoring service
            print(f"⚠️ Audit logging failed: {str(e)}")
            return None
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Log a security event (failed login, suspicious activity, etc.)
        
        Args:
            event_type: Type of security event
            severity: LOW, MEDIUM, HIGH, or CRITICAL
            description: Description of the event
            user_id: User ID (if known)
            user_email: User email (if known)
            ip_address: IP address
            user_agent: User agent
            details: Additional event details
            
        Returns:
            Security event ID or None if logging failed
        """
        
        try:
            event_entry = {
                "event_type": event_type,
                "severity": severity,
                "description": description,
                "user_id": user_id,
                "user_email": user_email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": json.dumps(details) if details else None,
                "occurred_at": datetime.now().isoformat()
            }
            
            response = self.sb.table("security_events").insert(event_entry).execute()
            
            if response.data:
                return response.data[0].get("id")
            
            return None
        
        except Exception as e:
            print(f"⚠️ Security event logging failed: {str(e)}")
            return None
    
    def get_recent_audit_logs(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Retrieve recent audit logs with optional filtering
        
        Args:
            user_id: Filter by user ID
            action_type: Filter by action type
            resource_type: Filter by resource type
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        
        try:
            query = self.sb.table("audit_log").select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            if action_type:
                query = query.eq("action_type", action_type)
            
            if resource_type:
                query = query.eq("resource_type", resource_type)
            
            query = query.order("performed_at", desc=True).limit(limit)
            
            response = query.execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"⚠️ Failed to retrieve audit logs: {str(e)}")
            return []
    
    def get_user_audit_summary(self, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get audit summary for a user (action counts by category)
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of action categories with counts
        """
        
        try:
            response = self.sb.rpc(
                "get_user_audit_summary",
                {"p_user_id": user_id, "p_days": days}
            ).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"⚠️ Failed to get audit summary: {str(e)}")
            return []
    
    def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get complete audit history for a specific resource
        
        Args:
            resource_type: Type of resource (e.g., "lease")
            resource_id: UUID of the resource
            limit: Maximum number of records
            
        Returns:
            List of audit log entries for the resource
        """
        
        try:
            response = self.sb.rpc(
                "get_resource_audit_history",
                {
                    "p_resource_type": resource_type,
                    "p_resource_id": resource_id,
                    "p_limit": limit
                }
            ).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"⚠️ Failed to get resource history: {str(e)}")
            return []
    
    def get_security_events(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get security events with optional filtering
        
        Args:
            severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
            resolved: Filter by resolution status
            limit: Maximum number of records
            
        Returns:
            List of security events
        """
        
        try:
            query = self.sb.table("security_events").select("*")
            
            if severity:
                query = query.eq("severity", severity)
            
            if resolved is not None:
                query = query.eq("resolved", resolved)
            
            query = query.order("occurred_at", desc=True).limit(limit)
            
            response = query.execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"⚠️ Failed to retrieve security events: {str(e)}")
            return []


# Convenience functions for common audit actions

def log_lease_upload(
    supabase_client: Client,
    user_id: str,
    user_email: str,
    lease_id: str,
    filename: str,
    pages: int,
    property_address: str = None
):
    """Log a lease upload action"""
    logger = AuditLogger(supabase_client)
    logger.log_action(
        user_id=user_id,
        user_email=user_email,
        action_type=AuditLogger.ACTION_LEASE_UPLOAD,
        action_category=AuditLogger.CATEGORY_DATA,
        action_description=f"Uploaded lease document: {filename}",
        resource_type="lease",
        resource_id=lease_id,
        resource_name=property_address or filename,
        new_values={
            "filename": filename,
            "pages": pages,
            "property_address": property_address
        }
    )


def log_data_export(
    supabase_client: Client,
    user_id: str,
    user_email: str,
    export_type: str,  # CSV, PDF, EXCEL, YARDI, MRI
    lease_id: str = None,
    lease_count: int = 1,
    filename: str = None
):
    """Log a data export action"""
    logger = AuditLogger(supabase_client)
    
    action_types = {
        "CSV": AuditLogger.ACTION_DATA_EXPORT_CSV,
        "PDF": AuditLogger.ACTION_DATA_EXPORT_PDF,
        "EXCEL": AuditLogger.ACTION_DATA_EXPORT_EXCEL,
        "YARDI": AuditLogger.ACTION_DATA_EXPORT_YARDI,
        "MRI": AuditLogger.ACTION_DATA_EXPORT_MRI
    }
    
    logger.log_action(
        user_id=user_id,
        user_email=user_email,
        action_type=action_types.get(export_type, AuditLogger.ACTION_DATA_EXPORT_CSV),
        action_category=AuditLogger.CATEGORY_EXPORT,
        action_description=f"Exported {lease_count} lease(s) as {export_type}",
        resource_type="lease",
        resource_id=lease_id,
        resource_name=filename,
        new_values={
            "export_type": export_type,
            "lease_count": lease_count,
            "filename": filename
        }
    )


def log_lease_delete(
    supabase_client: Client,
    user_id: str,
    user_email: str,
    lease_id: str,
    property_address: str,
    tenant_name: str = None
):
    """Log a lease deletion action"""
    logger = AuditLogger(supabase_client)
    logger.log_action(
        user_id=user_id,
        user_email=user_email,
        action_type=AuditLogger.ACTION_LEASE_DELETE,
        action_category=AuditLogger.CATEGORY_DATA,
        action_description=f"Deleted lease: {property_address}",
        resource_type="lease",
        resource_id=lease_id,
        resource_name=property_address,
        old_values={
            "property_address": property_address,
            "tenant_name": tenant_name
        }
    )


def log_settings_change(
    supabase_client: Client,
    user_id: str,
    user_email: str,
    setting_name: str,
    old_value: Any,
    new_value: Any
):
    """Log a settings change"""
    logger = AuditLogger(supabase_client)
    logger.log_action(
        user_id=user_id,
        user_email=user_email,
        action_type=AuditLogger.ACTION_SETTINGS_CHANGE,
        action_category=AuditLogger.CATEGORY_ADMIN,
        action_description=f"Changed setting: {setting_name}",
        resource_type="setting",
        resource_name=setting_name,
        old_values={"value": old_value},
        new_values={"value": new_value}
    )


def log_failed_login(
    supabase_client: Client,
    email: str,
    ip_address: str = None,
    reason: str = "Invalid credentials"
):
    """Log a failed login attempt"""
    logger = AuditLogger(supabase_client)
    logger.log_security_event(
        event_type="FAILED_LOGIN",
        severity="MEDIUM",
        description=f"Failed login attempt for {email}: {reason}",
        user_email=email,
        ip_address=ip_address,
        details={"reason": reason}
    )
