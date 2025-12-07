from .base_handler import BaseHandler
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from notifications.services.auth_service import auth_service_client
import logging

logger = logging.getLogger('notifications.channels.email')

class EmailHandler(BaseHandler):
    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)
        self.tenant_branding = None

    def _get_tenant_branding(self):
        """Get tenant branding information"""
        if self.tenant_branding is None:
            self.tenant_branding = auth_service_client.get_tenant_branding(self.tenant_id)
        return self.tenant_branding

    def _render_html_template(self, content: dict, context: dict) -> str:
        """Render HTML email template with tenant branding"""
        branding = self._get_tenant_branding()

        # Update context with branding
        context.update({
            'tenant_name': branding['name'],
            'tenant_logo': branding['logo_url'],
            'primary_color': branding['primary_color'],
            'secondary_color': branding['secondary_color'],
            'company_name': branding['name'],  # Alias for backward compatibility
            'logo_url': branding['logo_url']
        })

        subject = content.get('subject', '').format(**context)
        body_text = content.get('body', '').format(**context)

        # Create HTML version with branding
        html_body = self._create_html_email(subject, body_text, branding, context)

        return html_body

    def _create_html_email(self, subject: str, body_text: str, branding: dict, context: dict) -> str:
        """Create HTML email with tenant branding"""
        logo_html = ""
        if branding.get('logo_url'):
            logo_html = f'<img src="{branding["logo_url"]}" alt="{branding["name"]} Logo" style="max-width: 200px; height: auto;">'

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{subject}}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #f4f4f4;
                }}
                .email-container {{
                    background-color: white;
                    margin: 20px;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    padding-bottom: 30px;
                    border-bottom: 3px solid {branding['primary_color']};
                }}
                .logo {{
                    max-width: 200px;
                    height: auto;
                }}
                .content {{
                    padding: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: {branding['primary_color']};
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .button:hover {{
                    background-color: {branding['secondary_color']};
                    color: #333;
                }}
                .highlight {{
                    color: {branding['primary_color']};
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    {logo_html}
                    <h1 style="color: {branding['primary_color']}; margin: 20px 0 0 0;">{branding['name']}</h1>
                </div>

                <div class="content">
                    {body_text.replace(chr(10), '<br>')}
                </div>

                <div class="footer">
                    <p>This email was sent by {branding['name']}</p>
                    {f'<p>{branding.get("about_us", "")[:100]}...</p>' if branding.get('about_us') else ''}
                    <p><small>If you have any questions, please contact our support team.</small></p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    async def send(self, recipient: str, content: dict, context: dict) -> dict:
        try:
            # Get tenant branding
            branding = self._get_tenant_branding()

            # Render subject and text body
            subject = content.get('subject', '').format(**context)
            body_text = content.get('body', '').format(**context)

            # Add branding to context
            context.update({
                'tenant_name': branding['name'],
                'tenant_logo': branding['logo_url'],
                'primary_color': branding['primary_color'],
                'secondary_color': branding['secondary_color'],
                'company_name': branding['name'],
                'logo_url': branding['logo_url']
            })

            # Create HTML version
            html_body = self._render_html_template(content, context)

            # Determine from email
            from_email = self.credentials.get('from_email') or branding.get('email_from') or settings.DEFAULT_FROM_EMAIL

            # Send email with both text and HTML versions
            email = EmailMultiAlternatives(
                subject=subject,
                body=body_text,
                from_email=from_email,
                to=[recipient]
            )

            # Attach HTML version
            email.attach_alternative(html_body, "text/html")

            # Send the email
            sent = email.send(fail_silently=False)

            if sent:
                return {'success': True, 'response': f'Sent to {sent} recipients'}
            else:
                return {'success': False, 'error': 'Send failed', 'response': None}

        except Exception as e:
            logger.error(f"Email send error for tenant {self.tenant_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}