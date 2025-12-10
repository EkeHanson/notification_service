from .base_handler import BaseEventHandler
from notifications.models import ChannelType
from typing import Dict, Any, List
import logging

logger = logging.getLogger('notifications.events.document')


class DocumentExpiryHandler(BaseEventHandler):
    """Handles document expiry warning and expired events"""

    def __init__(self):
        super().__init__()
        self.supported_events = [
            'user.document.expiry.warning',
            'user.document.expired'
        ]
        self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
        self.priority = 'medium'

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.supported_events

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient email from event payload"""
        return event_payload.get('user_email')

    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'full_name': event_payload.get('full_name', ''),
            'user_email': event_payload.get('user_email', ''),
            'document_type': event_payload.get('document_type', ''),
            'document_name': event_payload.get('document_name', ''),
            'expiry_date': event_payload.get('expiry_date', ''),
            'days_left': event_payload.get('days_left'),
            'days_expired': event_payload.get('days_expired'),
            'message': event_payload.get('message', ''),
            'timezone': event_payload.get('timezone', 'Africa/Lagos'),
        }

    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if event_type == 'user.document.expiry.warning':
            subject = f"⚠️ Document Expiring Soon: {context['document_type']}"
            body = f"""
            Dear {context['full_name']},

            This is an important notification regarding your documents.

            **Document Details:**
            - Type: {context['document_type']}
            - Name: {context['document_name']}
            - Expiry Date: {context['expiry_date']}
            - Days Left: {context['days_left']}

            **Important:** {context['message']}

            Please take immediate action to renew this document to avoid any employment disruption or compliance issues.

            If you have already renewed this document, please update your profile with the new expiry date.

            Best regards,
            HR & Compliance Team
            """
        else:  # user.document.expired
            subject = f"🚨 EXPIRED Document: {context['document_type']}"
            body = f"""
            Dear {context['full_name']},

            **URGENT: Document Has Expired**

            **Document Details:**
            - Type: {context['document_type']}
            - Name: {context['document_name']}
            - Expiry Date: {context['expiry_date']}
            - Days Expired: {context['days_expired']}

            **Critical:** {context['message']}

            Your employment status and compliance may be affected. Please renew this document immediately and update your profile.

            Contact HR immediately if you need assistance with the renewal process.

            Best regards,
            HR & Compliance Team
            """

        return {
            'subject': subject,
            'body': body.strip()
        }

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate in-app notification content for document events"""
        if event_type == 'user.document.expiry.warning':
            return {
                'title': f'⚠️ {context["document_type"]} Expiring Soon',
                'body': f'Your {context["document_type"]} expires in {context["days_left"]} days. Please renew to avoid disruption.',
                'data': {
                    'type': 'document_expiry_warning',
                    'document_type': context['document_type'],
                    'document_name': context['document_name'],
                    'expiry_date': context['expiry_date'],
                    'days_left': context['days_left'],
                    'action': 'view_documents',
                    'priority': 'high'
                }
            }
        else:  # user.document.expired
            return {
                'title': f'🚨 {context["document_type"]} Expired',
                'body': f'Your {context["document_type"]} has expired. Immediate renewal required.',
                'data': {
                    'type': 'document_expired',
                    'document_type': context['document_type'],
                    'document_name': context['document_name'],
                    'expiry_date': context['expiry_date'],
                    'days_expired': context['days_expired'],
                    'action': 'renew_document',
                    'priority': 'urgent'
                }
            }


class DocumentAcknowledgmentHandler(BaseEventHandler):
   """Handles document acknowledgment events"""

   def __init__(self):
       super().__init__()
       self.supported_events = [
           'document.acknowledged'
       ]
       self.default_channels = [ChannelType.EMAIL, ChannelType.INAPP]
       self.priority = 'medium'

   def can_handle(self, event_type: str) -> bool:
       return event_type in self.supported_events

   def get_recipient(self, event_payload: Dict[str, Any]) -> str:
       """Extract recipient email from event payload"""
       return event_payload.get('user_email')

   def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
       return {
           'user_name': event_payload.get('user_name', ''),
           'user_email': event_payload.get('user_email', ''),
           'document_title': event_payload.get('document_title', ''),
           'document_id': event_payload.get('document_id', ''),
           'acknowledged_at': event_payload.get('acknowledged_at', ''),
           'tenant_name': event_payload.get('tenant_name', ''),
           'timezone': event_payload.get('timezone', 'Africa/Lagos'),
       }

   def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
       subject = f"✅ Document Acknowledged: {context['document_title']}"
       body = f"""
       Dear {context['user_name']},

       This is to confirm that you have successfully acknowledged the following document:

       **Document Details:**
       - Title: {context['document_title']}
       - Acknowledged At: {context['acknowledged_at']}
       - Organization: {context['tenant_name']}

       **Important Information:**
       By acknowledging this document, you confirm that you have read and understood its contents. This acknowledgment has been recorded in our system for compliance purposes.

       If you did not perform this action or believe this was done in error, please contact your administrator immediately.

       Thank you for your attention to compliance matters.

       Best regards,
       Compliance & HR Team
       {context['tenant_name']}
       """

       return {
           'subject': subject,
           'body': body.strip()
       }

   def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
       """Generate in-app notification content for document acknowledgment"""
       return {
           'title': f'✅ Document Acknowledged',
           'body': f'You have successfully acknowledged "{context["document_title"]}".',
           'data': {
               'type': 'document_acknowledged',
               'document_title': context['document_title'],
               'document_id': context['document_id'],
               'acknowledged_at': context['acknowledged_at'],
               'action': 'view_acknowledgment',
               'priority': 'normal'
           }
       }