from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.review')

class ReviewApprovedHandler(BaseEventHandler):
    """Handles review approval events"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['reviews.approved']
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'medium'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient - the reviewer whose review was approved"""
        return event_payload.get('reviewer_email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'review_id': event_payload.get('review_id', ''),
            'reviewer_email': event_payload.get('reviewer_email', ''),
            'rating': event_payload.get('rating', 0),
            'comment_preview': event_payload.get('comment_preview', ''),
            'submitted_at': event_payload.get('submitted_at', ''),
            'performed_by': event_payload.get('performed_by', ''),
            'tenant_id': event_payload.get('tenant_id', ''),
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'subject': 'Your Review Has Been Approved',
            'body': '''
            Hi,

            Your review has been approved and is now visible.

            Rating: {{rating}}/5
            Comment: {{comment_preview}}

            Thank you for your feedback!

            Best regards,
            Review Team
            '''
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': '✅ Review Approved',
            'body': 'Your review has been approved and is now live',
            'data': {
                'type': 'review_approved',
                'action': 'view_review',
                'review_id': context.get('review_id'),
                'rating': context.get('rating')
            }
        }


class ReviewQRScannedHandler(BaseEventHandler):
    """Handles QR scan events for reviews"""

    def __init__(self):
        super().__init__()
        self.supported_events = ['reviews.qr_scanned']
        self.default_channels = [ChannelType.INAPP]  # Maybe notify business admin
        self.priority = 'low'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient - could be business admin or system"""
        # For now, use a placeholder or admin email
        return event_payload.get('admin_email', 'admin@system.com')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'qr_id': event_payload.get('qr_id', ''),
            'review_id': event_payload.get('review_id', ''),
            'reviewer_email': event_payload.get('reviewer_email', ''),
            'rating': event_payload.get('rating', 0),
            'submitted_at': event_payload.get('submitted_at', ''),
            'tenant_id': event_payload.get('tenant_id', ''),
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'subject': 'New Review Submitted via QR Code',
            'body': '''
            A new review has been submitted via QR code scan.

            QR ID: {{qr_id}}
            Rating: {{rating}}/5
            Reviewer: {{reviewer_email}}

            Please review and approve if appropriate.

            Best regards,
            Review System
            '''
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': '📱 New Review via QR',
            'body': 'A new review has been submitted via QR code scan',
            'data': {
                'type': 'qr_review_submitted',
                'action': 'review_pending_reviews',
                'qr_id': context.get('qr_id'),
                'review_id': context.get('review_id'),
                'rating': context.get('rating')
            }
        }