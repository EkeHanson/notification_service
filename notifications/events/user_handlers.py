from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.user')

class UserAccountCreatedHandler(BaseEventHandler):
    """Handles user account created events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['user.account.created']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        return event_payload.get('user_email') or event_payload.get('email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'user_email': event_payload.get('user_email', ''),
            'user_name': event_payload.get('user_name', ''),
            'created_by': event_payload.get('created_by', ''),
            'creation_time': event_payload.get('creation_time', ''),
            'tenant_name': event_payload.get('tenant_name', ''),
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from django.template.loader import render_to_string
        subject = 'Your Account Has Been Created - {{tenant_name}}'
        body = render_to_string('email/user_account_created.html', context)
        return {
            'subject': subject,
            'body': body
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': '🎉 Account Created',
            'body': 'Your account has been created successfully.',
            'data': {
                'type': 'account_created',
                'action': 'view_account',
                'creation_time': context.get('creation_time'),
                'created_by': context.get('created_by')
            }
        }

class UserProfileUpdateHandler(BaseEventHandler):
    """Handles user profile update events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['user.profile.updated']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'medium'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient - the user whose profile was updated"""
        return event_payload.get('user_email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'user_email': event_payload.get('user_email', ''),
            'user_name': event_payload.get('user_name', ''),
            'updated_by': event_payload.get('updated_by', ''),
            'updated_fields': event_payload.get('updated_fields', []),
            'update_time': event_payload.get('update_time', ''),
            'ip_address': event_payload.get('ip_address', ''),
            'user_agent': event_payload.get('user_agent', ''),
            'tenant_name': event_payload.get('tenant_name', ''),
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from django.template.loader import render_to_string
        subject = 'Your Profile Has Been Updated - {{tenant_name}}'
        body = render_to_string('email/user_profile_updated.html', context)
        return {
            'subject': subject,
            'body': body
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        updated_fields = context.get('updated_fields', [])
        fields_count = len(updated_fields)

        return {
            'title': '📝 Profile Updated',
            'body': f'Your profile has been updated ({fields_count} field{"s" if fields_count != 1 else ""} changed)',
            'data': {
                'type': 'profile_updated',
                'action': 'view_profile',
                'updated_fields': updated_fields,
                'update_time': context.get('update_time'),
                'updated_by': context.get('updated_by')
            }
        }


class UserAccountActionHandler(BaseEventHandler):
    """Handles user account action events (lock, unlock, suspend, activate)"""

    def __init__(self):
        super().__init__()
        self.supported_events = [
            'user.account.locked',
            'user.account.unlocked',
            'user.account.suspended',
            'user.account.activated'
        ]
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient - the user whose account was affected"""
        return event_payload.get('user_email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'user_email': event_payload.get('user_email', ''),
            'user_name': event_payload.get('user_name', ''),
            'action': event_payload.get('action', ''),
            'reason': event_payload.get('reason', ''),
            'performed_by': event_payload.get('performed_by', ''),
            'action_time': event_payload.get('action_time', ''),
            'ip_address': event_payload.get('ip_address', ''),
            'user_agent': event_payload.get('user_agent', ''),
            'tenant_name': event_payload.get('tenant_name', ''),
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from django.template.loader import render_to_string
        subject = 'Account Status Changed - {{tenant_name}}'
        body = render_to_string('email/user_account_action.html', context)
        return {
            'subject': subject,
            'body': body
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        action = context.get('action', '').title()

        if event_type == 'user.account.locked':
            title = '🔒 Account Locked'
            body = 'Your account has been locked for security reasons'
            action_type = 'account_locked'
        elif event_type == 'user.account.unlocked':
            title = '🔓 Account Unlocked'
            body = 'Your account has been unlocked and is now accessible'
            action_type = 'account_unlocked'
        elif event_type == 'user.account.suspended':
            title = '⚠️ Account Suspended'
            body = 'Your account has been suspended'
            action_type = 'account_suspended'
        elif event_type == 'user.account.activated':
            title = '✅ Account Activated'
            body = 'Your account has been activated and is now active'
            action_type = 'account_activated'
        else:
            title = f'Account {action}'
            body = f'Your account status has been changed: {action}'
            action_type = 'account_status_changed'

        return {
            'title': title,
            'body': body,
            'data': {
                'type': action_type,
                'action': 'view_account_status',
                'reason': context.get('reason'),
                'performed_by': context.get('performed_by'),
                'action_time': context.get('action_time')
            }
        }


class UserPasswordChangeHandler(BaseEventHandler):
    """Handles user password change events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['user.password.changed']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient - the user whose password was changed"""
        return event_payload.get('user_email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'user_email': event_payload.get('user_email', ''),
            'user_name': event_payload.get('user_name', ''),
            'changed_by': event_payload.get('changed_by', ''),
            'change_time': event_payload.get('change_time', ''),
            'ip_address': event_payload.get('ip_address', ''),
            'user_agent': event_payload.get('user_agent', ''),
            'tenant_name': event_payload.get('tenant_name', ''),
            'change_method': event_payload.get('change_method', ''),  # 'self' or 'admin'
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        from django.template.loader import render_to_string
        subject = 'Your Password Has Been Changed - {{tenant_name}}'
        body = render_to_string('email/user_password_changed.html', context)
        return {
            'subject': subject,
            'body': body
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        change_method = context.get('change_method', 'self')

        if change_method == 'self':
            title = '🔑 Password Changed'
            body = 'Your password has been successfully changed'
        else:
            title = '🔑 Password Changed by Admin'
            body = 'Your password was changed by an administrator'

        return {
            'title': title,
            'body': body,
            'data': {
                'type': 'password_changed',
                'action': 'view_security_settings',
                'change_method': change_method,
                'changed_by': context.get('changed_by'),
                'change_time': context.get('change_time')
            }
        }