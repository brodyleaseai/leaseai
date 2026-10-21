"""
LeaseAI - DocuSign Integration
Phase 7: Native API Integrations

Integration for sending lease amendments and documents for e-signature via DocuSign.
"""

from typing import Dict, Any, Optional, List
import requests
from datetime import datetime
import base64
import json

from integrations.base import (
    BaseIntegration,
    IntegrationType,
    IntegrationStatus,
    AuthenticationError,
    SyncError
)


class DocuSignIntegration(BaseIntegration):
    """
    DocuSign eSignature API Integration
    
    Provides:
    - OAuth 2.0 authentication
    - Send lease amendments for signature
    - Track signature status
    - Download signed documents
    - Template management
    
    Required config:
    - integration_key: DocuSign OAuth client ID
    - secret_key: DocuSign OAuth client secret
    - account_id: DocuSign account ID
    - environment: 'demo' or 'production'
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        super().__init__(client_id, config)
        
        self.integration_key = config.get('integration_key')
        self.secret_key = config.get('secret_key')
        self.account_id = config.get('account_id')
        self.environment = config.get('environment', 'demo')
        
        # API endpoints
        if self.environment == 'demo':
            self.auth_base_url = 'https://account-d.docusign.com'
            self.api_base_url = 'https://demo.docusign.net/restapi'
        else:
            self.auth_base_url = 'https://account.docusign.com'
            self.api_base_url = 'https://na1.docusign.net/restapi'  # Will be updated after auth
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def _get_integration_type(self) -> IntegrationType:
        return IntegrationType.DOCUSIGN
    
    def authenticate(self) -> bool:
        """
        Authenticate with DocuSign using OAuth 2.0
        
        Returns:
            True if authentication successful
        """
        try:
            # For this implementation, assume tokens are provided in config
            # In production, you'd implement full OAuth flow
            self.access_token = self.config.get('access_token')
            
            if self.access_token:
                # Get user info to determine base URL
                self._get_user_info()
                
                self.authenticated = True
                print(f"✅ Successfully authenticated with DocuSign")
                return True
            else:
                print(f"❌ DocuSign authentication failed: No access token provided")
                return False
        
        except Exception as e:
            print(f"❌ DocuSign authentication error: {str(e)}")
            return False
    
    def _get_user_info(self):
        """Get user info and set correct base URL"""
        try:
            url = f"{self.auth_base_url}/oauth/userinfo"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                user_info = response.json()
                accounts = user_info.get('accounts', [])
                
                if accounts:
                    account = accounts[0]
                    self.account_id = account.get('account_id')
                    self.api_base_url = account.get('base_uri') + '/restapi'
        
        except:
            pass  # Use default base URL
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request to DocuSign
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            params: Query parameters
            files: Files to upload
            
        Returns:
            Response JSON
        """
        self.ensure_authenticated()
        
        url = f"{self.api_base_url}/v2.1/accounts/{self.account_id}/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        if not files:
            headers['Content-Type'] = 'application/json'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=60)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=60)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.text else {}
        
        except requests.exceptions.HTTPError as e:
            raise SyncError(f"DocuSign API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise SyncError(f"DocuSign request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to DocuSign
        
        Returns:
            Dict with 'success' and 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Test by fetching account info
            response = self._make_request('GET', '')
            
            account_name = response.get('accountName', 'Unknown')
            
            return {
                'success': True,
                'message': f'Successfully connected to DocuSign: {account_name}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }
    
    def send_amendment_for_signature(
        self,
        amendment_data: Dict[str, Any],
        signers: List[Dict[str, Any]],
        pdf_content: bytes
    ) -> Dict[str, Any]:
        """
        Send lease amendment for e-signature
        
        Args:
            amendment_data: Amendment metadata (lease_id, amendment_number, etc.)
            signers: List of signers with name, email, role
            pdf_content: PDF file content (bytes)
            
        Returns:
            Dict with 'success', 'envelope_id', 'message'
        """
        try:
            self.ensure_authenticated()
            
            # Create envelope with amendment document
            envelope_definition = self._create_envelope_definition(
                amendment_data,
                signers,
                pdf_content
            )
            
            response = self._make_request('POST', 'envelopes', data=envelope_definition)
            
            envelope_id = response.get('envelopeId')
            status = response.get('status')
            
            self.log_sync(
                action='send_amendment_for_signature',
                status=IntegrationStatus.SUCCESS,
                record_count=1,
                details={
                    'amendment_id': amendment_data.get('id'),
                    'envelope_id': envelope_id,
                    'signers_count': len(signers)
                }
            )
            
            return {
                'success': True,
                'envelope_id': envelope_id,
                'status': status,
                'message': f'Amendment sent for signature successfully (Envelope ID: {envelope_id})'
            }
        
        except Exception as e:
            self.log_sync(
                action='send_amendment_for_signature',
                status=IntegrationStatus.FAILED,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'envelope_id': None,
                'message': f'Failed to send amendment: {str(e)}'
            }
    
    def get_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """
        Get status of an envelope (document sent for signature)
        
        Args:
            envelope_id: DocuSign envelope ID
            
        Returns:
            Dict with 'status', 'completed_signers', 'pending_signers'
        """
        try:
            self.ensure_authenticated()
            
            response = self._make_request('GET', f'envelopes/{envelope_id}')
            
            status = response.get('status')
            
            # Get recipients
            recipients_response = self._make_request('GET', f'envelopes/{envelope_id}/recipients')
            
            signers = recipients_response.get('signers', [])
            
            completed_signers = [s for s in signers if s.get('status') == 'completed']
            pending_signers = [s for s in signers if s.get('status') in ['sent', 'delivered']]
            
            return {
                'status': status,
                'completed_signers': len(completed_signers),
                'pending_signers': len(pending_signers),
                'signers_detail': signers
            }
        
        except Exception as e:
            return {
                'status': 'unknown',
                'error': str(e)
            }
    
    def download_signed_document(self, envelope_id: str) -> Dict[str, Any]:
        """
        Download signed document after all signatures collected
        
        Args:
            envelope_id: DocuSign envelope ID
            
        Returns:
            Dict with 'success', 'pdf_content' (bytes), 'message'
        """
        try:
            self.ensure_authenticated()
            
            url = f"{self.api_base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/pdf'
            }
            
            response = requests.get(url, headers=headers, timeout=120)
            response.raise_for_status()
            
            return {
                'success': True,
                'pdf_content': response.content,
                'message': 'Signed document downloaded successfully'
            }
        
        except Exception as e:
            return {
                'success': False,
                'pdf_content': None,
                'message': f'Failed to download document: {str(e)}'
            }
    
    def _create_envelope_definition(
        self,
        amendment_data: Dict[str, Any],
        signers: List[Dict[str, Any]],
        pdf_content: bytes
    ) -> Dict[str, Any]:
        """
        Create envelope definition for DocuSign
        
        Args:
            amendment_data: Amendment metadata
            signers: List of signers
            pdf_content: PDF content
            
        Returns:
            Envelope definition dictionary
        """
        
        # Encode PDF to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Create signer objects
        signer_objects = []
        for idx, signer in enumerate(signers, start=1):
            signer_objects.append({
                'email': signer.get('email'),
                'name': signer.get('name'),
                'recipientId': str(idx),
                'routingOrder': str(idx),
                'roleName': signer.get('role', 'Signer'),
                'tabs': {
                    'signHereTabs': [{
                        'anchorString': signer.get('anchor_string', '/s1/'),
                        'anchorUnits': 'pixels',
                        'anchorYOffset': '10',
                        'anchorXOffset': '20'
                    }],
                    'dateSignedTabs': [{
                        'anchorString': signer.get('date_anchor', '/d1/'),
                        'anchorUnits': 'pixels',
                        'anchorYOffset': '10',
                        'anchorXOffset': '20'
                    }]
                }
            })
        
        envelope_definition = {
            'emailSubject': amendment_data.get('email_subject', f"Please sign: Amendment {amendment_data.get('amendment_number')}"),
            'emailBlurb': amendment_data.get('email_body', 'Please review and sign the attached lease amendment.'),
            'status': 'sent',
            'documents': [{
                'documentBase64': pdf_base64,
                'name': amendment_data.get('document_name', f"Amendment_{amendment_data.get('amendment_number')}.pdf"),
                'fileExtension': 'pdf',
                'documentId': '1'
            }],
            'recipients': {
                'signers': signer_objects
            }
        }
        
        return envelope_definition
