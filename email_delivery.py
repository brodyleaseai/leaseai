"""
Email Delivery Module for LeaseAI
Handles SendGrid email delivery with PDF attachments.
"""
import base64
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import config
from lease_report import generate_lease_abstract_pdf


def send_upload_confirmation_email(
    recipient_email: str,
    recipient_name: str,
    property_address: str,
    lease_id: int
) -> bool:
    """
    Send confirmation email when client uploads a lease.
    
    Args:
        recipient_email: Client email address
        recipient_name: Client name
        property_address: Property address
        lease_id: Lease ID for reference
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Create email content
    subject = f"✅ Lease Upload Confirmed - {property_address}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">📄 {config.APP_NAME}</h1>
                <h2 style="margin: 10px 0 0 0; font-weight: normal;">Upload Confirmed!</h2>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
                <p>Hi {recipient_name},</p>
                
                <p>We've successfully received your commercial lease document and our AI is now extracting the key terms.</p>
                
                <div style="background: #E3F2FD; padding: 15px; border-left: 4px solid #1976D2; margin: 20px 0;">
                    <strong>Property:</strong> {property_address}<br>
                    <strong>Lease ID:</strong> #{lease_id}<br>
                    <strong>Status:</strong> Processing
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #667eea;">⏱️ What Happens Next?</h3>
                    <ol style="margin: 0; padding-left: 20px;">
                        <li><strong>AI Extraction (Minutes):</strong> GPT-4 extracts 84+ lease terms automatically</li>
                        <li><strong>Expert Review (24 hours):</strong> Our team verifies accuracy and confidence scores</li>
                        <li><strong>Email Notification:</strong> You'll receive an email when your abstract is ready</li>
                        <li><strong>Download:</strong> Access your professional PDF abstract in your client portal</li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{config.APP_URL}" style="display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        View Progress in Portal
                    </a>
                </div>
                
                <p>We'll send you another email as soon as your lease abstract is ready for download (typically within 24 hours).</p>
                
                <p>If you have any questions, please don't hesitate to reach out.</p>
                
                <p>Best regards,<br>
                <strong>{config.SENDER_NAME}</strong><br>
                {config.COMPANY_NAME}<br>
                {config.COMPANY_LOCATION}</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from {config.APP_NAME}. 
                    Please do not reply directly to this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Upload Confirmed!
    
    Hi {recipient_name},
    
    We've successfully received your commercial lease document and our AI is now extracting the key terms.
    
    Property: {property_address}
    Lease ID: #{lease_id}
    Status: Processing
    
    What Happens Next?
    1. AI Extraction (Minutes): GPT-4 extracts 84+ lease terms automatically
    2. Expert Review (24 hours): Our team verifies accuracy and confidence scores
    3. Email Notification: You'll receive an email when your abstract is ready
    4. Download: Access your professional PDF abstract in your client portal
    
    We'll send you another email as soon as your lease abstract is ready for download (typically within 24 hours).
    
    View your progress at: {config.APP_URL}
    
    Best regards,
    {config.SENDER_NAME}
    {config.COMPANY_NAME}
    {config.COMPANY_LOCATION}
    
    ---
    This is an automated message from {config.APP_NAME}. 
    Please do not reply directly to this email.
    """
    
    # Create SendGrid message
    message = Mail(
        from_email=(config.SENDER_EMAIL, config.SENDER_NAME),
        to_emails=recipient_email,
        subject=subject,
        plain_text_content=plain_content,
        html_content=html_content
    )
    
    # Send via SendGrid
    try:
        if not config.SENDGRID_API_KEY or config.SENDGRID_API_KEY == "your-sendgrid-key-here":
            print("⚠️ SendGrid not configured - skipping upload confirmation email")
            return False
            
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Upload confirmation email sent to {recipient_email}")
            return True
        else:
            print(f"⚠️ SendGrid returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send upload confirmation email: {str(e)}")
        return False


def send_lease_abstract_email(
    recipient_email: str,
    recipient_name: str,
    property_address: str,
    tenant_name: str,
    pdf_bytes: bytes,
    lease_id: int
) -> bool:
    """
    Send lease abstract PDF via SendGrid.
    
    Args:
        recipient_email: Client email address
        recipient_name: Client name
        property_address: Property address for email context
        tenant_name: Tenant name for email context
        pdf_bytes: PDF file content as bytes
        lease_id: Lease ID for reference
    
    Returns:
        True if email sent successfully, False otherwise
    """
    # Create email content
    subject = f"Lease Abstract Ready - {property_address}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1976D2;">Your Lease Abstract is Ready</h2>
            
            <p>Dear {recipient_name},</p>
            
            <p>Your commercial lease abstract has been completed and is attached to this email.</p>
            
            <div style="background-color: #E3F2FD; padding: 15px; border-left: 4px solid #1976D2; margin: 20px 0;">
                <strong>Property:</strong> {property_address}<br>
                <strong>Tenant:</strong> {tenant_name}<br>
                <strong>Lease ID:</strong> #{lease_id}
            </div>
            
            <p>The attached PDF contains a comprehensive abstract of your lease with all key terms extracted and organized for easy reference.</p>
            
            <p>If you have any questions or need clarification on any extracted data, please don't hesitate to reach out.</p>
            
            <p>Best regards,<br>
            <strong>{config.SENDER_NAME}</strong><br>
            {config.COMPANY_NAME}<br>
            {config.COMPANY_LOCATION}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #666;">
                This is an automated message from {config.APP_NAME}. 
                Please do not reply directly to this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Your Lease Abstract is Ready
    
    Dear {recipient_name},
    
    Your commercial lease abstract has been completed and is attached to this email.
    
    Property: {property_address}
    Tenant: {tenant_name}
    Lease ID: #{lease_id}
    
    The attached PDF contains a comprehensive abstract of your lease with all key terms extracted and organized for easy reference.
    
    If you have any questions or need clarification on any extracted data, please don't hesitate to reach out.
    
    Best regards,
    {config.SENDER_NAME}
    {config.COMPANY_NAME}
    {config.COMPANY_LOCATION}
    
    ---
    This is an automated message from {config.APP_NAME}. 
    Please do not reply directly to this email.
    """
    
    # Create SendGrid message
    message = Mail(
        from_email=(config.SENDER_EMAIL, config.SENDER_NAME),
        to_emails=recipient_email,
        subject=subject,
        plain_text_content=plain_content,
        html_content=html_content
    )
    
    # Attach PDF
    encoded_pdf = base64.b64encode(pdf_bytes).decode()
    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName(f"LeaseAbstract_{lease_id}_{property_address.replace(' ', '_')}.pdf"),
        FileType("application/pdf"),
        Disposition("attachment")
    )
    message.attachment = attachment
    
    # Send via SendGrid
    try:
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            return True
        else:
            print(f"SendGrid error: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def send_critical_date_reminder(
    client_email: str,
    client_name: str,
    date_type: str,
    date_value: str,
    days_until: int,
    property_address: str,
    lease_id: int,
    description: str = None
) -> bool:
    """
    Send critical date reminder email to client.
    
    Args:
        client_email: Client email address
        client_name: Client name
        date_type: Type of critical date
        date_value: Date in YYYY-MM-DD format
        days_until: Number of days until the date
        property_address: Property address
        lease_id: Lease ID
        description: Optional description
    
    Returns:
        True if email sent successfully
    """
    # Determine urgency level
    if days_until <= 7:
        urgency_color = "#dc2626"  # Red
        urgency_label = "URGENT"
        urgency_icon = "🔴"
    elif days_until <= 14:
        urgency_color = "#ea580c"  # Orange
        urgency_label = "HIGH PRIORITY"
        urgency_icon = "🟠"
    elif days_until <= 30:
        urgency_color = "#f59e0b"  # Amber
        urgency_label = "ATTENTION NEEDED"
        urgency_icon = "🟡"
    else:
        urgency_color = "#3b82f6"  # Blue
        urgency_label = "UPCOMING"
        urgency_icon = "🔵"
    
    # Format the date nicely
    from datetime import datetime
    date_obj = datetime.strptime(date_value, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%B %d, %Y")
    
    subject = f"{urgency_icon} {date_type} in {days_until} days - {property_address}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: {urgency_color}; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 2rem;">{urgency_icon} {urgency_label}</h1>
                <h2 style="margin: 10px 0 0 0; font-weight: normal;">{date_type} Reminder</h2>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
                <p>Dear {client_name},</p>
                
                <p>This is a reminder that an important date for your commercial lease is approaching:</p>
                
                <div style="background: #fef3c7; border-left: 4px solid {urgency_color}; padding: 20px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: {urgency_color};">📅 {date_type}</h3>
                    <p style="margin: 10px 0;"><strong>Date:</strong> {formatted_date}</p>
                    <p style="margin: 10px 0;"><strong>Days Until:</strong> {days_until} days</p>
                    <p style="margin: 10px 0;"><strong>Property:</strong> {property_address}</p>
                    <p style="margin: 10px 0;"><strong>Lease ID:</strong> #{lease_id}</p>
                    {f'<p style="margin: 10px 0;"><strong>Details:</strong> {description}</p>' if description else ''}
                </div>
                
                <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0369a1;">💡 Recommended Actions:</h3>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Review your lease terms and obligations related to this date</li>
                        <li>Consult with your legal or real estate team if needed</li>
                        <li>Prepare any required documentation or notices</li>
                        <li>Contact your landlord or property manager if applicable</li>
                        <li>Mark this date on your calendar with appropriate lead time</li>
                    </ul>
                </div>
                
                <p><strong>Why This Matters:</strong></p>
                <p>Missing critical lease dates can result in:</p>
                <ul>
                    <li>Automatic lease renewals on unfavorable terms</li>
                    <li>Loss of renewal or termination options</li>
                    <li>Financial penalties or increased costs</li>
                    <li>Legal complications or default</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{config.APP_URL}" style="display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        View Lease Details
                    </a>
                </div>
                
                <p>If you have any questions or need assistance with this date, please don't hesitate to contact us.</p>
                
                <p>Best regards,<br>
                <strong>{config.SENDER_NAME}</strong><br>
                {config.COMPANY_NAME}<br>
                {config.COMPANY_LOCATION}</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    This is an automated reminder from {config.APP_NAME}. 
                    You can manage your notification preferences in your client portal.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    {urgency_label}: {date_type} Reminder
    
    Dear {client_name},
    
    This is a reminder that an important date for your commercial lease is approaching:
    
    {date_type}
    Date: {formatted_date}
    Days Until: {days_until} days
    Property: {property_address}
    Lease ID: #{lease_id}
    {f'Details: {description}' if description else ''}
    
    Recommended Actions:
    - Review your lease terms and obligations related to this date
    - Consult with your legal or real estate team if needed
    - Prepare any required documentation or notices
    - Contact your landlord or property manager if applicable
    - Mark this date on your calendar with appropriate lead time
    
    Why This Matters:
    Missing critical lease dates can result in automatic lease renewals on unfavorable terms, 
    loss of renewal or termination options, financial penalties, or legal complications.
    
    View your lease details at: {config.APP_URL}
    
    If you have any questions, please contact us.
    
    Best regards,
    {config.SENDER_NAME}
    {config.COMPANY_NAME}
    {config.COMPANY_LOCATION}
    
    ---
    This is an automated reminder from {config.APP_NAME}.
    """
    
    # Create SendGrid message
    message = Mail(
        from_email=(config.SENDER_EMAIL, config.SENDER_NAME),
        to_emails=client_email,
        subject=subject,
        plain_text_content=plain_content,
        html_content=html_content
    )
    
    # Send via SendGrid
    try:
        if not config.SENDGRID_API_KEY or config.SENDGRID_API_KEY == "your-sendgrid-key-here":
            print("⚠️ SendGrid not configured - skipping critical date reminder")
            return False
            
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Critical date reminder sent to {client_email} for {date_type}")
            return True
        else:
            print(f"⚠️ SendGrid returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send critical date reminder: {str(e)}")
        return False


def trigger_delivery_email(lease_id: int, supabase_client) -> tuple[bool, str]:
    """
    Fetch lease data, generate PDF, and send email to client.
    
    Args:
        lease_id: ID of the lease to deliver
        supabase_client: Supabase client instance
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Fetch lease details
        lease_response = supabase_client.table("leases").select("*").eq("id", lease_id).single().execute()
        lease_data = lease_response.data
        
        if not lease_data:
            return False, "Lease not found"
        
        # Fetch client details
        client_id = lease_data.get("client_id")
        if not client_id:
            return False, "No client associated with this lease"
        
        client_response = supabase_client.table("clients").select("*").eq("id", client_id).single().execute()
        client_data = client_response.data
        
        if not client_data:
            return False, "Client not found"
        
        # Fetch extracted fields
        extracted_fields = lease_data.get("extracted_data", {})
        
        # Generate PDF
        pdf_bytes = generate_lease_abstract_pdf(lease_data, extracted_fields)
        
        # Send email
        success = send_lease_abstract_email(
            recipient_email=client_data.get("email"),
            recipient_name=client_data.get("company_name", "Client"),
            property_address=lease_data.get("property_address", "N/A"),
            tenant_name=lease_data.get("tenant_name", "N/A"),
            pdf_bytes=pdf_bytes,
            lease_id=lease_id
        )
        
        if success:
            return True, f"✅ Email delivered to {client_data.get('email')}"
        else:
            return False, "Failed to send email via SendGrid"
            
    except Exception as e:
        return False, f"Error: {str(e)}"
