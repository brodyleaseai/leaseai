"""
Test Email Delivery System
Verify SendGrid configuration and email sending functionality.
"""
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import config

def test_sendgrid_config():
    """Test if SendGrid is properly configured."""
    print("🔍 Testing SendGrid Configuration...\n")
    
    # Check API Key
    if not config.SENDGRID_API_KEY or config.SENDGRID_API_KEY == "your-sendgrid-key-here":
        print("❌ SENDGRID_API_KEY not configured")
        print("   Please update config.py or set environment variable SENDGRID_API_KEY")
        return False
    else:
        print(f"✅ SENDGRID_API_KEY configured (length: {len(config.SENDGRID_API_KEY)})")
    
    # Check From Email
    if not config.SENDGRID_FROM_EMAIL:
        print("❌ SENDGRID_FROM_EMAIL not configured")
        return False
    else:
        print(f"✅ SENDGRID_FROM_EMAIL: {config.SENDGRID_FROM_EMAIL}")
    
    return True


def send_test_email(recipient_email: str):
    """
    Send a test email to verify SendGrid is working.
    
    Args:
        recipient_email: Email address to send test to
    """
    print(f"\n📧 Sending test email to: {recipient_email}")
    
    try:
        message = Mail(
            from_email=config.SENDGRID_FROM_EMAIL,
            to_emails=recipient_email,
            subject='🧪 LeaseAI Email Test',
            html_content=f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #667eea;">LeaseAI Email Test</h2>
                <p>This is a test email from your LeaseAI application.</p>
                
                <div style="background: #f0f4ff; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0;">
                    <strong>✅ SendGrid Configuration Successful!</strong><br>
                    Your email delivery system is working correctly.
                </div>
                
                <p><strong>Configuration Details:</strong></p>
                <ul>
                    <li>From Email: {config.SENDGRID_FROM_EMAIL}</li>
                    <li>Company: {config.COMPANY_NAME}</li>
                    <li>Location: {config.COMPANY_LOCATION}</li>
                </ul>
                
                <p>You can now receive automated lease notifications!</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    Automated test from {config.APP_NAME}
                </p>
            </body>
            </html>
            """
        )
        
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ Email sent successfully!")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.body}")
        print(f"   Response Headers: {response.headers}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        print("\n🔧 Common Issues:")
        print("   1. Invalid API key")
        print("   2. Sender email not verified in SendGrid")
        print("   3. SendGrid account suspended or not activated")
        print("   4. Network/firewall blocking outbound SMTP")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("LeaseAI Email Delivery Test")
    print("=" * 60)
    
    # Test configuration
    if not test_sendgrid_config():
        print("\n⚠️  Please configure SendGrid before testing email delivery")
        print("\n📖 Setup Instructions:")
        print("   1. Sign up for SendGrid: https://signup.sendgrid.com/")
        print("   2. Verify your sender email address")
        print("   3. Create an API key with 'Mail Send' permissions")
        print("   4. Update config.py with your API key")
        sys.exit(1)
    
    # Get recipient email
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = input("\n📧 Enter recipient email address for test: ")
    
    # Send test email
    success = send_test_email(recipient)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ EMAIL SYSTEM IS WORKING!")
        print("=" * 60)
        print("\nNext steps:")
        print("  • Automatic emails will be sent when leases are approved")
        print("  • Check your inbox for the test email")
        print("  • Add recipient to your SendGrid verified senders if needed")
    else:
        print("\n" + "=" * 60)
        print("❌ EMAIL SYSTEM NEEDS ATTENTION")
        print("=" * 60)
        print("\nPlease review the error messages above and fix the issues.")
    
    print("\n")
