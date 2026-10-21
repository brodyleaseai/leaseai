"""
LeaseAI - Notifications Integration
Phase 7: Native API Integrations

Integration for sending notifications via Slack and Microsoft Teams webhooks.
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


class SlackNotifier(BaseIntegration):
    """
    Slack Webhook Notifications
    
    Provides:
    - Send formatted notifications to Slack channels
    - Lease expiration alerts
    - CAM reconciliation completion notices
    - Anomaly detection alerts
    - Amendment signature reminders
    
    Required config:
    - webhook_url: Slack webhook URL
    - channel: Default Slack channel (optional)
    - username: Bot username (optional)
    - icon_emoji: Bot icon (optional, default :office:)
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        super().__init__(client_id, config)
        
        self.webhook_url = config.get('webhook_url')
        self.default_channel = config.get('channel')
        self.username = config.get('username', 'LeaseAI Bot')
        self.icon_emoji = config.get('icon_emoji', ':office:')
    
    def _get_integration_type(self) -> IntegrationType:
        return IntegrationType.SLACK
    
    def authenticate(self) -> bool:
        """Validate webhook URL"""
        if self.webhook_url and self.webhook_url.startswith('https://hooks.slack.com/'):
            self.authenticated = True
            print(f"✅ Slack webhook configured")
            return True
        else:
            print(f"❌ Invalid Slack webhook URL")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Slack webhook by sending a test message"""
        try:
            self.ensure_authenticated()
            
            result = self.send_notification(
                title="LeaseAI Connection Test",
                message="Successfully connected to Slack! 🎉",
                color="good"
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Test message sent to Slack successfully'
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to send test message')
                }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }
    
    def send_notification(
        self,
        title: str,
        message: str,
        color: str = "#36a64f",
        fields: Optional[List[Dict[str, Any]]] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to Slack
        
        Args:
            title: Notification title
            message: Main message text
            color: Attachment color (good/warning/danger or hex)
            fields: Additional fields to display
            channel: Override default channel
            
        Returns:
            Dict with 'success' and 'message'
        """
        try:
            self.ensure_authenticated()
            
            payload = {
                'username': self.username,
                'icon_emoji': self.icon_emoji,
                'attachments': [{
                    'color': color,
                    'title': title,
                    'text': message,
                    'footer': 'LeaseAI',
                    'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            # Add channel override
            if channel or self.default_channel:
                payload['channel'] = channel or self.default_channel
            
            # Add fields if provided
            if fields:
                payload['attachments'][0]['fields'] = fields
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            
            self.log_sync(
                action='send_notification',
                status=IntegrationStatus.SUCCESS,
                record_count=1,
                details={'title': title}
            )
            
            return {
                'success': True,
                'message': 'Notification sent successfully'
            }
        
        except Exception as e:
            self.log_sync(
                action='send_notification',
                status=IntegrationStatus.FAILED,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'message': f'Failed to send notification: {str(e)}'
            }
    
    def notify_lease_expiration(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send lease expiration alert"""
        
        days_until_expiry = lease_data.get('days_until_expiry', 0)
        
        if days_until_expiry <= 30:
            color = 'danger'
            urgency = 'URGENT'
        elif days_until_expiry <= 90:
            color = 'warning'
            urgency = 'ATTENTION NEEDED'
        else:
            color = 'good'
            urgency = 'FYI'
        
        fields = [
            {
                'title': 'Tenant',
                'value': lease_data.get('tenant_name', 'N/A'),
                'short': True
            },
            {
                'title': 'Unit',
                'value': lease_data.get('unit_number', 'N/A'),
                'short': True
            },
            {
                'title': 'Expiration Date',
                'value': format_date(lease_data.get('expiration_date')),
                'short': True
            },
            {
                'title': 'Days Until Expiry',
                'value': f"{days_until_expiry} days",
                'short': True
            }
        ]
        
        return self.send_notification(
            title=f"🚨 {urgency}: Lease Expiring Soon",
            message=f"Lease for {lease_data.get('tenant_name')} expires in {days_until_expiry} days",
            color=color,
            fields=fields
        )
    
    def notify_cam_completion(self, reconciliation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send CAM reconciliation completion notice"""
        
        fields = [
            {
                'title': 'Property',
                'value': reconciliation_data.get('property_name', 'N/A'),
                'short': True
            },
            {
                'title': 'Period',
                'value': reconciliation_data.get('period', 'N/A'),
                'short': True
            },
            {
                'title': 'Total Expenses',
                'value': format_currency(reconciliation_data.get('total_expenses', 0)),
                'short': True
            },
            {
                'title': 'Total Recoveries',
                'value': format_currency(reconciliation_data.get('total_recoveries', 0)),
                'short': True
            }
        ]
        
        return self.send_notification(
            title="✅ CAM Reconciliation Completed",
            message=f"CAM reconciliation for {reconciliation_data.get('property_name')} has been completed",
            color="good",
            fields=fields
        )
    
    def notify_anomaly_detected(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send anomaly detection alert"""
        
        severity = anomaly_data.get('severity', 'medium')
        
        color_map = {
            'critical': 'danger',
            'high': 'danger',
            'medium': 'warning',
            'low': 'good'
        }
        
        fields = [
            {
                'title': 'Anomaly Type',
                'value': anomaly_data.get('anomaly_type', 'Unknown'),
                'short': True
            },
            {
                'title': 'Severity',
                'value': severity.upper(),
                'short': True
            },
            {
                'title': 'Lease/Property',
                'value': anomaly_data.get('lease_identifier', 'N/A'),
                'short': True
            },
            {
                'title': 'Detection Time',
                'value': format_date(datetime.now()),
                'short': True
            }
        ]
        
        return self.send_notification(
            title=f"⚠️ Anomaly Detected: {anomaly_data.get('anomaly_type')}",
            message=anomaly_data.get('description', 'An anomaly was detected in lease data'),
            color=color_map.get(severity, 'warning'),
            fields=fields
        )


class TeamsNotifier(BaseIntegration):
    """
    Microsoft Teams Webhook Notifications
    
    Provides:
    - Send formatted notifications to Teams channels
    - Lease expiration alerts
    - CAM reconciliation completion notices
    - Anomaly detection alerts
    - Amendment signature reminders
    
    Required config:
    - webhook_url: Teams webhook URL
    """
    
    def __init__(self, client_id: str, config: Dict[str, Any]):
        super().__init__(client_id, config)
        
        self.webhook_url = config.get('webhook_url')
    
    def _get_integration_type(self) -> IntegrationType:
        return IntegrationType.TEAMS
    
    def authenticate(self) -> bool:
        """Validate webhook URL"""
        if self.webhook_url and 'webhook.office.com' in self.webhook_url:
            self.authenticated = True
            print(f"✅ Teams webhook configured")
            return True
        else:
            print(f"❌ Invalid Teams webhook URL")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Teams webhook by sending a test message"""
        try:
            self.ensure_authenticated()
            
            result = self.send_notification(
                title="LeaseAI Connection Test",
                message="Successfully connected to Microsoft Teams!",
                theme_color="00FF00"
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Test message sent to Teams successfully'
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Failed to send test message')
                }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Connection test failed: {str(e)}"
            }
    
    def send_notification(
        self,
        title: str,
        message: str,
        theme_color: str = "0076D7",
        sections: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send notification to Teams using Adaptive Cards
        
        Args:
            title: Notification title
            message: Main message text
            theme_color: Card theme color (hex without #)
            sections: Additional sections to display
            
        Returns:
            Dict with 'success' and 'message'
        """
        try:
            self.ensure_authenticated()
            
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": theme_color,
                "title": title,
                "sections": [{
                    "activityTitle": "LeaseAI",
                    "activitySubtitle": format_date(datetime.now()),
                    "text": message
                }]
            }
            
            # Add additional sections if provided
            if sections:
                payload['sections'].extend(sections)
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            
            self.log_sync(
                action='send_notification',
                status=IntegrationStatus.SUCCESS,
                record_count=1,
                details={'title': title}
            )
            
            return {
                'success': True,
                'message': 'Notification sent successfully'
            }
        
        except Exception as e:
            self.log_sync(
                action='send_notification',
                status=IntegrationStatus.FAILED,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'message': f'Failed to send notification: {str(e)}'
            }
    
    def notify_lease_expiration(self, lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send lease expiration alert"""
        
        days_until_expiry = lease_data.get('days_until_expiry', 0)
        
        if days_until_expiry <= 30:
            theme_color = "FF0000"
            urgency = 'URGENT'
        elif days_until_expiry <= 90:
            theme_color = "FFA500"
            urgency = 'ATTENTION NEEDED'
        else:
            theme_color = "00FF00"
            urgency = 'FYI'
        
        facts = [
            {"name": "Tenant", "value": lease_data.get('tenant_name', 'N/A')},
            {"name": "Unit", "value": lease_data.get('unit_number', 'N/A')},
            {"name": "Expiration Date", "value": format_date(lease_data.get('expiration_date'))},
            {"name": "Days Until Expiry", "value": f"{days_until_expiry} days"}
        ]
        
        sections = [{
            "facts": facts
        }]
        
        return self.send_notification(
            title=f"🚨 {urgency}: Lease Expiring Soon",
            message=f"Lease for {lease_data.get('tenant_name')} expires in {days_until_expiry} days",
            theme_color=theme_color,
            sections=sections
        )
    
    def notify_cam_completion(self, reconciliation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send CAM reconciliation completion notice"""
        
        facts = [
            {"name": "Property", "value": reconciliation_data.get('property_name', 'N/A')},
            {"name": "Period", "value": reconciliation_data.get('period', 'N/A')},
            {"name": "Total Expenses", "value": format_currency(reconciliation_data.get('total_expenses', 0))},
            {"name": "Total Recoveries", "value": format_currency(reconciliation_data.get('total_recoveries', 0))}
        ]
        
        sections = [{
            "facts": facts
        }]
        
        return self.send_notification(
            title="✅ CAM Reconciliation Completed",
            message=f"CAM reconciliation for {reconciliation_data.get('property_name')} has been completed",
            theme_color="00FF00",
            sections=sections
        )
    
    def notify_anomaly_detected(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send anomaly detection alert"""
        
        severity = anomaly_data.get('severity', 'medium')
        
        color_map = {
            'critical': 'FF0000',
            'high': 'FF0000',
            'medium': 'FFA500',
            'low': '00FF00'
        }
        
        facts = [
            {"name": "Anomaly Type", "value": anomaly_data.get('anomaly_type', 'Unknown')},
            {"name": "Severity", "value": severity.upper()},
            {"name": "Lease/Property", "value": anomaly_data.get('lease_identifier', 'N/A')},
            {"name": "Detection Time", "value": format_date(datetime.now())}
        ]
        
        sections = [{
            "facts": facts
        }]
        
        return self.send_notification(
            title=f"⚠️ Anomaly Detected: {anomaly_data.get('anomaly_type')}",
            message=anomaly_data.get('description', 'An anomaly was detected in lease data'),
            theme_color=color_map.get(severity, 'FFA500'),
            sections=sections
        )
