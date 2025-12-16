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

    def send_async(self, recipient: str, content: dict, context: dict, record_id: str = None):
        """Send email asynchronously using Celery task."""
        try:
            from notifications.tasks.email_tasks import send_email_task
            send_email_task.delay(self.tenant_id, self.credentials, recipient, content, context, record_id)
            logger.info(f"[Async] Email task dispatched for {recipient}")
            return {'success': True, 'response': 'Email task dispatched'}
        except Exception as e:
            logger.error(f"[Async] Failed to dispatch email task: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_tenant_branding(self, context=None):
        """Get tenant branding information from context or fallback to API"""
        if self.tenant_branding is None:
            # First try to get branding from context (from event payload)
            if context and 'tenant_name' in context:
                self.tenant_branding = {
                    'name': context.get('tenant_name', 'Platform'),
                    'logo_url': context.get('tenant_logo'),
                    'primary_color': context.get('primary_color', '#007bff'),
                    'secondary_color': context.get('secondary_color', '#6c757d'),
                    'email_from': context.get('email_from')
                }
                logger.info(f"Using tenant branding from event payload: {self.tenant_branding['name']}")
            else:
                # Fallback to API call if no context provided
                try:
                    self.tenant_branding = auth_service_client.get_tenant_branding(self.tenant_id)
                    logger.info(f"Using tenant branding from API: {self.tenant_branding['name']}")
                except Exception as e:
                    logger.warning(f"Failed to fetch tenant branding for {self.tenant_id}: {str(e)}")
                    # Use default branding
                    tenant_prefix = str(self.tenant_id)[:8]  # Convert UUID to string first
                    self.tenant_branding = {
                        'name': f'Tenant {tenant_prefix}',
                        'logo_url': None,
                        'primary_color': '#007bff',
                        'secondary_color': '#6c757d',
                        'email_from': f'noreply@{tenant_prefix}.local'
                    }
        return self.tenant_branding

    def _render_content(self, content: dict, context: dict) -> dict:
        """Render email content with context variables"""
        try:
            rendered = {}

            # Render subject and body - handle both single and double curly braces
            for key in ['subject', 'body']:
                if key in content:
                    text = content[key]

                    # Replace double curly braces with single ones for Python formatting
                    for ctx_key, value in context.items():
                        text = text.replace(f'{{{{{ctx_key}}}}}', str(value))
                    # Also handle single curly braces
                    try:
                        text = text.format(**context)
                    except KeyError:
                        pass  # Keep original if formatting fails

                    rendered[key] = text

            return rendered

        except Exception as e:
            logger.error(f"Email content rendering error: {str(e)}")
            return content

    def _render_html_template(self, content: dict, context: dict) -> str:
        """Always render HTML email using Django template system for consistency and testing."""
        from django.template.loader import render_to_string
        # Flatten context if nested under 'template_data'
        if isinstance(context, dict) and 'template_data' in context and isinstance(context['template_data'], dict):
            flat_context = context['template_data'].copy()
            for k, v in context.items():
                if k != 'template_data':
                    flat_context[k] = v
            context = flat_context
        # Use template from content or default to otp_email.html
        template_name = content.get('html_template', 'email/otp_email.html')
        # Ensure all branding/context is present
        branding = self._get_tenant_branding(context)
        context.update({
            'tenant_name': branding['name'],
            'tenant_logo': branding['logo_url'],
            'primary_color': branding['primary_color'],
            'secondary_color': branding['secondary_color'],
            'company_name': branding['name'],
            'logo_url': branding['logo_url']
        })
        return render_to_string(template_name, context)

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

    async def send(self, recipient: str, content: dict, context: dict, record_id: str = None) -> dict:
        from django.core.mail import get_connection
        try:
            branding = self._get_tenant_branding(context)
            logger.info(f"Content before rendering: {content}")
            logger.info(f"Context before rendering: {context}")
            rendered_content = self._render_content(content, context)
            subject = rendered_content.get('subject', '')
            body_text = rendered_content.get('body', '')
            logger.info(f"Rendered content: {rendered_content}")
            logger.info(f"Template context keys: {list(context.keys())}")
            logger.info(f"Code value in context: {context.get('code', 'NOT_FOUND')}")
            logger.info(f"Body template before rendering: {content.get('body', '')[:100]}...")
            logger.info(f"Body after rendering: {body_text[:100]}...")
            context.update({
                'tenant_name': branding['name'],
                'tenant_logo': branding['logo_url'],
                'primary_color': branding['primary_color'],
                'secondary_color': branding['secondary_color'],
                'company_name': branding['name'],
                'logo_url': branding['logo_url']
            })
            html_body = self._render_html_template(content, context)
            creds = self.credentials
            _pwd = creds.get('password', '') or ''
            _pwd_preview = (_pwd[:6] + '...') if len(_pwd) > 6 else _pwd
            _looks_encrypted = str(_pwd).startswith('gAAAA')
            logger.info(f"🔍 DEBUG - Credentials summary - smtp_host={creds.get('smtp_host')}, smtp_port={creds.get('smtp_port')}, username={creds.get('username')}, password_preview={_pwd_preview}, password_len={len(_pwd)}, looks_encrypted={_looks_encrypted}")
            logger.info(f"🔍 DEBUG - Use SSL: {creds.get('use_ssl')}, Use TLS: {creds.get('use_tls')}")
            from_email = creds.get('from_email') or creds.get('username')
            # Always use tenant's from_email or username as from address; do not fall back to settings
            logger.info(f"📧 Sending email for tenant {self.tenant_id}")
            logger.info(f"   From: {from_email}")
            logger.info(f"   To: {recipient}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Content preview: {body_text[:100]}...")
            logger.info(f"   Using SMTP: {creds.get('smtp_host')}:{creds.get('smtp_port')}")
            # Decrypt password if needed
            if isinstance(_pwd, str) and _pwd.startswith('gAAAA'):
                try:
                    from notifications.utils.encryption import decrypt_data
                    _pwd = decrypt_data(_pwd)
                    logger.info(f"🔐 EmailHandler - decrypted tenant password fallback (masked): {_pwd[:6]}...")
                except Exception:
                    logger.warning("🔐 EmailHandler - password looks encrypted but failed to decrypt locally; proceeding with original value")
            # Use get_connection for pooling
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=creds.get('smtp_host'),
                port=creds.get('smtp_port'),
                username=creds.get('username'),
                password=_pwd,
                use_ssl=creds.get('use_ssl', False),
                use_tls=creds.get('use_tls', False),
                timeout=20
            )
            email = EmailMultiAlternatives(
                subject=subject,
                body=body_text,
                from_email=from_email,
                to=[recipient],
                connection=connection
            )
            email.attach_alternative(html_body, "text/html")
            sent = email.send(fail_silently=False)
            if sent:
                logger.info(f"✅ Email sent successfully to {recipient}")
            else:
                logger.warning(f"⚠️ Email send returned 0 for {recipient}")
            if sent:
                return {'success': True, 'response': f'Sent to {sent} recipients'}
            else:
                return {'success': False, 'error': 'Send failed', 'response': None}
        except Exception as e:
            logger.error(f"Email send error for tenant {self.tenant_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}