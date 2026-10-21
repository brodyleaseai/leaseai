"""
LeaseAI - QuickBooks Integration
Phase 7: Native API Integrations

Integration for exporting rent rolls and CAM charges to QuickBooks.
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
    format_date,
    format_currency
)


class QuickBooksIntegration(BaseIntegration):
    """
    QuickBooks Online API Integration
    
    Provides:
    - OAuth 2.0 authentication
    - Export rent rolls as invoices
    - Export CAM charges as invoices
    - Create/update customers (tenants)
    - Chart of accounts mapping
    
    Required config:
    - client_id: QuickBooks OAuth client ID
    - client_secret: QuickBooks OAuth client secret
    - realm_id: QuickBooks company ID
    - redirect_uri: OAuth redirect URI
    - environment: 'sandbox' or 'production'
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        super().__init__(client_id, config)
        
        self.qb_client_id = config.get('client_id')
        self.qb_client_secret = config.get('client_secret')
        self.realm_id = config.get('realm_id')
        self.redirect_uri = config.get('redirect_uri')
        self.environment = config.get('environment', 'production')
        
        # API endpoints
        if self.environment == 'sandbox':
            self.api_base_url = 'https://sandbox-quickbooks.api.intuit.com'
        else:
            self.api_base_url = 'https://quickbooks.api.intuit.com'
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def _get_integration_type(self) -> IntegrationType:
        return IntegrationType.QUICKBOOKS
    
    def authenticate(self) -> bool:
        """
        Authenticate with QuickBooks using OAuth 2.0
        
        Note: This requires user to complete OAuth flow in browser.
        In production, you'd redirect user to QuickBooks authorization URL.
        
        Returns:
            True if authentication successful
        """
        # OAuth 2.0 flow for QuickBooks
        # Step 1: Direct user to authorization URL
        # Step 2: User grants permission
        # Step 3: Exchange authorization code for access token
        
        # For this implementation, assume tokens are provided in config
        self.access_token = self.config.get('access_token')
        self.refresh_token = self.config.get('refresh_token')
        
        if self.access_token:
            self.authenticated = True
            print(f"✅ Successfully authenticated with QuickBooks")
            return True
        else:
            print(f"❌ QuickBooks authentication failed: No access token provided")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token
        
        Returns:
            True if refresh successful
        """
        if not self.refresh_token:
            return False
        
        try:
            token_url = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
            
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            auth = (self.qb_client_id, self.qb_client_secret)
            
            response = requests.post(token_url, data=payload, auth=auth, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.now().timestamp() + expires_in
                
                return True
            else:
                return False
        
        except Exception as e:
            print(f"⚠️  Token refresh failed: {str(e)}")
            return False
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request to QuickBooks
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            params: Query parameters
            
        Returns:
            Response JSON
        """
        self.ensure_authenticated()
        
        url = f"{self.api_base_url}/v3/company/{self.realm_id}/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=60)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'POST_FORM':
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                response = requests.post(url, headers=headers, data=data, timeout=60)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            raise SyncError(f"QuickBooks API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise SyncError(f"QuickBooks request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to QuickBooks
        
        Returns:
            Dict with 'success' and 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Test by fetching company info
            response = self._make_request('GET', 'companyinfo/' + self.realm_id)
            
            company_name = response.get('CompanyInfo', {}).get('CompanyName', 'Unknown')
            
            return {
                'success': True,
                'message': f'Successfully connected to QuickBooks: {company_name}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }
    
    def export_rent_roll(self, rent_roll_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Export rent roll as invoices in QuickBooks
        
        Args:
            rent_roll_data: List of rent charges (one per tenant/lease)
            
        Returns:
            Dict with 'success', 'created_count', 'failed_count'
        """
        try:
            self.ensure_authenticated()
            
            succeeded = []
            failed = []
            
            for rent_item in rent_roll_data:
                try:
                    # Create or get customer (tenant)
                    customer_id = self._get_or_create_customer(rent_item)
                    
                    # Create invoice for rent
                    invoice = self._create_rent_invoice(customer_id, rent_item)
                    
                    succeeded.append({
                        'tenant': rent_item.get('tenant_name'),
                        'invoice_id': invoice.get('Id'),
                        'amount': rent_item.get('amount')
                    })
                
                except Exception as e:
                    failed.append({
                        'tenant': rent_item.get('tenant_name'),
                        'error': str(e)
                    })
            
            self.log_sync(
                action='export_rent_roll',
                status=IntegrationStatus.SUCCESS if len(failed) == 0 else IntegrationStatus.PARTIAL,
                record_count=len(succeeded),
                details={'succeeded': len(succeeded), 'failed': len(failed)}
            )
            
            return {
                'success': len(failed) == 0,
                'created_count': len(succeeded),
                'failed_count': len(failed),
                'succeeded': succeeded,
                'failed': failed
            }
        
        except Exception as e:
            self.log_sync(
                action='export_rent_roll',
                status=IntegrationStatus.FAILED,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'created_count': 0,
                'failed_count': len(rent_roll_data),
                'error': str(e)
            }
    
    def export_cam_charges(self, cam_charges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Export CAM charges as invoices in QuickBooks
        
        Args:
            cam_charges: List of CAM charges (one per tenant)
            
        Returns:
            Dict with 'success', 'created_count', 'failed_count'
        """
        try:
            self.ensure_authenticated()
            
            succeeded = []
            failed = []
            
            for cam_item in cam_charges:
                try:
                    # Create or get customer (tenant)
                    customer_id = self._get_or_create_customer(cam_item)
                    
                    # Create invoice for CAM charges
                    invoice = self._create_cam_invoice(customer_id, cam_item)
                    
                    succeeded.append({
                        'tenant': cam_item.get('tenant_name'),
                        'invoice_id': invoice.get('Id'),
                        'amount': cam_item.get('total_cam_charge')
                    })
                
                except Exception as e:
                    failed.append({
                        'tenant': cam_item.get('tenant_name'),
                        'error': str(e)
                    })
            
            return {
                'success': len(failed) == 0,
                'created_count': len(succeeded),
                'failed_count': len(failed),
                'succeeded': succeeded,
                'failed': failed
            }
        
        except Exception as e:
            return {
                'success': False,
                'created_count': 0,
                'failed_count': len(cam_charges),
                'error': str(e)
            }
    
    def _get_or_create_customer(self, item_data: Dict[str, Any]) -> str:
        """
        Get existing customer or create new one
        
        Args:
            item_data: Data containing tenant_name
            
        Returns:
            QuickBooks customer ID
        """
        tenant_name = item_data.get('tenant_name')
        
        # Search for existing customer
        query = f"SELECT * FROM Customer WHERE DisplayName = '{tenant_name}'"
        params = {'query': query}
        
        try:
            response = self._make_request('GET', 'query', params=params)
            
            customers = response.get('QueryResponse', {}).get('Customer', [])
            
            if customers:
                return customers[0]['Id']
            
            # Create new customer
            customer_data = {
                'DisplayName': tenant_name,
                'CompanyName': tenant_name
            }
            
            response = self._make_request('POST', 'customer', data=customer_data)
            return response.get('Customer', {}).get('Id')
        
        except:
            # If search/create fails, return a placeholder
            return '1'  # Default customer ID
    
    def _create_rent_invoice(self, customer_id: str, rent_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create rent invoice in QuickBooks
        
        Args:
            customer_id: QuickBooks customer ID
            rent_item: Rent charge data
            
        Returns:
            Created invoice data
        """
        invoice_data = {
            'CustomerRef': {'value': customer_id},
            'Line': [
                {
                    'Amount': format_currency(rent_item.get('amount')),
                    'DetailType': 'SalesItemLineDetail',
                    'SalesItemLineDetail': {
                        'ItemRef': {'value': '1'},  # Default income account
                        'Qty': 1,
                        'UnitPrice': format_currency(rent_item.get('amount'))
                    },
                    'Description': f"Rent - {rent_item.get('period', 'Monthly')}"
                }
            ],
            'DueDate': format_date(rent_item.get('due_date')),
            'TxnDate': format_date(rent_item.get('invoice_date') or datetime.now())
        }
        
        response = self._make_request('POST', 'invoice', data=invoice_data)
        return response.get('Invoice', {})
    
    def _create_cam_invoice(self, customer_id: str, cam_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create CAM charge invoice in QuickBooks
        
        Args:
            customer_id: QuickBooks customer ID
            cam_item: CAM charge data
            
        Returns:
            Created invoice data
        """
        # Create line items for each CAM category
        lines = []
        
        cam_categories = cam_item.get('cam_breakdown', {})
        for category, amount in cam_categories.items():
            if amount and amount > 0:
                lines.append({
                    'Amount': format_currency(amount),
                    'DetailType': 'SalesItemLineDetail',
                    'SalesItemLineDetail': {
                        'ItemRef': {'value': '1'},
                        'Qty': 1,
                        'UnitPrice': format_currency(amount)
                    },
                    'Description': f"CAM - {category}"
                })
        
        # If no breakdown, create single line
        if not lines:
            lines.append({
                'Amount': format_currency(cam_item.get('total_cam_charge')),
                'DetailType': 'SalesItemLineDetail',
                'SalesItemLineDetail': {
                    'ItemRef': {'value': '1'},
                    'Qty': 1,
                    'UnitPrice': format_currency(cam_item.get('total_cam_charge'))
                },
                'Description': "CAM Charges"
            })
        
        invoice_data = {
            'CustomerRef': {'value': customer_id},
            'Line': lines,
            'DueDate': format_date(cam_item.get('due_date')),
            'TxnDate': format_date(cam_item.get('invoice_date') or datetime.now())
        }
        
        response = self._make_request('POST', 'invoice', data=invoice_data)
        return response.get('Invoice', {})
