from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.app')

class InvoicePaymentHandler(BaseEventHandler):
    """Handles invoice payment events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['invoice.payment.failed']
        self.default_channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.PUSH]
        self.priority = 'high'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'invoice_id': event_payload.get('invoice_id', ''),
            'amount': event_payload.get('amount', 0),
            'currency': event_payload.get('currency', 'USD'),
            'failure_reason': event_payload.get('failure_reason', ''),
            'next_retry_date': event_payload.get('next_retry_date', ''),
            'payment_method': event_payload.get('payment_method', '')
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        retry_text = f"We'll automatically retry this payment on {context.get('next_retry_date', '')}." if context.get('next_retry_date') else ""

        return {
            'subject': 'Payment Failed - Invoice {{invoice_id}} - {{tenant_name}}',
            'body': f'''
            Payment Failed

            We're sorry, but your payment of {{currency}} {{amount}} for invoice {{invoice_id}} has failed.

            Reason: {{failure_reason}}

            Please update your payment method or contact {{tenant_name}} support to resolve this issue.

            {retry_text}

            Best regards,
            {{tenant_name}} Billing Team
            '''
        }

    def _get_sms_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'body': 'Payment failed for invoice {{invoice_id}} ({{currency}} {{amount}}). Please update payment method.'
        }

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'Payment Failed',
            'body': 'Invoice {{invoice_id}} payment of {{currency}} {{amount}} failed',
            'data': {
                'type': 'payment_failed',
                'invoice_id': '{{invoice_id}}',
                'action': 'open_billing'
            }
        }


class TaskAssignmentHandler(BaseEventHandler):
    """Handles task assignment events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['task.assigned']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP, ChannelType.PUSH]
        self.priority = 'medium'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'task_id': event_payload.get('task_id', ''),
            'task_title': event_payload.get('task_title', ''),
            'task_description': event_payload.get('task_description', ''),
            'assigned_by': event_payload.get('assigned_by', ''),
            'due_date': event_payload.get('due_date', ''),
            'priority': event_payload.get('priority', 'medium')
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'subject': 'New Task Assigned: {{task_title}} - {{tenant_name}}',
            'body': '''
            Hi,

            A new task has been assigned to you in {{tenant_name}}:

            **Task:** {{task_title}}
            **Description:** {{task_description}}
            **Assigned by:** {{assigned_by}}
            **Due Date:** {{due_date}}
            **Priority:** {{priority}}

            Please review and complete this task by the due date.

            [View Task]({{task_link}})

            Best regards,
            {{tenant_name}} Task Management
            '''
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'New Task Assigned',
            'body': '{{task_title}} - Due: {{due_date}}',
            'data': {
                'type': 'task_assigned',
                'task_id': '{{task_id}}',
                'action': 'open_task'
            }
        }

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'New Task',
            'body': '{{task_title}} assigned by {{assigned_by}}',
            'data': {
                'type': 'task_notification',
                'task_id': '{{task_id}}',
                'action': 'open_task'
            }
        }


class CommentMentionHandler(BaseEventHandler):
    """Handles comment mention events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['comment.mentioned']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP, ChannelType.PUSH]
        self.priority = 'medium'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'comment_id': event_payload.get('comment_id', ''),
            'comment_text': event_payload.get('comment_text', ''),
            'author_name': event_payload.get('author_name', ''),
            'entity_type': event_payload.get('entity_type', ''),
            'entity_id': event_payload.get('entity_id', ''),
            'entity_title': event_payload.get('entity_title', ''),
            'mentioned_at': event_payload.get('mentioned_at', '')
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'subject': 'You were mentioned in a comment',
            'body': '''
            Hi,

            {{author_name}} mentioned you in a comment on {{entity_type}} "{{entity_title}}":

            "{{comment_text}}"

            [View Comment]({{comment_link}})

            Best regards,
            Team
            '''
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'You were mentioned',
            'body': '{{author_name}} mentioned you in a comment',
            'data': {
                'type': 'mention',
                'comment_id': '{{comment_id}}',
                'entity_id': '{{entity_id}}',
                'action': 'open_comment'
            }
        }

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'Mentioned',
            'body': '{{author_name}} mentioned you',
            'data': {
                'type': 'mention_notification',
                'comment_id': '{{comment_id}}',
                'action': 'open_comment'
            }
        }


class ContentEngagementHandler(BaseEventHandler):
    """Handles content engagement events (likes, etc.)"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['content.liked']
        self.default_channels = [ChannelType.INAPP, ChannelType.PUSH]
        self.priority = 'low'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'content_id': event_payload.get('content_id', ''),
            'content_type': event_payload.get('content_type', ''),
            'content_title': event_payload.get('content_title', ''),
            'liker_name': event_payload.get('liker_name', ''),
            'like_count': event_payload.get('like_count', 0),
            'engagement_type': event_payload.get('engagement_type', 'like')
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'New Engagement',
            'body': '{{liker_name}} {{engagement_type}}d your {{content_type}}',
            'data': {
                'type': 'engagement',
                'content_id': '{{content_id}}',
                'action': 'open_content'
            }
        }

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': 'New {{engagement_type}}',
            'body': '{{liker_name}} {{engagement_type}}d your post',
            'data': {
                'type': 'engagement_notification',
                'content_id': '{{content_id}}',
                'action': 'open_content'
            }
        }