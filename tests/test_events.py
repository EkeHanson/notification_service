import json
from django.test import TestCase
from unittest.mock import patch, MagicMock
from notifications.events.base_handler import BaseEventHandler
from notifications.events.auth_handlers import (
    UserRegistrationHandler, PasswordResetHandler,
    LoginSecurityHandler
)
from notifications.events.app_handlers import (
    InvoicePaymentHandler, TaskAssignedHandler,
    CommentMentionedHandler, ContentLikedHandler
)
from notifications.events.security_handlers import (
    TwoFactorCodeHandler, TwoFactorFailureHandler,
    TwoFactorMethodChangedHandler
)
from notifications.models import ChannelType, NotificationRecord


class EventHandlerBaseTest(TestCase):
    """Test base event handler functionality"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    def test_base_handler_interface(self):
        """Test that base handler defines required interface"""
        handler = BaseEventHandler()

        # Should have required methods
        self.assertTrue(hasattr(handler, 'can_handle'))
        self.assertTrue(hasattr(handler, 'get_default_channels'))
        self.assertTrue(hasattr(handler, 'get_template_data'))
        self.assertTrue(hasattr(handler, 'get_recipient'))
        self.assertTrue(hasattr(handler, 'get_channel_content'))
        self.assertTrue(hasattr(handler, 'process_event'))

        # Should have default implementations
        self.assertEqual(handler.get_default_channels('test'), [])
        self.assertEqual(handler.priority, 'medium')

    def test_handler_registration(self):
        """Test event handler registration system"""
        from notifications.events import EVENT_HANDLERS

        # Should have handlers registered
        self.assertIsInstance(EVENT_HANDLERS, dict)
        self.assertGreater(len(EVENT_HANDLERS), 0)

        # Each handler should be a class
        for event_type, handler_class in EVENT_HANDLERS.items():
            self.assertTrue(issubclass(handler_class, BaseEventHandler))


class AuthenticationEventTest(TestCase):
    """Test authentication-related event handlers"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    def test_user_registration_handler(self):
        """Test user registration event handling"""
        handler = UserRegistrationHandler()

        # Should handle registration events
        self.assertTrue(handler.can_handle('user.registration.completed'))
        self.assertFalse(handler.can_handle('user.login.succeeded'))

        # Should use email and in-app channels
        channels = handler.get_default_channels('user.registration.completed')
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.INAPP, channels)

        # Test template data extraction
        event_payload = {
            'user_id': self.user_id,
            'email': 'user@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'verification_required': True
        }

        template_data = handler.get_template_data(event_payload)
        self.assertEqual(template_data['first_name'], 'John')
        self.assertEqual(template_data['email'], 'user@example.com')
        self.assertTrue(template_data['verification_required'])

        # Test email content generation
        email_content = handler._get_email_content('user.registration.completed', template_data)
        self.assertIn('Welcome John!', email_content['subject'])
        self.assertIn('Welcome John, welcome!', email_content['body'])

        # Test in-app content generation
        inapp_content = handler._get_inapp_content('user.registration.completed', template_data)
        self.assertEqual(inapp_content['title'], 'Welcome to our platform!')
        self.assertIn('account has been created', inapp_content['body'])

    def test_password_reset_handler(self):
        """Test password reset event handling"""
        handler = PasswordResetHandler()

        self.assertTrue(handler.can_handle('user.password.reset.requested'))
        self.assertEqual(handler.priority, 'high')

        # Should use email and SMS
        channels = handler.get_default_channels('user.password.reset.requested')
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.SMS, channels)

        # Test recipient extraction (can be email or phone)
        event_payload = {
            'email': 'user@example.com',
            'phone': '+1234567890'
        }

        self.assertEqual(handler.get_recipient(event_payload), 'user@example.com')

        # Test template data
        template_data = handler.get_template_data(event_payload)
        self.assertEqual(template_data['email'], 'user@example.com')
        self.assertEqual(template_data['phone'], '+1234567890')
        self.assertIn('reset_token', template_data)

    def test_login_security_handler(self):
        """Test login security event handling"""
        handler = LoginSecurityHandler()

        # Should handle both success and failure
        self.assertTrue(handler.can_handle('user.login.succeeded'))
        self.assertTrue(handler.can_handle('user.login.failed'))

        # Different channels for different events
        success_channels = handler.get_default_channels('user.login.succeeded')
        failure_channels = handler.get_default_channels('user.login.failed')

        self.assertIn(ChannelType.EMAIL, success_channels)
        self.assertIn(ChannelType.INAPP, success_channels)

        self.assertIn(ChannelType.EMAIL, failure_channels)
        self.assertIn(ChannelType.SMS, failure_channels)
        self.assertIn(ChannelType.PUSH, failure_channels)

        # Test failure event content
        event_payload = {
            'email': 'user@example.com',
            'failure_reason': 'invalid_password',
            'attempt_count': 3,
            'ip_address': '192.168.1.1'
        }

        template_data = handler.get_template_data(event_payload)
        self.assertEqual(template_data['failure_reason'], 'invalid_password')
        self.assertEqual(template_data['attempt_count'], 3)

        email_content = handler._get_email_content('user.login.failed', template_data)
        self.assertIn('Security Alert', email_content['subject'])
        self.assertIn('invalid_password', email_content['body'])


class ApplicationEventTest(TestCase):
    """Test application-related event handlers"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    def test_invoice_payment_handler(self):
        """Test invoice payment event handling"""
        handler = InvoicePaymentHandler()

        self.assertTrue(handler.can_handle('invoice.payment.failed'))
        self.assertEqual(handler.priority, 'high')

        # Should use multiple channels for payment failures
        channels = handler.get_default_channels('invoice.payment.failed')
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.SMS, channels)
        self.assertIn(ChannelType.PUSH, channels)

        event_payload = {
            'user_id': self.user_id,
            'invoice_id': 'inv_123',
            'amount': 99.99,
            'currency': 'USD',
            'failure_reason': 'insufficient_funds'
        }

        template_data = handler.get_template_data(event_payload)
        self.assertEqual(template_data['amount'], 99.99)
        self.assertEqual(template_data['failure_reason'], 'insufficient_funds')

    def test_task_assigned_handler(self):
        """Test task assignment event handling"""
        handler = TaskAssignedHandler()

        self.assertTrue(handler.can_handle('task.assigned'))
        self.assertEqual(handler.priority, 'medium')

        channels = handler.get_default_channels('task.assigned')
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.INAPP, channels)
        self.assertIn(ChannelType.PUSH, channels)

    def test_comment_mention_handler(self):
        """Test comment mention event handling"""
        handler = CommentMentionedHandler()

        self.assertTrue(handler.can_handle('comment.mentioned'))

        event_payload = {
            'user_id': self.user_id,
            'comment_text': 'Hey @john, check this out!',
            'author_name': 'Jane Smith',
            'entity_title': 'Project Proposal'
        }

        template_data = handler.get_template_data(event_payload)
        self.assertEqual(template_data['author_name'], 'Jane Smith')
        self.assertEqual(template_data['entity_title'], 'Project Proposal')

    def test_content_liked_handler(self):
        """Test content liked event handling"""
        handler = ContentLikedHandler()

        self.assertTrue(handler.can_handle('content.liked'))
        self.assertEqual(handler.priority, 'low')

        # Should only use in-app and push for likes
        channels = handler.get_default_channels('content.liked')
        self.assertIn(ChannelType.INAPP, channels)
        self.assertIn(ChannelType.PUSH, channels)
        self.assertNotIn(ChannelType.EMAIL, channels)  # Not for likes


class SecurityEventTest(TestCase):
    """Test security-related event handlers"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    def test_2fa_code_handler(self):
        """Test 2FA code request handling"""
        handler = TwoFactorCodeHandler()

        self.assertTrue(handler.can_handle('auth.2fa.code.requested'))
        self.assertEqual(handler.priority, 'high')

        # Should use SMS, email, and in-app
        channels = handler.get_default_channels('auth.2fa.code.requested')
        self.assertIn(ChannelType.SMS, channels)
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.INAPP, channels)

    def test_2fa_failure_handler(self):
        """Test 2FA failure handling"""
        handler = TwoFactorFailureHandler()

        self.assertTrue(handler.can_handle('auth.2fa.attempt.failed'))
        self.assertEqual(handler.priority, 'high')

        # Should use all channels for security alerts
        channels = handler.get_default_channels('auth.2fa.attempt.failed')
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.SMS, channels)
        self.assertIn(ChannelType.PUSH, channels)

    def test_2fa_method_changed_handler(self):
        """Test 2FA method change handling"""
        handler = TwoFactorMethodChangedHandler()

        self.assertTrue(handler.can_handle('auth.2fa.method.changed'))
        self.assertEqual(handler.priority, 'medium')

        channels = handler.get_default_channels('auth.2fa.method.changed')
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.SMS, channels)
        self.assertIn(ChannelType.INAPP, channels)


class EventProcessingTest(TestCase):
    """Test end-to-end event processing"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    @patch('notifications.tasks.send_notification_task.delay')
    def test_user_registration_event_processing(self, mock_task):
        """Test complete user registration event processing"""
        handler = UserRegistrationHandler()

        event = {
            'event_type': 'user.registration.completed',
            'tenant_id': self.tenant_id,
            'payload': {
                'user_id': self.user_id,
                'email': 'user@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'verification_required': True
            }
        }

        result = handler.process_event(event)

        # Should create notifications
        self.assertIsNotNone(result)

        # Should have queued notification tasks
        self.assertEqual(mock_task.call_count, 2)  # Email and in-app

        # Check notification records were created
        notifications = NotificationRecord.objects.filter(
            tenant_id=self.tenant_id,
            recipient='user@example.com'
        )
        self.assertEqual(notifications.count(), 2)

        # Check channels
        channels = notifications.values_list('channel', flat=True)
        self.assertIn(ChannelType.EMAIL, channels)
        self.assertIn(ChannelType.INAPP, channels)

    @patch('notifications.tasks.send_notification_task.delay')
    def test_payment_failure_event_processing(self, mock_task):
        """Test payment failure event processing"""
        handler = InvoicePaymentHandler()

        event = {
            'event_type': 'invoice.payment.failed',
            'tenant_id': self.tenant_id,
            'payload': {
                'user_id': self.user_id,
                'email': 'user@example.com',
                'phone': '+1234567890',
                'invoice_id': 'inv_123',
                'amount': 99.99,
                'failure_reason': 'insufficient_funds'
            }
        }

        result = handler.process_event(event)

        self.assertIsNotNone(result)
        self.assertEqual(mock_task.call_count, 3)  # Email, SMS, Push

        # Check all channels were used
        notifications = NotificationRecord.objects.filter(
            tenant_id=self.tenant_id
        )
        channels = set(notifications.values_list('channel', flat=True))
        expected_channels = {ChannelType.EMAIL, ChannelType.SMS, ChannelType.PUSH}
        self.assertEqual(channels, expected_channels)

    def test_event_handler_error_handling(self):
        """Test event handler error handling"""
        handler = UserRegistrationHandler()

        # Test with missing payload
        result = handler.process_event({
            'event_type': 'user.registration.completed',
            'tenant_id': self.tenant_id
        })

        self.assertIsNone(result)  # Should handle gracefully

        # Test with invalid event type
        result = handler.process_event({
            'event_type': 'invalid.event',
            'tenant_id': self.tenant_id,
            'payload': {}
        })

        self.assertIsNone(result)  # Should not handle invalid events

    def test_template_context_injection(self):
        """Test template context injection in events"""
        handler = TaskAssignedHandler()

        event_payload = {
            'user_id': self.user_id,
            'task_title': 'Review Report',
            'assigned_by': 'manager@example.com',
            'due_date': '2024-01-15T17:00:00Z',
            'priority': 'high'
        }

        template_data = handler.get_template_data(event_payload)

        # Test context injection
        email_content = handler._get_email_content('task.assigned', template_data)
        self.assertIn('Review Report', email_content['body'])
        self.assertIn('manager@example.com', email_content['body'])
        self.assertIn('high', email_content['body'])

    def test_event_priority_handling(self):
        """Test event priority handling"""
        handlers = [
            (UserRegistrationHandler(), 'high'),
            (PasswordResetHandler(), 'high'),
            (TaskAssignedHandler(), 'medium'),
            (ContentLikedHandler(), 'low')
        ]

        for handler, expected_priority in handlers:
            self.assertEqual(handler.priority, expected_priority,
                           f"{handler.__class__.__name__} should have {expected_priority} priority")


class EventIntegrationTest(TestCase):
    """Test event system integration"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    @patch('notifications.events.base_handler.BaseEventHandler.process_event')
    def test_event_router_integration(self, mock_process):
        """Test event routing to appropriate handlers"""
        from notifications.events import EVENT_HANDLERS

        # Test that all supported events have handlers
        supported_events = [
            'user.registration.completed',
            'user.password.reset.requested',
            'user.login.succeeded',
            'user.login.failed',
            'invoice.payment.failed',
            'task.assigned',
            'comment.mentioned',
            'content.liked',
            'auth.2fa.code.requested',
            'auth.2fa.attempt.failed',
            'auth.2fa.method.changed'
        ]

        for event_type in supported_events:
            self.assertIn(event_type, EVENT_HANDLERS,
                         f"No handler registered for event: {event_type}")

            handler_class = EVENT_HANDLERS[event_type]
            handler = handler_class()

            self.assertTrue(handler.can_handle(event_type),
                          f"Handler {handler_class.__name__} should handle {event_type}")

    def test_event_payload_validation(self):
        """Test event payload validation"""
        handler = UserRegistrationHandler()

        # Valid payload
        valid_event = {
            'event_type': 'user.registration.completed',
            'tenant_id': self.tenant_id,
            'payload': {
                'user_id': self.user_id,
                'email': 'user@example.com',
                'first_name': 'John'
            }
        }

        result = handler.process_event(valid_event)
        # Should process without errors (mocked)

        # Invalid payload - missing required fields
        invalid_event = {
            'event_type': 'user.registration.completed',
            'tenant_id': self.tenant_id,
            'payload': {}  # Missing required fields
        }

        result = handler.process_event(invalid_event)
        # Should handle gracefully

    def test_tenant_isolation_in_events(self):
        """Test tenant isolation in event processing"""
        handler1 = UserRegistrationHandler()
        handler2 = UserRegistrationHandler()

        event1 = {
            'event_type': 'user.registration.completed',
            'tenant_id': 'tenant1',
            'payload': {'user_id': 'user1', 'email': 'user1@example.com'}
        }

        event2 = {
            'event_type': 'user.registration.completed',
            'tenant_id': 'tenant2',
            'payload': {'user_id': 'user2', 'email': 'user2@example.com'}
        }

        # Process events for different tenants
        handler1.process_event(event1)
        handler2.process_event(event2)

        # Check that notifications were created for correct tenants
        notifications1 = NotificationRecord.objects.filter(tenant_id='tenant1')
        notifications2 = NotificationRecord.objects.filter(tenant_id='tenant2')

        # Should be isolated (though mocked, this tests the logic)
        self.assertNotEqual(notifications1.count(), notifications2.count())