from .base_handler import BaseHandler
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from notifications.services.auth_service import auth_service_client
import logging

logger = logging.getLogger('notifications.channels.email')

class EmailHandler(BaseHandler):
    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)

    def _get_tenant_branding(self, context: dict) -> dict:
        """Get tenant branding information"""
        return auth_service_client.get_tenant_branding(self.tenant_id)

    def _render_content(self, content: dict, context: dict) -> dict:
        """Render content with context"""
        from django.template import Template, Context
        rendered = {}
        for key, value in content.items():
            if isinstance(value, str):
                template = Template(value)
                rendered[key] = template.render(Context(context))
            else:
                rendered[key] = value
        return rendered

    def _render_html_template(self, content: dict, context: dict) -> str:
        """Render HTML template"""
        from django.template.loader import render_to_string
        template_name = content.get('html_template', 'email/base_email.html')
        return render_to_string(template_name, context)

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
                    logger.info(f"🔐 EmailHandler - decrypted tenant password fallback (masked): {_pwd[:6]}... (len={len(_pwd)})")
                except Exception as exc:
                    logger.warning(f"🔐 EmailHandler - password looks encrypted but failed to decrypt locally; proceeding with original value. Error: {exc}")
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
            try:
                sent = email.send(fail_silently=False)
                logger.info(f"📬 SMTP send() returned: {sent}")
                if sent:
                    logger.info(f"✅ Email sent successfully to {recipient}")
                else:
                    logger.warning(f"⚠️ Email send returned 0 for {recipient}")
                if sent:
                    return {'success': True, 'response': f'Sent to {sent} recipients'}
                else:
                    return {'success': False, 'error': 'Send failed', 'response': None}

            except Exception as smtp_exc:
                logger.error(f"❌ SMTP send error for tenant {self.tenant_id}: {smtp_exc}")
                import traceback
                logger.error(traceback.format_exc())
                return {'success': False, 'error': str(smtp_exc), 'response': None}

        except Exception as e:
            logger.error(f"EmailHandler.send error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e), 'response': None}

# End of EmailHandler