from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.user')

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
        updated_fields = context.get('updated_fields', [])
        fields_text = ', '.join(updated_fields) if updated_fields else 'profile information'

        return {
            'subject': 'Your Profile Has Been Updated - {{tenant_name}}',
            'body': f'''
            Hi {{user_name}},

            Your profile information has been successfully updated.

            Updated Fields: {fields_text}

            Update Time: {{update_time}}
            Updated By: {{updated_by}}

            If you did not make these changes, please contact support immediately.

            Best regards,
            {{tenant_name}} Team
            '''
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
        action = context.get('action', '').title()
        reason = context.get('reason', '')

        if event_type == 'user.account.locked':
            subject = 'Account Security Alert: Account Locked'
            body = f'''
            Your account has been locked for security reasons.

            Reason: {reason}
            Action Time: {{action_time}}
            Performed By: {{performed_by}}

            If you believe this was done in error, please contact support.

            Best regards,
            {{tenant_name}} Security Team
            '''
        elif event_type == 'user.account.unlocked':
            subject = 'Account Unlocked'
            body = f'''
            Your account has been unlocked.

            Action Time: {{action_time}}
            Performed By: {{performed_by}}

            You can now access your account normally.

            Best regards,
            {{tenant_name}} Team
            '''
        elif event_type == 'user.account.suspended':
            subject = 'Account Suspended'
            body = f'''
            Your account has been suspended.

            Reason: {reason}
            Action Time: {{action_time}}
            Performed By: {{performed_by}}

            Please contact support for more information.

            Best regards,
            {{tenant_name}} Team
            '''
        elif event_type == 'user.account.activated':
            subject = 'Account Activated'
            body = f'''
            Your account has been activated.

            Action Time: {{action_time}}
            Performed By: {{performed_by}}

            Welcome back! You can now access all account features.

            Best regards,
            {{tenant_name}} Team
            '''
        else:
            subject = f'Account {action}'
            body = f'''
            Your account status has been changed.

            Action: {action}
            Reason: {reason}
            Action Time: {{action_time}}
            Performed By: {{performed_by}}

            Best regards,
            {{tenant_name}} Team
            '''

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
        change_method = context.get('change_method', 'self')

        if change_method == 'self':
            subject = 'Password Changed Successfully'
            body = '''
            Hi {{user_name}},

            Your password has been successfully changed.

            Change Time: {{change_time}}
            IP Address: {{ip_address}}

            If you did not make this change, please contact support immediately and change your password.

            Best regards,
            {{tenant_name}} Security Team
            '''
        else:
            subject = 'Password Changed by Administrator'
            body = '''
            Hi {{user_name}},

            Your password has been changed by an administrator.

            Changed By: {{changed_by}}
            Change Time: {{change_time}}

            For security reasons, please log in with your new password and change it to something only you know.

            If you have any concerns, please contact support.

            Best regards,
            {{tenant_name}} Security Team
            '''

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