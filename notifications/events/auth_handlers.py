from .base_handler import BaseEventHandler
from notifications.models import ChannelType, NotificationRecord
from typing import Dict, Any, List, Optional
import logging
from django.utils import timezone
from datetime import timedelta

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
        # Priority: username > email/user_email > user_id
        return (event_payload.get('username') or
                event_payload.get('email') or
                event_payload.get('user_email') or
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



class OTPHandler(BaseEventHandler):
    """Handles OTP code requested events"""

    def _get_inapp_content(self, event_type: str, context: dict) -> dict:
        return {
            'title': 'Your Login Verification Code',
            'body': f"Your OTP code is: {context.get('2fa_code', 'N/A')} (expires in {context.get('expires_in_seconds', 300)} seconds)",
            'data': {
                'type': 'otp',
                'code': context.get('2fa_code', ''),
                'method': context.get('2fa_method', ''),
                'expires_in_seconds': context.get('expires_in_seconds', 300),
            }
        }

    def _get_email_content(self, event_type: str, context: dict) -> dict:
        from django.template.loader import render_to_string
        subject = 'Your Login Verification Code - {{tenant_name}}'
        body = render_to_string('email/otp_email.html', context)
        return {
            'subject': subject,
            'body': body
        }

    def __init__(self):
        super().__init__()
        self.supported_events = ['auth.2fa.code.requested']
        self.default_channels = [ChannelType.EMAIL]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        return event_payload.get('user_email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'user_email': event_payload.get('user_email', ''),
            '2fa_code': event_payload.get('2fa_code', ''),
            '2fa_method': event_payload.get('2fa_method', 'email'),
            'ip_address': event_payload.get('ip_address', ''),
            'user_agent': event_payload.get('user_agent', ''),
            'login_method': event_payload.get('login_method', ''),
            'remember_me': event_payload.get('remember_me', False),
            'expires_in_seconds': event_payload.get('expires_in_seconds', 300),
            'login_domain': event_payload.get('login_domain', ''),
            'tenant_name': event_payload.get('tenant_name', ''),
            'tenant_logo': event_payload.get('tenant_logo', ''),
            'tenant_primary_color': event_payload.get('tenant_primary_color', ''),
            'tenant_secondary_color': event_payload.get('tenant_secondary_color', ''),
        }

        def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
                from django.template.loader import render_to_string
                subject = 'Your Login Verification Code - {{tenant_name}}'
                body = render_to_string('email/otp_email.html', context)
                return {
                        'subject': subject,
                        'body': body
                }

    def process_event(self, event: Dict[str, Any]) -> Optional[NotificationRecord]:
        """Process OTP event with deduplication to prevent multiple emails and always include INAPP channel."""
        try:
            event_type = event['event_type']
            event_payload = event['payload']
            tenant_id = event['tenant_id']

            if not self.can_handle(event_type):
                return None

            recipient = self.get_recipient(event_payload)
            if not recipient:
                logger.warning(f"No recipient found for event {event_type}")
                return None

            # Database-based deduplication to prevent duplicates across multiple service instances
            from notifications.models import NotificationRecord
            from django.utils import timezone
            from datetime import timedelta

            # Check for recent OTP notifications to the same recipient in the last 60 seconds
            recent_otp = NotificationRecord.objects.filter(
                tenant_id=tenant_id,
                recipient=recipient,
                channel='email',
                context__has_key='2fa_code',  # Check if context contains 2fa_code
                created_at__gte=timezone.now() - timedelta(seconds=60)
            ).exists()

            if recent_otp:
                logger.info(f"Skipping duplicate OTP notification for {recipient} in tenant {tenant_id} (database check)")
                return None

            # Patch: Always include INAPP in default_channels for this event
            if ChannelType.INAPP not in self.default_channels:
                self.default_channels.append(ChannelType.INAPP)

            # Proceed with normal processing
            return super().process_event(event)

        except Exception as e:
            logger.error(f"Error processing OTP event {event.get('event_type')}: {str(e)}")
            return None



class PasswordResetHandler(BaseEventHandler):
    """Handles password reset requested events"""

    def _get_email_content(self, event_type: str, context: dict) -> dict:
        from django.template.loader import render_to_string
        subject = 'Password Reset Request - {{tenant_name}}'
        body = render_to_string('email/password_reset_email.html', context)
        return {
            'subject': subject,
            'body': body
        }

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

        # Format expiration time in a user-friendly way
        expires_at_raw = event_payload.get('expires_at', '')
        expires_at_formatted = expires_at_raw
        if expires_at_raw:
            try:
                from datetime import datetime
                # Parse ISO format and format nicely
                dt = datetime.fromisoformat(expires_at_raw.replace('Z', '+00:00'))
                expires_at_formatted = dt.strftime('%B %d, %Y at %I:%M %p UTC')
            except Exception:
                # Fallback to original if parsing fails
                expires_at_formatted = expires_at_raw

        return {
            'email': event_payload.get('email', ''),
            'phone': event_payload.get('phone', ''),
            'user_name': event_payload.get('user_name', ''),
            'reset_token': reset_token,
            'expires_at': expires_at_formatted,
            'ip_address': event_payload.get('ip_address', ''),
            'reset_link': provided_link or f"/reset-password?token={reset_token}",
            'reset_domain': event_payload.get('reset_domain', ''),
            'tenant_name': event_payload.get('tenant_name', ''),
            'tenant_logo': event_payload.get('tenant_logo', ''),
            'tenant_primary_color': event_payload.get('tenant_primary_color', ''),
            'tenant_secondary_color': event_payload.get('tenant_secondary_color', ''),
            'tenant_unique_id': event_payload.get('tenant_unique_id', ''),
            'tenant_schema': event_payload.get('tenant_schema', ''),
        }

        def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
                from django.template.loader import render_to_string
                subject = 'Password Reset Request - {{tenant_name}}'
                body = render_to_string('email/password_reset_email.html', context)
                return {
                        'subject': subject,
                        'body': body
                }

    def _get_sms_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'body': 'Password reset requested. Use this code to reset: {{reset_token}}'
        }

    def process_event(self, event: Dict[str, Any]) -> Optional[NotificationRecord]:
        """Process password reset event with deduplication to prevent multiple emails"""
        try:
            event_type = event['event_type']
            event_payload = event['payload']
            tenant_id = event['tenant_id']

            if not self.can_handle(event_type):
                return None

            recipient = self.get_recipient(event_payload)
            if not recipient:
                logger.warning(f"No recipient found for event {event_type}")
                return None

            # Database-based deduplication to prevent duplicates across multiple service instances
            from notifications.models import NotificationRecord
            from django.utils import timezone
            from datetime import timedelta

            # Check for recent password reset notifications to the same recipient in the last 60 seconds
            recent_reset = NotificationRecord.objects.filter(
                tenant_id=tenant_id,
                recipient=recipient,
                channel__in=['email', 'sms'],  # Password reset can be email or SMS
                context__has_key='reset_token',  # Check if context contains reset_token
                created_at__gte=timezone.now() - timedelta(seconds=60)
            ).exists()

            if recent_reset:
                logger.info(f"Skipping duplicate password reset notification for {recipient} in tenant {tenant_id} (database check)")
                return None

            # Proceed with normal processing
            return super().process_event(event)

        except Exception as e:
            logger.error(f"Error processing password reset event {event.get('event_type')}: {str(e)}")
            return None


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
            'attempt_count': event_payload.get('attempt_count', 0),
            'login_method': event_payload.get('login_method', ''),
            # Include tenant name for in-app notification message
            'tenant_name': event_payload.get('tenant_name', 'the platform'),
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
            content = {
                'title': '✅ Login Successful',
                'body': f'Welcome back! You have successfully logged in to {context.get("tenant_name", "the platform")}.',
                'data': {
                    'type': 'login_success',
                    'action': 'view_dashboard',
                    'priority': 'normal',
                    'login_method': context.get('login_method')
                }
            }
            logger.info(f"📱 Generated login success notification content: {content}")
            return content
        elif event_type == 'user.login.failed':
            content = {
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
            logger.info(f"📱 Generated login failed notification content: {content}")
            return content
        return {}