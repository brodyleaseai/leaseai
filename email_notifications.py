"""
Email Notification System for LeaseAI
Automated SendGrid email notifications for lease processing events.
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import config
from datetime import datetime


class EmailNotificationService:
    """Service for sending automated email notifications via SendGrid."""
    
    def __init__(self):
        """Initialize SendGrid client."""
        self.sg_client = None
        if config.SENDGRID_API_KEY and config.SENDGRID_API_KEY != "your-sendgrid-api-key-here":
            try:
                self.sg_client = SendGridAPIClient(config.SENDGRID_API_KEY)
            except Exception as e:
                print(f"⚠️ SendGrid initialization failed: {e}")
    
    def send_lease_approved_email(self, client_email, client_name, lease_data, download_url=None):
        """
        Send email notification when lease is approved and ready for download.
        
        Args:
            client_email: Client's email address
            client_name: Client's name
            lease_data: Dict with lease information (property_address, tenant_name, lease_id)
            download_url: Optional direct download URL
        """
        if not self.sg_client:
            print("⚠️ SendGrid not configured - email not sent")
            return False
        
        try:
            property_address = lease_data.get("property_address", "Your Property")
            tenant_name = lease_data.get("tenant_name", "")
            lease_id = lease_data.get("id", "")
            
            subject = f"✅ Your Lease Abstract is Ready - {property_address}"
            
            # HTML email body
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; 
                              padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                              font-weight: bold; margin: 20px 0; }}
                    .info-box {{ background: white; padding: 20px; border-radius: 6px; 
                                margin: 20px 0; border-left: 4px solid #10b981; }}
                    .footer {{ text-align: center; color: #6b7280; font-size: 12px; 
                              margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📄 {config.APP_NAME}</h1>
                        <p>Your Lease Abstract is Ready!</p>
                    </div>
                    
                    <div class="content">
                        <p>Hi {client_name},</p>
                        
                        <p>Great news! We've completed processing your commercial lease and your abstract is ready for download.</p>
                        
                        <div class="info-box">
                            <h3 style="margin-top: 0; color: #667eea;">📋 Lease Details</h3>
                            <p><strong>Property:</strong> {property_address}</p>
                            <p><strong>Tenant:</strong> {tenant_name}</p>
                            <p><strong>Lease ID:</strong> #{lease_id}</p>
                            <p><strong>Processing Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                        </div>
                        
                        <p><strong>What's Included:</strong></p>
                        <ul>
                            <li>✅ 84+ key lease terms extracted</li>
                            <li>✅ AI confidence scores for every field</li>
                            <li>✅ Expert-reviewed data points</li>
                            <li>✅ Professional PDF abstract</li>
                        </ul>
                        
                        <div style="text-align: center;">
                            <a href="{config.APP_URL}" class="button">
                                📥 Download Your Abstract
                            </a>
                        </div>
                        
                        <p style="margin-top: 30px;">
                            <strong>Next Steps:</strong><br>
                            1. Log in to your LeaseAI portal<br>
                            2. Navigate to "My Leases"<br>
                            3. Click "Download Abstract" next to this lease
                        </p>
                        
                        <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                            Need help or have questions? Reply to this email or contact our support team at 
                            <a href="mailto:support@leaseai.com">support@leaseai.com</a>
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>© 2026 {config.APP_NAME}. All rights reserved.</p>
                        <p>You're receiving this email because you uploaded a lease for processing.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
            Hi {client_name},
            
            Your lease abstract is ready for download!
            
            Property: {property_address}
            Tenant: {tenant_name}
            Lease ID: #{lease_id}
            
            Log in to {config.APP_URL} and navigate to "My Leases" to download your abstract.
            
            Questions? Contact us at support@leaseai.com
            
            - The {config.APP_NAME} Team
            """
            
            # Create message
            message = Mail(
                from_email=Email(config.SENDGRID_FROM_EMAIL, config.COMPANY_NAME),
                to_emails=To(client_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )
            
            # Send email
            response = self.sg_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Email sent to {client_email}")
                return True
            else:
                print(f"⚠️ Email send failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Email error: {str(e)}")
            return False
    
    def send_lease_flagged_email(self, client_email, client_name, lease_data, reason=""):
        """
        Send email notification when lease requires manual attention.
        
        Args:
            client_email: Client's email address
            client_name: Client's name
            lease_data: Dict with lease information
            reason: Optional reason for flagging
        """
        if not self.sg_client:
            print("⚠️ SendGrid not configured - email not sent")
            return False
        
        try:
            property_address = lease_data.get("property_address", "Your Property")
            lease_id = lease_data.get("id", "")
            
            subject = f"⚠️ Your Lease Requires Additional Review - {property_address}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #f59e0b; color: white; padding: 30px; 
                              text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                    .info-box {{ background: white; padding: 20px; border-radius: 6px; 
                                margin: 20px 0; border-left: 4px solid #f59e0b; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📄 {config.APP_NAME}</h1>
                        <p>Lease Requires Manual Review</p>
                    </div>
                    
                    <div class="content">
                        <p>Hi {client_name},</p>
                        
                        <p>Thank you for uploading your lease. Our AI has completed the initial extraction, 
                        but this lease requires additional manual review by our team to ensure accuracy.</p>
                        
                        <div class="info-box">
                            <h3 style="margin-top: 0;">📋 Lease Details</h3>
                            <p><strong>Property:</strong> {property_address}</p>
                            <p><strong>Lease ID:</strong> #{lease_id}</p>
                            {f'<p><strong>Reason:</strong> {reason}</p>' if reason else ''}
                        </div>
                        
                        <p><strong>What happens next:</strong></p>
                        <ul>
                            <li>Our expert team will manually review this lease</li>
                            <li>We'll verify all extracted data for accuracy</li>
                            <li>You'll receive your abstract within 24 hours</li>
                        </ul>
                        
                        <p style="margin-top: 30px; color: #6b7280;">
                            We'll send you another email as soon as your abstract is ready. 
                            If you have any questions, contact us at support@leaseai.com
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=Email(config.SENDGRID_FROM_EMAIL, config.COMPANY_NAME),
                to_emails=To(client_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.sg_client.send(message)
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            print(f"❌ Email error: {str(e)}")
            return False
    
    def send_welcome_email(self, client_email, client_name):
        """Send welcome email to new clients."""
        if not self.sg_client:
            return False
        
        try:
            subject = f"Welcome to {config.APP_NAME}! 🎉"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; 
                              padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                              font-weight: bold; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Welcome to {config.APP_NAME}!</h1>
                    </div>
                    
                    <div class="content">
                        <p>Hi {client_name},</p>
                        
                        <p>Thank you for signing up! You now have access to AI-powered commercial lease abstraction.</p>
                        
                        <p><strong>What you can do:</strong></p>
                        <ul>
                            <li>📤 Upload commercial lease PDFs</li>
                            <li>🤖 Get AI extraction in 5-10 minutes</li>
                            <li>📊 84+ key terms extracted automatically</li>
                            <li>📥 Download professional lease abstracts</li>
                        </ul>
                        
                        <div style="text-align: center;">
                            <a href="{config.APP_URL}" class="button">
                                Get Started Now
                            </a>
                        </div>
                        
                        <p style="margin-top: 30px;">
                            Need help? Check out our <a href="{config.APP_URL}/docs">User Guide</a> or 
                            contact us at support@leaseai.com
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=Email(config.SENDGRID_FROM_EMAIL, config.COMPANY_NAME),
                to_emails=To(client_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.sg_client.send(message)
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            print(f"❌ Email error: {str(e)}")
            return False


# Singleton instance
_email_service = None

def get_email_service():
    """Get or create the email notification service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailNotificationService()
    return _email_service