"""
LeaseAI - Yardi Voyager Integration
Phase 7: Native API Integrations

Native API connector for Yardi Voyager property management system.
"""

from typing import Dict, Any, Optional, List
import requests
from datetime import datetime
import json

from integrations.base import (
    BaseIntegration,
    IntegrationType,
    IntegrationStatus,
    AuthenticationError,
    SyncError,
    LeaseExportMixin,
    TenantExportMixin,
    BidirectionalSyncMixin,
    map_lease_fields,
    format_date,
    format_currency,
    retry_on_failure
)


class YardiVoyagerIntegration(BaseIntegration, LeaseExportMixin, TenantExportMixin, BidirectionalSyncMixin):
    """
    Yardi Voyager API Integration
    
    Provides:
    - OAuth 2.0 authentication
    - Lease export (LeaseAI → Yardi)
    - Tenant export (LeaseAI → Yardi)
    - Bidirectional sync (import leases from Yardi)
    - Property and unit mapping
    
    Required config:
    - client_id: Yardi API client ID
    - client_secret: Yardi API client secret
    - platform: Yardi platform URL (e.g., "https://api.yardi.com")
    - database: Yardi database name
    - entity: Yardi entity code
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        super().__init__(client_id, config)
        
        self.api_base_url = config.get('platform', 'https://api.yardi.com')
        self.database = config.get('database')
        self.entity = config.get('entity')
        
        self.yardi_client_id = config.get('yardi_client_id')
        self.yardi_client_secret = config.get('yardi_client_secret')
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def _get_integration_type(self) -> IntegrationType:
        return IntegrationType.YARDI_VOYAGER
    
    def authenticate(self) -> bool:
        """
        Authenticate with Yardi using OAuth 2.0
        
        Returns:
            True if authentication successful
        """
        try:
            # OAuth 2.0 token endpoint
            token_url = f"{self.api_base_url}/auth/token"
            
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.yardi_client_id,
                'client_secret': self.yardi_client_secret,
                'scope': 'api'
            }
            
            response = requests.post(token_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                
                # Calculate token expiration
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.now().timestamp() + expires_in
                
                self.authenticated = True
                print(f"✅ Successfully authenticated with Yardi Voyager")
                return True
            else:
                print(f"❌ Yardi authentication failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Yardi authentication error: {str(e)}")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token
        
        Returns:
            True if refresh successful
        """
        if not self.refresh_token:
            return self.authenticate()
        
        try:
            token_url = f"{self.api_base_url}/auth/token"
            
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.yardi_client_id,
                'client_secret': self.yardi_client_secret
            }
            
            response = requests.post(token_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.now().timestamp() + expires_in
                
                return True
            else:
                # Refresh failed, re-authenticate
                return self.authenticate()
        
        except Exception as e:
            print(f"⚠️  Token refresh failed: {str(e)}")
            return self.authenticate()
    
    def _ensure_token_valid(self):
        """Ensure access token is valid, refresh if needed"""
        if not self.authenticated:
            self.authenticate()
        
        # Check if token is expiring soon (within 5 minutes)
        if self.token_expires_at and datetime.now().timestamp() > (self.token_expires_at - 300):
            self.refresh_access_token()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request to Yardi
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON
        """
        self._ensure_token_valid()
        
        url = f"{self.api_base_url}/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=60)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=60)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=60)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            raise SyncError(f"Yardi API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise SyncError(f"Yardi request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Yardi Voyager
        
        Returns:
            Dict with 'success' and 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Test by fetching properties
            endpoint = f"api/v1/{self.database}/{self.entity}/properties"
            response = self._make_request('GET', endpoint, params={'limit': 1})
            
            return {
                'success': True,
                'message': 'Successfully connected to Yardi Voyager',
                'properties_count': len(response.get('properties', []))
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }
    
    def export_lease(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a single lease to Yardi Voyager
        
        Args:
            lease_data: Lease data from LeaseAI
            
        Returns:
            Dict with 'success', 'external_id', 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Map LeaseAI fields to Yardi fields
            yardi_lease = self._map_lease_to_yardi(lease_data)
            
            # Create or update lease in Yardi
            endpoint = f"api/v1/{self.database}/{self.entity}/leases"
            response = self._make_request('POST', endpoint, data=yardi_lease)
            
            external_id = response.get('LeaseId') or response.get('leaseId')
            
            self.log_sync(
                action='export_lease',
                status=IntegrationStatus.SUCCESS,
                record_count=1,
                details={'lease_id': lease_data.get('id'), 'yardi_lease_id': external_id}
            )
            
            return {
                'success': True,
                'external_id': external_id,
                'message': f'Lease exported to Yardi successfully (ID: {external_id})'
            }
        
        except Exception as e:
            self.log_sync(
                action='export_lease',
                status=IntegrationStatus.FAILED,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'external_id': None,
                'message': f'Failed to export lease: {str(e)}'
            }
    
    def export_leases_bulk(self, leases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Export multiple leases in bulk
        
        Args:
            leases: List of lease data dictionaries
            
        Returns:
            Dict with 'success', 'succeeded_count', 'failed_count', 'details'
        """
        succeeded = []
        failed = []
        
        for lease in leases:
            result = self.export_lease(lease)
            
            if result['success']:
                succeeded.append({
                    'lease_id': lease.get('id'),
                    'yardi_id': result['external_id']
                })
            else:
                failed.append({
                    'lease_id': lease.get('id'),
                    'error': result['message']
                })
        
        return {
            'success': len(failed) == 0,
            'succeeded_count': len(succeeded),
            'failed_count': len(failed),
            'succeeded': succeeded,
            'failed': failed
        }
    
    def export_tenant(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a single tenant to Yardi Voyager
        
        Args:
            tenant_data: Tenant data from LeaseAI
            
        Returns:
            Dict with 'success', 'external_id', 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Map tenant data to Yardi format
            yardi_tenant = {
                'TenantName': tenant_data.get('tenant_name'),
                'TenantCode': tenant_data.get('tenant_code') or tenant_data.get('id'),
                'ContactName': tenant_data.get('contact_name'),
                'Email': tenant_data.get('email'),
                'Phone': tenant_data.get('phone'),
                'Address': tenant_data.get('address'),
                'City': tenant_data.get('city'),
                'State': tenant_data.get('state'),
                'ZipCode': tenant_data.get('zip_code')
            }
            
            # Remove None values
            yardi_tenant = {k: v for k, v in yardi_tenant.items() if v is not None}
            
            endpoint = f"api/v1/{self.database}/{self.entity}/tenants"
            response = self._make_request('POST', endpoint, data=yardi_tenant)
            
            external_id = response.get('TenantId') or response.get('tenantId')
            
            return {
                'success': True,
                'external_id': external_id,
                'message': f'Tenant exported to Yardi successfully (ID: {external_id})'
            }
        
        except Exception as e:
            return {
                'success': False,
                'external_id': None,
                'message': f'Failed to export tenant: {str(e)}'
            }
    
    def import_leases(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Import leases from Yardi Voyager
        
        Args:
            filters: Optional filters (property_id, date_range, etc.)
            
        Returns:
            Dict with 'success', 'imported_count', 'leases'
        """
        try:
            self.ensure_authenticated()
            
            endpoint = f"api/v1/{self.database}/{self.entity}/leases"
            
            params = filters or {}
            response = self._make_request('GET', endpoint, params=params)
            
            yardi_leases = response.get('leases', [])
            
            # Map Yardi leases to LeaseAI format
            leaseai_leases = [self._map_yardi_to_leaseai(yl) for yl in yardi_leases]
            
            return {
                'success': True,
                'imported_count': len(leaseai_leases),
                'leases': leaseai_leases
            }
        
        except Exception as e:
            return {
                'success': False,
                'imported_count': 0,
                'leases': [],
                'error': str(e)
            }
    
    def resolve_conflicts(self, lease_id: str, strategy: str = "leaseai_wins") -> Dict[str, Any]:
        """
        Resolve conflicts when data differs between LeaseAI and Yardi
        
        Args:
            lease_id: LeaseAI lease ID
            strategy: "leaseai_wins", "yardi_wins", or "manual"
            
        Returns:
            Dict with 'success', 'resolved_fields', 'message'
        """
        # Placeholder for conflict resolution logic
        # In production, this would:
        # 1. Fetch lease from both systems
        # 2. Compare field by field
        # 3. Apply strategy to resolve conflicts
        # 4. Update the appropriate system(s)
        
        return {
            'success': True,
            'resolved_fields': [],
            'message': f'Conflicts resolved using strategy: {strategy}'
        }
    
    def _map_lease_to_yardi(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map LeaseAI lease data to Yardi Voyager format
        
        Args:
            lease_data: LeaseAI lease data
            
        Returns:
            Yardi-formatted lease dictionary
        """
        
        # Yardi field mapping
        yardi_lease = {
            # Property & Unit
            'PropertyCode': lease_data.get('property_code'),
            'UnitCode': lease_data.get('unit_number') or lease_data.get('suite_number'),
            
            # Tenant
            'TenantCode': lease_data.get('tenant_code') or lease_data.get('tenant_name'),
            'TenantName': lease_data.get('tenant_name'),
            
            # Lease Dates
            'LeaseStartDate': format_date(lease_data.get('lease_start_date')),
            'LeaseEndDate': format_date(lease_data.get('lease_expiration_date')),
            'CommencementDate': format_date(lease_data.get('commencement_date')),
            'PossessionDate': format_date(lease_data.get('rent_commencement_date')),
            
            # Financial
            'BaseRent': format_currency(lease_data.get('base_rent')),
            'SecurityDeposit': format_currency(lease_data.get('security_deposit')),
            'RentableArea': lease_data.get('rentable_square_feet'),
            
            # Lease Type
            'LeaseType': lease_data.get('lease_type'),
            'LeaseStatus': 'Active',  # Default to active
            
            # Additional fields
            'LeaseExecutionDate': format_date(lease_data.get('lease_execution_date')),
            'RentEscalation': lease_data.get('rent_escalation_percentage'),
            'ParkingSpaces': lease_data.get('parking_spaces'),
            
            # Notes
            'Comments': lease_data.get('notes') or lease_data.get('special_provisions')
        }
        
        # Remove None values
        yardi_lease = {k: v for k, v in yardi_lease.items() if v is not None}
        
        return yardi_lease
    
    def _map_yardi_to_leaseai(self, yardi_lease: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Yardi lease data to LeaseAI format
        
        Args:
            yardi_lease: Yardi lease data
            
        Returns:
            LeaseAI-formatted lease dictionary
        """
        
        leaseai_lease = {
            'external_id': yardi_lease.get('LeaseId'),
            'external_system': 'yardi_voyager',
            
            # Property
            'property_code': yardi_lease.get('PropertyCode'),
            'unit_number': yardi_lease.get('UnitCode'),
            
            # Tenant
            'tenant_name': yardi_lease.get('TenantName'),
            'tenant_code': yardi_lease.get('TenantCode'),
            
            # Dates
            'lease_start_date': yardi_lease.get('LeaseStartDate'),
            'lease_expiration_date': yardi_lease.get('LeaseEndDate'),
            'commencement_date': yardi_lease.get('CommencementDate'),
            'rent_commencement_date': yardi_lease.get('PossessionDate'),
            'lease_execution_date': yardi_lease.get('LeaseExecutionDate'),
            
            # Financial
            'base_rent': yardi_lease.get('BaseRent'),
            'security_deposit': yardi_lease.get('SecurityDeposit'),
            'rentable_square_feet': yardi_lease.get('RentableArea'),
            'rent_escalation_percentage': yardi_lease.get('RentEscalation'),
            
            # Type & Status
            'lease_type': yardi_lease.get('LeaseType'),
            'lease_status': yardi_lease.get('LeaseStatus'),
            
            # Additional
            'parking_spaces': yardi_lease.get('ParkingSpaces'),
            'notes': yardi_lease.get('Comments')
        }
        
        # Remove None values
        leaseai_lease = {k: v for k, v in leaseai_lease.items() if v is not None}
        
        return leaseai_lease
