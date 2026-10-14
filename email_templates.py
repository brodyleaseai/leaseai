from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import config

class EmailTemplates:
    @staticmethod
    def send_abstract_ready_email(client_email: str, property_address: str, lease_id: str):
        message = Mail(
            from_email=config.SENDER_EMAIL,
            to_emails=client_email,
            subject=f'Your Lease Abstract is Ready: {property_address}',
            html_content=f'''
            <html>
            <body>
                <h2>Your Lease Abstract is Ready!</h2>
                <p>The lease abstract for <strong>{property_address}</strong> has been completed.</p>
                <p>Lease ID: {lease_id}</p>
                <p>Log in to your LeaseAI portal to download your abstract.</p>
                <p>Best regards,<br>The LeaseAI Team</p>
            </body>
            </html>
            '''
        )
        
        try:
            sg = SendGridAPIClient(config.SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False