"""
LeaseAI - MRI Software Integration
Phase 7: Native API Integrations

Native API connector for MRI Software property management system.
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
    map_lease_fields,
    format_date,
    format_currency
)


class MRISoftwareIntegration(BaseIntegration, LeaseExportMixin, TenantExportMixin):
    """
    MRI Software API Integration
    
    Provides:
    - API key authentication
    - Lease export (LeaseAI → MRI)
    - Tenant export (LeaseAI → MRI)
    - Property and unit mapping
    
    Required config:
    - api_key: MRI API key
    - api_endpoint: MRI API endpoint URL
    - company_id: MRI company/database ID
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        super().__init__(client_id, config)
        
        self.api_key = config.get('api_key')
        self.api_endpoint = config.get('api_endpoint', 'https://api.mrisoftware.com')
        self.company_id = config.get('company_id')
    
    def _get_integration_type(self) -> IntegrationType:
        return IntegrationType.MRI_SOFTWARE
    
    def authenticate(self) -> bool:
        """
        Authenticate with MRI Software (API key based)
        
        Returns:
            True if authentication successful
        """
        if not self.api_key:
            print("❌ MRI API key not configured")
            return False
        
        try:
            # Test authentication by making a simple API call
            test_result = self.test_connection()
            
            if test_result['success']:
                self.authenticated = True
                print(f"✅ Successfully authenticated with MRI Software")
                return True
            else:
                print(f"❌ MRI authentication failed: {test_result['message']}")
                return False
        
        except Exception as e:
            print(f"❌ MRI authentication error: {str(e)}")
            return False
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request to MRI
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON
        """
        self.ensure_authenticated()
        
        url = f"{self.api_endpoint}/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Company-Id': str(self.company_id)
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
            raise SyncError(f"MRI API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise SyncError(f"MRI request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to MRI Software
        
        Returns:
            Dict with 'success' and 'message'
        """
        try:
            # Test by fetching properties
            endpoint = f"api/v1/companies/{self.company_id}/properties"
            response = self._make_request('GET', endpoint, params={'limit': 1})
            
            return {
                'success': True,
                'message': 'Successfully connected to MRI Software',
                'properties_count': len(response.get('data', []))
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }
    
    def export_lease(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a single lease to MRI Software
        
        Args:
            lease_data: Lease data from LeaseAI
            
        Returns:
            Dict with 'success', 'external_id', 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Map LeaseAI fields to MRI fields
            mri_lease = self._map_lease_to_mri(lease_data)
            
            # Create or update lease in MRI
            endpoint = f"api/v1/companies/{self.company_id}/leases"
            response = self._make_request('POST', endpoint, data=mri_lease)
            
            external_id = response.get('id') or response.get('leaseId')
            
            self.log_sync(
                action='export_lease',
                status=IntegrationStatus.SUCCESS,
                record_count=1,
                details={'lease_id': lease_data.get('id'), 'mri_lease_id': external_id}
            )
            
            return {
                'success': True,
                'external_id': external_id,
                'message': f'Lease exported to MRI successfully (ID: {external_id})'
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
                    'mri_id': result['external_id']
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
        Export a single tenant to MRI Software
        
        Args:
            tenant_data: Tenant data from LeaseAI
            
        Returns:
            Dict with 'success', 'external_id', 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Map tenant data to MRI format
            mri_tenant = {
                'name': tenant_data.get('tenant_name'),
                'code': tenant_data.get('tenant_code') or tenant_data.get('id'),
                'contactName': tenant_data.get('contact_name'),
                'email': tenant_data.get('email'),
                'phone': tenant_data.get('phone'),
                'address': {
                    'street': tenant_data.get('address'),
                    'city': tenant_data.get('city'),
                    'state': tenant_data.get('state'),
                    'zip': tenant_data.get('zip_code')
                }
            }
            
            # Remove None values
            mri_tenant = {k: v for k, v in mri_tenant.items() if v is not None}
            
            endpoint = f"api/v1/companies/{self.company_id}/tenants"
            response = self._make_request('POST', endpoint, data=mri_tenant)
            
            external_id = response.get('id') or response.get('tenantId')
            
            return {
                'success': True,
                'external_id': external_id,
                'message': f'Tenant exported to MRI successfully (ID: {external_id})'
            }
        
        except Exception as e:
            return {
                'success': False,
                'external_id': None,
                'message': f'Failed to export tenant: {str(e)}'
            }
    
    def _map_lease_to_mri(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map LeaseAI lease data to MRI Software format
        
        Args:
            lease_data: LeaseAI lease data
            
        Returns:
            MRI-formatted lease dictionary
        """
        
        # MRI field mapping
        mri_lease = {
            # Property & Unit
            'propertyCode': lease_data.get('property_code'),
            'unitNumber': lease_data.get('unit_number') or lease_data.get('suite_number'),
            
            # Tenant
            'tenantCode': lease_data.get('tenant_code') or lease_data.get('tenant_name'),
            'tenantName': lease_data.get('tenant_name'),
            
            # Lease Dates
            'leaseStartDate': format_date(lease_data.get('lease_start_date')),
            'leaseEndDate': format_date(lease_data.get('lease_expiration_date')),
            'commencementDate': format_date(lease_data.get('commencement_date')),
            'rentCommencementDate': format_date(lease_data.get('rent_commencement_date')),
            
            # Financial
            'baseRent': format_currency(lease_data.get('base_rent')),
            'securityDeposit': format_currency(lease_data.get('security_deposit')),
            'rentableSquareFeet': lease_data.get('rentable_square_feet'),
            
            # Lease Type
            'leaseType': lease_data.get('lease_type'),
            'leaseStatus': 'Active',
            
            # Additional fields
            'executionDate': format_date(lease_data.get('lease_execution_date')),
            'rentEscalationRate': lease_data.get('rent_escalation_percentage'),
            'parkingSpaces': lease_data.get('parking_spaces'),
            
            # Notes
            'notes': lease_data.get('notes') or lease_data.get('special_provisions')
        }
        
        # Remove None values
        mri_lease = {k: v for k, v in mri_lease.items() if v is not None}
        
        return mri_lease
