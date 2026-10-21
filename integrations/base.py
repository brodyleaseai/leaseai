"""
LeaseAI - Integration Framework
Phase 7: Native API Integrations

Base classes and utilities for third-party API integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json


class IntegrationStatus(Enum):
    """Integration sync status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class IntegrationType(Enum):
    """Supported integration types"""
    YARDI_VOYAGER = "yardi_voyager"
    MRI_SOFTWARE = "mri_software"
    QUICKBOOKS = "quickbooks"
    DOCUSIGN = "docusign"
    SLACK = "slack"
    TEAMS = "teams"


class IntegrationError(Exception):
    """Base exception for integration errors"""
    pass


class AuthenticationError(IntegrationError):
    """Raised when authentication fails"""
    pass


class SyncError(IntegrationError):
    """Raised when data sync fails"""
    pass


class BaseIntegration(ABC):
    """
    Abstract base class for all third-party integrations
    
    Provides common functionality:
    - Authentication management
    - Error handling
    - Logging
    - Retry logic
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        """
        Initialize integration
        
        Args:
            client_id: LeaseAI client ID
            config: Integration-specific configuration (API keys, endpoints, etc.)
        """
        self.client_id = client_id
        self.config = config
        self.integration_type = self._get_integration_type()
        self.authenticated = False
    
    @abstractmethod
    def _get_integration_type(self) -> IntegrationType:
        """Return the integration type"""
        pass
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the third-party service
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the third-party service
        
        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        pass
    
    def ensure_authenticated(self):
        """Ensure the integration is authenticated, raise error if not"""
        if not self.authenticated:
            success = self.authenticate()
            if not success:
                raise AuthenticationError(f"Failed to authenticate with {self.integration_type.value}")
    
    def log_sync(
        self,
        action: str,
        status: IntegrationStatus,
        record_count: int = 0,
        details: Optional[Dict] = None,
        error_message: Optional[str] = None
    ):
        """
        Log integration sync activity
        
        Args:
            action: What action was performed (e.g., "export_lease", "import_tenant")
            status: Sync status
            record_count: Number of records processed
            details: Additional details (JSON-serializable)
            error_message: Error message if failed
        """
        # In production, this would write to integration_logs table
        log_entry = {
            'client_id': self.client_id,
            'integration_type': self.integration_type.value,
            'action': action,
            'status': status.value,
            'record_count': record_count,
            'details': details or {},
            'error_message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        # For now, just print (in production, save to database)
        print(f"[{self.integration_type.value}] {action}: {status.value}")
        if error_message:
            print(f"  Error: {error_message}")


class LeaseExportMixin:
    """
    Mixin for integrations that support exporting leases
    """
    
    @abstractmethod
    def export_lease(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a single lease to the third-party system
        
        Args:
            lease_data: Lease data from LeaseAI (extracted fields)
            
        Returns:
            Dict with 'success' (bool), 'external_id' (str), 'message' (str)
        """
        pass
    
    @abstractmethod
    def export_leases_bulk(self, leases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Export multiple leases in bulk
        
        Args:
            leases: List of lease data dictionaries
            
        Returns:
            Dict with 'success', 'succeeded_count', 'failed_count', 'details'
        """
        pass


class TenantExportMixin:
    """
    Mixin for integrations that support exporting tenants
    """
    
    @abstractmethod
    def export_tenant(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a single tenant to the third-party system
        
        Args:
            tenant_data: Tenant data from LeaseAI
            
        Returns:
            Dict with 'success', 'external_id', 'message'
        """
        pass


class BidirectionalSyncMixin:
    """
    Mixin for integrations that support bidirectional sync
    """
    
    @abstractmethod
    def import_leases(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Import leases from the third-party system
        
        Args:
            filters: Optional filters (e.g., date range, property ID)
            
        Returns:
            Dict with 'success', 'imported_count', 'leases'
        """
        pass
    
    @abstractmethod
    def resolve_conflicts(self, lease_id: str, strategy: str = "leaseai_wins") -> Dict[str, Any]:
        """
        Resolve conflicts when data differs between systems
        
        Args:
            lease_id: LeaseAI lease ID
            strategy: Conflict resolution strategy ("leaseai_wins", "external_wins", "manual")
            
        Returns:
            Dict with 'success', 'resolved_fields', 'message'
        """
        pass


class WebhookMixin:
    """
    Mixin for integrations that support webhooks
    """
    
    @abstractmethod
    def register_webhook(self, webhook_url: str, events: List[str]) -> Dict[str, Any]:
        """
        Register a webhook with the third-party service
        
        Args:
            webhook_url: URL to receive webhook events
            events: List of event types to subscribe to
            
        Returns:
            Dict with 'success', 'webhook_id', 'message'
        """
        pass
    
    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming webhook event
        
        Args:
            payload: Webhook payload from third-party service
            
        Returns:
            Dict with 'success', 'action_taken', 'message'
        """
        pass


# Utility functions

def map_lease_fields(lease_data: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Map LeaseAI lease fields to external system fields
    
    Args:
        lease_data: Lease data from LeaseAI
        field_mapping: Dict mapping LeaseAI field names to external field names
        
    Returns:
        Mapped data dictionary
    """
    mapped_data = {}
    
    for leaseai_field, external_field in field_mapping.items():
        if leaseai_field in lease_data and lease_data[leaseai_field] is not None:
            # Handle nested fields (e.g., "tenant.name" -> "TenantName")
            value = lease_data[leaseai_field]
            mapped_data[external_field] = value
    
    return mapped_data


def format_date(date_value: Any, format: str = "%Y-%m-%d") -> Optional[str]:
    """
    Format a date value to a standard string format
    
    Args:
        date_value: Date value (string, datetime, or None)
        format: Output format string
        
    Returns:
        Formatted date string or None
    """
    if date_value is None:
        return None
    
    if isinstance(date_value, str):
        # Try to parse string date
        try:
            from dateutil import parser
            dt = parser.parse(date_value)
            return dt.strftime(format)
        except:
            return date_value
    
    elif isinstance(date_value, datetime):
        return date_value.strftime(format)
    
    else:
        return str(date_value)


def format_currency(amount: Any, decimals: int = 2) -> Optional[float]:
    """
    Format currency values
    
    Args:
        amount: Currency amount (string, float, or None)
        decimals: Number of decimal places
        
    Returns:
        Formatted float or None
    """
    if amount is None:
        return None
    
    try:
        # Remove currency symbols and commas
        if isinstance(amount, str):
            amount = amount.replace('$', '').replace(',', '').strip()
        
        return round(float(amount), decimals)
    except:
        return None


def retry_on_failure(func, max_retries: int = 3, delay: int = 1):
    """
    Decorator to retry a function on failure
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Delay between retries (seconds)
    """
    import time
    
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                time.sleep(delay)
    
    return wrapper
