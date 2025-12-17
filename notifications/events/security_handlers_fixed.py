from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.security')

class TwoFactorAuthHandler(BaseEventHandler):
    """Handles 2FA-related security events"""

    def __init__(self):
        super().__init__()
        self.supported_events = [
            'auth.2fa.code.requested',
            'auth.2fa.attempt.failed',
            'auth.2fa.method.changed'
        ]
        self.default_channels = [ChannelType.SMS, ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_default_channels(self, event_type: str) -> List[str]:
        if event_type == 'auth.2fa.code.requested':
            return [ChannelType.SMS, ChannelType.EMAIL]  # Primary and backup
        elif event_type == 'auth.2fa.attempt.failed':
            return [ChannelType.EMAIL, ChannelType.SMS, ChannelType.PUSH]
        else:  # method changed
            return [ChannelType.EMAIL, ChannelType.INAPP]

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient from 2FA event payload"""
        # For 2FA events, the recipient is the user_email field
        return event_payload.get('user_email') or event_payload.get('email') or event_payload.get('phone') or event_payload.get('user_id')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        # Format expires_at properly
        expires_at = event_payload.get('expires_at', '')
        if expires_at:
            try:
                from datetime import datetime
                # Try to parse and format the datetime
                if isinstance(expires_at, str):
                    dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    expires_at = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                elif hasattr(expires_at, 'strftime'):
                    expires_at = expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                # If formatting fails, use as-is
                pass

        # Get login domain
        login_domain = event_payload.get('login_domain', '')
        login_domain_text = f" to {login_domain}" if login_domain else ""

        # Build greeting
        first_name = event_payload.get('user_first_name', '').strip()
        last_name = event_payload.get('user_last_name', '').strip()
        greeting = f"Hi {first_name} {last_name},".strip() if first_name or last_name else "Hi,"

        # Extract tenant details directly from event payload
        return {
            'user_id': event_payload.get('user_id', ''),
            'user_first_name': first_name,
            'user_last_name': last_name,
            'greeting': greeting,
            'method': event_payload.get('method', 'sms'),
            'code': event_payload.get('2fa_code', ''),  # Use 2fa_code from payload
            'expires_at': expires_at or '15 minutes from now',  # Default fallback
            'ip_address': event_payload.get('ip_address', ''),
            'user_agent': event_payload.get('user_agent', ''),
            'failure_reason': event_payload.get('failure_reason', ''),
            'attempt_count': event_payload.get('attempt_count', 0),
            'old_method': event_payload.get('old_method', ''),
            'new_method': event_payload.get('new_method', ''),
            'changed_at': event_payload.get('changed_at', ''),
            'login_domain': login_domain,
            'login_domain_text': login_domain_text,
            # Include tenant branding data directly from event payload
            'tenant_name': event_payload.get('tenant_name', 'Platform'),
            'tenant_logo': event_payload.get('tenant_logo'),
            'primary_color': event_payload.get('tenant_primary_color', '#007bff'),
            'secondary_color': event_payload.get('tenant_secondary_color', '#6c757d'),
            'email_from': event_payload.get('email_from')
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'auth.2fa.code.requested':
            return {
                'subject': 'Your Two-Factor Authentication Code - {{tenant_name}}',
                'body': '''{{greeting}}

You requested to log in{{login_domain_text}} with your {{tenant_name}} account.

Your two-factor authentication code is:

{{code}}

This code will expire in 5 minutes.

For your security, this code was requested from IP address: {{ip_address}}

If you didn't request this code, please secure your account immediately by changing your password and contacting our support team.

Best regards,
The {{tenant_name}} Security Team'''
            }
        elif event_type == 'auth.2fa.attempt.failed':
            return {
                'subject': 'Security Alert: Failed 2FA Attempt',
                'body': '''
Security Alert!

A failed two-factor authentication attempt was detected on your account.

Details:
- Time: {{changed_at}}
- Method: {{method}}
- IP Address: {{ip_address}}
- Failure Reason: {{failure_reason}}
- Attempt Count: {{attempt_count}}

If this wasn't you, please change your password and contact support immediately.

Best regards,
Security Team
'''
            }
        else:  # method changed
            return {
                'subject': 'Security Settings Changed',
                'body': '''
Hi,

Your two-factor authentication method has been changed.

Previous method: {{old_method}}
New method: {{new_method}}
Changed at: {{changed_at}}

If you didn't make this change, please contact support immediately.

Best regards,
Security Team
'''
            }

    def _get_sms_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'auth.2fa.code.requested':
            return {
                'body': 'Your 2FA code: {{code}}. Expires: {{expires_at}}'
            }
        elif event_type == 'auth.2fa.attempt.failed':
            return {
                'body': 'Security Alert: Failed 2FA attempt detected. Check email for details.'
            }
        else:  # method changed
            return {
                'body': 'Security: Your 2FA method changed from {{old_method}} to {{new_method}}'
            }

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'auth.2fa.attempt.failed':
            return {
                'title': 'Security Alert',
                'body': 'Failed 2FA attempt detected',
                'data': {
                    'type': 'security_alert',
                    'action': 'review_security'
                }
            }
        return {}

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'auth.2fa.code.requested':
            return {
                'title': '2FA Code Sent',
                'body': 'A two-factor authentication code has been sent to your {{method}}',
                'data': {
                    'type': '2fa_code_sent',
                    'method': '{{method}}'
                }
            }
        elif event_type == 'auth.2fa.method.changed':
            return {
                'title': 'Security Settings Updated',
                'body': 'Your 2FA method has been changed to {{new_method}}',
                'data': {
                    'type': 'security_settings_changed',
                    'action': 'view_security_settings'
                }
            }
        return {}