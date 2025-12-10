from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.auth')

class UserRegistrationHandler(BaseEventHandler):
    """Handles user registration completed events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['user.registration.completed']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient - can use username, email, or user_id"""
        # Priority: username > email > user_id
        return (event_payload.get('username') or
                event_payload.get('email') or
                event_payload.get('user_id'))

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'username': event_payload.get('username', ''),
            'first_name': event_payload.get('first_name', ''),
            'last_name': event_payload.get('last_name', ''),
            'email': event_payload.get('email', ''),
            'registration_date': event_payload.get('registration_date', ''),
            'verification_required': event_payload.get('verification_required', False),
            'send_credentials': event_payload.get('send_credentials', False),
            'temp_password': event_payload.get('temp_password', ''),
            'login_link': event_payload.get('login_link', '')
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        verification_text = 'To get started, please verify your email address.' if context.get('verification_required') else ''

        # Build credentials section if send_credentials is true
        credentials_text = ''
        if context.get('send_credentials'):
            # Determine which identifier to show (username or email)
            identifier_label = 'Username'
            identifier_value = context.get('username', '')

            # If no username, use email as identifier
            if not identifier_value:
                identifier_label = 'Email'
                identifier_value = context.get('email', '')

            credentials_text = f'''

Your login credentials:
{identifier_label}: {identifier_value}
Temporary Password: {context.get('temp_password', 'N/A')}'''

            if context.get('login_link'):
                credentials_text += f'''

Login Link: {context.get('login_link')}'''

            credentials_text += '''

Please change your password after first login for security.
IMPORTANT: Keep these credentials secure and do not share them with anyone.'''

        return {
            'subject': 'Welcome to {{tenant_name}}, {{first_name}}!',
            'body': f'''
            Hi {{first_name}},

            Welcome to {{tenant_name}}! Your account has been successfully created.

            {verification_text}{credentials_text}

            If you have any questions, feel free to reach out to our support team.

            Best regards,
            The {{tenant_name}} Team
            '''
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'Welcome to our platform!',
            'body': 'Your account has been created successfully. Explore and get started!',
            'data': {
                'type': 'welcome',
                'action': 'redirect',
                'url': '/dashboard'
            }
        }


class PasswordResetHandler(BaseEventHandler):
    """Handles password reset requested events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['user.password.reset.requested']
        self.default_channels = [ChannelType.EMAIL, ChannelType.SMS]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        # Can send to both email and phone based on user preference
        return event_payload.get('email') or event_payload.get('phone')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        reset_token = event_payload.get('reset_token', '')
        provided_link = event_payload.get('reset_link')

        return {
            'email': event_payload.get('email', ''),
            'phone': event_payload.get('phone', ''),
            'reset_token': reset_token,
            'expires_at': event_payload.get('expires_at', ''),
            'ip_address': event_payload.get('ip_address', ''),
            'reset_link': provided_link or f"/reset-password?token={reset_token}"
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'subject': 'Password Reset Request - {{tenant_name}}',
            'body': '''
            Hi,

            We received a request to reset your password for your {{tenant_name}} account. If you made this request, click the link below:

            [Reset Password]({{reset_link}})

            This link will expire at {{expires_at}}.

            If you didn't request this reset, please ignore this email and secure your account.

            For security reasons, this request was made from IP: {{ip_address}}

            Best regards,
            The {{tenant_name}} Security Team
            '''
        }

    def _get_sms_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'body': 'Password reset requested. Use this code to reset: {{reset_token}}'
        }


class LoginSecurityHandler(BaseEventHandler):
    """Handles login success and failure events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['user.login.succeeded', 'user.login.failed']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_default_channels(self, event_type: str) -> List[str]:
        if event_type == 'user.login.failed':
            return [ChannelType.EMAIL, ChannelType.SMS, ChannelType.PUSH, ChannelType.INAPP]
        return [ChannelType.EMAIL, ChannelType.INAPP]

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'email': event_payload.get('email', ''),
            'login_time': event_payload.get('login_time', ''),
            'ip_address': event_payload.get('ip_address', ''),
            'user_agent': event_payload.get('user_agent', ''),
            'location': event_payload.get('location', ''),
            'failure_reason': event_payload.get('failure_reason', ''),
            'attempt_count': event_payload.get('attempt_count', 0)
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'user.login.failed':
            return {
                'subject': 'Security Alert: Failed Login Attempt',
                'body': '''
                Security Alert!

                We detected a failed login attempt on your account.

                Details:
                - Time: {{login_time}}
                - IP Address: {{ip_address}}
                - Location: {{location}}
                - Reason: {{failure_reason}}
                - Attempt Count: {{attempt_count}}

                If this wasn't you, please change your password immediately and contact support.

                Best regards,
                The Security Team
                '''
            }
        else:  # login succeeded
            return {
                'subject': 'New Login to Your Account',
                'body': '''
                Hi,

                We noticed a new login to your account.

                Details:
                - Time: {{login_time}}
                - IP Address: {{ip_address}}
                - Location: {{location}}
                - Device: {{user_agent}}

                If this wasn't you, please secure your account immediately.

                Best regards,
                The Security Team
                '''
            }

    def _get_sms_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'user.login.failed':
            return {
                'body': 'Security Alert: Failed login attempt detected. Check your email for details.'
            }
        return {}

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'user.login.failed':
            return {
                'title': 'Security Alert',
                'body': 'Failed login attempt detected',
                'data': {
                    'type': 'security_alert',
                    'action': 'open_security'
                }
            }
        return {}

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'user.login.succeeded':
            return {
                'title': '🔐 New Login Detected',
                'body': 'A new login was detected on your account from {{location}}',
                'data': {
                    'type': 'login_success',
                    'action': 'view_activity',
                    'priority': 'normal'
                }
            }
        elif event_type == 'user.login.failed':
            return {
                'title': '🚨 Security Alert: Failed Login',
                'body': 'A failed login attempt was detected from {{location}}. Attempt #{{attempt_count}}',
                'data': {
                    'type': 'login_failed',
                    'action': 'view_security',
                    'priority': 'urgent',
                    'failure_reason': context.get('failure_reason'),
                    'ip_address': context.get('ip_address')
                }
            }
        return {}