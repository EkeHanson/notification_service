from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from notifications.models import NotificationRecord, ChannelType

logger = logging.getLogger('notifications.events')

class BaseEventHandler(ABC):
    """Base class for all event handlers"""

    def __init__(self):
        self.supported_events = []
        self.default_channels = []
        self.priority = 'medium'  # low, medium, high

    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can process the event type"""
        pass

    def get_default_channels(self, event_type: str) -> List[str]:
        """Get recommended channels for this event type"""
        return self.default_channels

    def get_priority(self, event_type: str) -> str:
        """Get priority level for this event type"""
        return self.priority

    @abstractmethod
    def get_template_data(self, event_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract template context from event payload"""
        pass

    def get_recipient(self, event_payload: Dict[str, Any]) -> str:
        """Extract recipient from event payload"""
        # Default implementation - override if needed
        return event_payload.get('email') or event_payload.get('phone') or event_payload.get('user_id')

    def get_channel_content(self, event_type: str, event_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Get content for each channel type"""
        context = self.get_template_data(event_payload)

        content_map = {}

        if ChannelType.EMAIL in self.get_default_channels(event_type):
            content_map[ChannelType.EMAIL] = self._get_email_content(event_type, context)

        if ChannelType.SMS in self.get_default_channels(event_type):
            content_map[ChannelType.SMS] = self._get_sms_content(event_type, context)

        if ChannelType.PUSH in self.get_default_channels(event_type):
            content_map[ChannelType.PUSH] = self._get_push_content(event_type, context)

        if ChannelType.INAPP in self.get_default_channels(event_type):
            content_map[ChannelType.INAPP] = self._get_inapp_content(event_type, context)

        return content_map

    @abstractmethod
    def _get_email_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get email content for this event"""
        pass

    def _get_sms_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get SMS content for this event (optional)"""
        return {}

    def _get_push_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get push content for this event (optional)"""
        return {}

    def _get_inapp_content(self, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get in-app content for this event (optional)"""
        return {}

    def process_event(self, event: Dict[str, Any]) -> Optional[NotificationRecord]:
        """Process the event and create notifications"""
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

            channels_content = self.get_channel_content(event_type, event_payload)

            # Create notifications for each channel
            notifications = []
            for channel, content in channels_content.items():
                if content:  # Only create if content is provided
                    notification = NotificationRecord.objects.create(
                        tenant_id=tenant_id,
                        channel=channel,
                        recipient=recipient,
                        content=content,
                        context=self.get_template_data(event_payload)
                    )
                    notifications.append(notification)

                    # Trigger async sending
                    from notifications.tasks import send_notification_task
                    send_notification_task.delay(
                        str(notification.id), channel, recipient, content,
                        self.get_template_data(event_payload)
                    )

            logger.info(f"Processed event {event_type} for tenant {tenant_id}: {len(notifications)} notifications created")
            return notifications[0] if notifications else None

        except Exception as e:
            logger.error(f"Error processing event {event.get('event_type')}: {str(e)}")
            return None