from .auth_handlers import (
    UserRegistrationHandler,
    PasswordResetHandler,
    LoginSecurityHandler
)
from .app_handlers import (
    InvoicePaymentHandler,
    TaskAssignmentHandler,
    CommentMentionHandler,
    ContentEngagementHandler
)
from .security_handlers import TwoFactorAuthHandler
from .document_handlers import (
    DocumentExpiryHandler,
    DocumentAcknowledgmentHandler
)
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger('notifications.events.registry')

class EventRegistry:
    """Registry for all event handlers"""

    def __init__(self):
        self.handlers = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register all event handlers"""
        handlers = [
            UserRegistrationHandler(),
            PasswordResetHandler(),
            LoginSecurityHandler(),
            InvoicePaymentHandler(),
            TaskAssignmentHandler(),
            CommentMentionHandler(),
            ContentEngagementHandler(),
            TwoFactorAuthHandler(),
            DocumentExpiryHandler(),
            DocumentAcknowledgmentHandler()
        ]

        for handler in handlers:
            for event_type in handler.supported_events:
                self.handlers[event_type] = handler

        logger.info(f"Registered {len(self.handlers)} event types with {len(handlers)} handlers")

    def get_handler(self, event_type: str):
        """Get handler for event type"""
        return self.handlers.get(event_type)

    def get_supported_events(self) -> List[str]:
        """Get all supported event types"""
        return list(self.handlers.keys())

    def process_event(self, event: Dict[str, Any]) -> Optional[Any]:
        """Process an event using appropriate handler"""
        event_type = event.get('event_type')
        if not event_type:
            logger.warning("Event missing event_type field")
            return None

        handler = self.get_handler(event_type)
        if not handler:
            logger.warning(f"No handler found for event type: {event_type}")
            return None

        return handler.process_event(event)

    def get_event_info(self, event_type: str) -> Optional[Dict[str, Any]]:
        """Get information about an event type"""
        handler = self.get_handler(event_type)
        if not handler:
            return None

        return {
            'handler_class': handler.__class__.__name__,
            'default_channels': handler.get_default_channels(event_type),
            'priority': handler.get_priority(event_type),
            'supported': True
        }


# Global registry instance
event_registry = EventRegistry()