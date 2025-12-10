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

        rendered = self._render_content(content, context)
        subject = rendered.get('subject', '')
        body_text = rendered.get('body', '')

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

    async def send(self, recipient: str, content: dict, context: dict, record_id: str = None) -> dict:
        try:
            # Get tenant branding (prefer from context, fallback to API)
            branding = self._get_tenant_branding(context)

            # Render subject and text body
            logger.info(f"Content before rendering: {content}")
            logger.info(f"Context before rendering: {context}")
            rendered_content = self._render_content(content, context)
            subject = rendered_content.get('subject', '')
            body_text = rendered_content.get('body', '')
            logger.info(f"Rendered content: {rendered_content}")

            # Debug logging
            logger.info(f"Template context keys: {list(context.keys())}")
            logger.info(f"Code value in context: {context.get('code', 'NOT_FOUND')}")
            logger.info(f"Body template before rendering: {content.get('body', '')[:100]}...")
            logger.info(f"Body after rendering: {body_text[:100]}...")

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

            # Use credentials (already decrypted by validator)
            creds = self.credentials

            # DEBUG: Log a masked credentials summary (do NOT log plaintext passwords)
            _pwd = creds.get('password', '') or ''
            _pwd_preview = (_pwd[:6] + '...') if len(_pwd) > 6 else _pwd
            _looks_encrypted = str(_pwd).startswith('gAAAA')
            logger.info(f"🔍 DEBUG - Credentials summary - smtp_host={creds.get('smtp_host')}, smtp_port={creds.get('smtp_port')}, username={creds.get('username')}, password_preview={_pwd_preview}, password_len={len(_pwd)}, looks_encrypted={_looks_encrypted}")
            logger.info(f"🔍 DEBUG - Use SSL: {creds.get('use_ssl')}, Use TLS: {creds.get('use_tls')}")

            # Determine from email
            from_email = creds.get('from_email') or branding.get('email_from') or settings.DEFAULT_FROM_EMAIL

            # Log email details before sending
            logger.info(f"📧 Sending email for tenant {self.tenant_id}")
            logger.info(f"   From: {from_email}")
            logger.info(f"   To: {recipient}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Content preview: {body_text[:100]}...")
            logger.info(f"   Using SMTP: {creds.get('smtp_host')}:{creds.get('smtp_port')}")

            # Temporarily override Django's email settings for this tenant
            from django.conf import settings as django_settings
            original_backend = getattr(django_settings, 'EMAIL_BACKEND', None)
            original_host = getattr(django_settings, 'EMAIL_HOST', None)
            original_port = getattr(django_settings, 'EMAIL_PORT', None)
            original_user = getattr(django_settings, 'EMAIL_HOST_USER', None)
            original_pass = getattr(django_settings, 'EMAIL_HOST_PASSWORD', None)
            original_ssl = getattr(django_settings, 'EMAIL_USE_SSL', None)
            original_tls = getattr(django_settings, 'EMAIL_USE_TLS', None)

            try:
                # Override Django settings with tenant credentials
                django_settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
                django_settings.EMAIL_HOST = creds.get('smtp_host')
                django_settings.EMAIL_PORT = creds.get('smtp_port')
                django_settings.EMAIL_HOST_USER = creds.get('username')
                # If the password looks like a Fernet token (starts with gAAAA), attempt to decrypt as a fallback.
                _pwd = creds.get('password') or ''
                if isinstance(_pwd, str) and _pwd.startswith('gAAAA'):
                    try:
                        from notifications.utils.encryption import decrypt_data
                        _decrypted = decrypt_data(_pwd)
                        django_settings.EMAIL_HOST_PASSWORD = _decrypted
                        logger.info(f"🔐 EmailHandler - decrypted tenant password fallback (masked): {_decrypted[:6]}...")
                    except Exception:
                        # If decrypt fails, keep original and let send fail with clear error
                        django_settings.EMAIL_HOST_PASSWORD = _pwd
                        logger.warning("🔐 EmailHandler - password looks encrypted but failed to decrypt locally; proceeding with original value")
                else:
                    django_settings.EMAIL_HOST_PASSWORD = _pwd
                django_settings.EMAIL_USE_SSL = creds.get('use_ssl', False)
                django_settings.EMAIL_USE_TLS = creds.get('use_tls', False)

                # DEBUG: Log Django settings being used
                logger.info(f"🔧 Django EMAIL_HOST: {django_settings.EMAIL_HOST}")
                logger.info(f"🔧 Django EMAIL_PORT: {django_settings.EMAIL_PORT}")
                logger.info(f"🔧 Django EMAIL_HOST_USER: {django_settings.EMAIL_HOST_USER}")
                logger.info(f"🔧 Django EMAIL_USE_SSL: {django_settings.EMAIL_USE_SSL}")
                logger.info(f"🔧 Django EMAIL_USE_TLS: {django_settings.EMAIL_USE_TLS}")

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
                    logger.info(f"✅ Email sent successfully to {recipient}")
                else:
                    logger.warning(f"⚠️ Email send returned 0 for {recipient}")

                if sent:
                    return {'success': True, 'response': f'Sent to {sent} recipients'}
                else:
                    return {'success': False, 'error': 'Send failed', 'response': None}

            finally:
                # Restore original Django email settings
                if original_backend is not None:
                    django_settings.EMAIL_BACKEND = original_backend
                if original_host is not None:
                    django_settings.EMAIL_HOST = original_host
                if original_port is not None:
                    django_settings.EMAIL_PORT = original_port
                if original_user is not None:
                    django_settings.EMAIL_HOST_USER = original_user
                if original_pass is not None:
                    django_settings.EMAIL_HOST_PASSWORD = original_pass
                if original_ssl is not None:
                    django_settings.EMAIL_USE_SSL = original_ssl
                if original_tls is not None:
                    django_settings.EMAIL_USE_TLS = original_tls

        except Exception as e:
            logger.error(f"Email send error for tenant {self.tenant_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}