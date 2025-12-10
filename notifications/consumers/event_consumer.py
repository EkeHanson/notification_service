import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from notifications.events.auth_handlers import (
    UserRegistrationHandler,
    PasswordResetHandler,
    LoginSecurityHandler
)
from notifications.events.app_handlers import (
    InvoicePaymentHandler,
    TaskAssignmentHandler,
    CommentMentionHandler,
    ContentEngagementHandler
)
from notifications.events.security_handlers import (
    TwoFactorAuthHandler
)
from notifications.events.user_handlers import (
    UserProfileUpdateHandler,
    UserAccountActionHandler,
    UserPasswordChangeHandler
)
from notifications.events.review_handlers import (
    ReviewApprovedHandler,
    ReviewQRScannedHandler
)
from notifications.events.document_handlers import (
    DocumentExpiryHandler,
    DocumentAcknowledgmentHandler
)

logger = logging.getLogger('notifications.consumers')

class EventConsumer:
    """
    Kafka consumer for processing notification events
    """

    def __init__(self):
        # Register all event handlers
        self.event_handlers = {
            # Authentication Events
            'user.registration.completed': UserRegistrationHandler(),
            'user.password.reset.requested': PasswordResetHandler(),
            'user.login.succeeded': LoginSecurityHandler(),
            'user.login.failed': LoginSecurityHandler(),

            # Application Events
            'invoice.payment.failed': InvoicePaymentHandler(),
            'task.assigned': TaskAssignmentHandler(),
            'comment.mentioned': CommentMentionHandler(),
            'content.liked': ContentEngagementHandler(),

            # Security Events
            'auth.2fa.code.requested': TwoFactorAuthHandler(),
            'auth.2fa.attempt.failed': TwoFactorAuthHandler(),
            'auth.2fa.method.changed': TwoFactorAuthHandler(),

            # Document Events
            'user.document.expiry.warning': DocumentExpiryHandler(),
            'user.document.expired': DocumentExpiryHandler(),
            'document.acknowledged': DocumentAcknowledgmentHandler(),

            # User Data Change Events
            'user.profile.updated': UserProfileUpdateHandler(),
            'user.account.locked': UserAccountActionHandler(),
            'user.account.unlocked': UserAccountActionHandler(),
            'user.account.suspended': UserAccountActionHandler(),
            'user.account.activated': UserAccountActionHandler(),
            'user.password.changed': UserPasswordChangeHandler(),

            # Review Events
            'reviews.approved': ReviewApprovedHandler(),
            'reviews.qr_scanned': ReviewQRScannedHandler(),
        }

        logger.info(f"Registered {len(self.event_handlers)} event handlers")

    def process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process a single event from Kafka

        Args:
            event_data: The event message from Kafka

        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Validate event structure
            if not self._validate_event_structure(event_data):
                logger.error(f"Invalid event structure: {event_data}")
                return False

            event_type = event_data['event_type']
            tenant_id = event_data['tenant_id']

            logger.info(f"Processing event: {event_type} for tenant: {tenant_id}")

            # Get the appropriate handler
            handler = self.event_handlers.get(event_type)
            if not handler:
                logger.warning(f"No handler found for event type: {event_type}")
                return False

            # Process the event
            result = handler.process_event(event_data)

            if result:
                logger.info(f"Successfully processed event: {event_type}")
                return True
            else:
                logger.error(f"Failed to process event: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            return False

    def _validate_event_structure(self, event_data: Dict[str, Any]) -> bool:
        """
        Validate that the event has the required structure

        Args:
            event_data: Event data to validate

        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ['event_type', 'tenant_id', 'payload', 'timestamp']

        for field in required_fields:
            if field not in event_data:
                logger.error(f"Missing required field: {field}")
                return False

        # Validate event_type format
        event_type = event_data['event_type']
        if not isinstance(event_type, str) or '.' not in event_type:
            logger.error(f"Invalid event_type format: {event_type}")
            return False

        # Validate tenant_id
        if not isinstance(event_data['tenant_id'], str):
            logger.error("tenant_id must be a string")
            return False

        # Validate payload
        if not isinstance(event_data['payload'], dict):
            logger.error("payload must be a dictionary")
            return False

        return True

    def get_supported_events(self) -> list:
        """Get list of all supported event types"""
        return list(self.event_handlers.keys())

    def get_handler_for_event(self, event_type: str):
        """Get the handler for a specific event type"""
        return self.event_handlers.get(event_type)


# Global consumer instance
event_consumer = EventConsumer()