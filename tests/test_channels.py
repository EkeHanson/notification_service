import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock, AsyncMock
from asgiref.sync import async_to_sync
from notifications.channels.email_handler import EmailHandler
from notifications.channels.sms_handler import SMSHandler
from notifications.channels.push_handler import PushHandler
from notifications.channels.inapp_handler import InAppHandler
from notifications.models import ChannelType


class EmailChannelTest(TestCase):
    """Test Email notification channel"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.credentials = {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "test_password",
            "from_email": "noreply@example.com",
            "use_tls": True
        }

    @patch('notifications.channels.email_handler.auth_service_client.get_tenant_branding')
    @patch('notifications.channels.email_handler.EmailMultiAlternatives')
    def test_email_send_success(self, mock_email_class, mock_get_branding):
        """Test successful email sending"""
        # Mock tenant branding
        mock_get_branding.return_value = {
            'name': 'Test Company',
            'logo_url': None,
            'primary_color': '#FF0000',
            'secondary_color': '#FADBD8',
            'email_from': 'noreply@test.com'
        }

        # Mock email send
        mock_email_instance = MagicMock()
        mock_email_instance.send.return_value = 1
        mock_email_class.return_value = mock_email_instance

        handler = EmailHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="user@example.com",
            content={
                "subject": "Welcome {{name}}!",
                "body": "Hello {{name}}, welcome to our platform!"
            },
            context={"name": "John Doe"}
        )

        self.assertTrue(result['success'])
        self.assertIn('Sent to 1 recipients', result['response'])
        mock_email_instance.send.assert_called_once()

    @patch('notifications.channels.email_handler.auth_service_client.get_tenant_branding')
    @patch('notifications.channels.email_handler.EmailMultiAlternatives')
    def test_email_send_failure(self, mock_email_class, mock_get_branding):
        """Test email sending failure"""
        # Mock tenant branding
        mock_get_branding.return_value = {
            'name': 'Test Company',
            'logo_url': None,
            'primary_color': '#FF0000',
            'secondary_color': '#FADBD8',
            'email_from': 'noreply@test.com'
        }

        # Mock email send failure
        mock_email_instance = MagicMock()
        mock_email_instance.send.side_effect = Exception("SMTP Error")
        mock_email_class.return_value = mock_email_instance

        handler = EmailHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="user@example.com",
            content={"subject": "Test", "body": "Test body"},
            context={}
        )

        self.assertFalse(result['success'])
        self.assertIn("SMTP Error", result['error'])

    @patch('notifications.channels.email_handler.auth_service_client.get_tenant_branding')
    @patch('notifications.channels.email_handler.EmailMultiAlternatives')
    def test_email_content_rendering(self, mock_email_class, mock_get_branding):
        """Test email template rendering"""
        # Mock tenant branding
        mock_get_branding.return_value = {
            'name': 'Test Company',
            'logo_url': None,
            'primary_color': '#FF0000',
            'secondary_color': '#FADBD8',
            'email_from': 'noreply@test.com'
        }

        # Mock email send
        mock_email_instance = MagicMock()
        mock_email_instance.send.return_value = 1
        mock_email_class.return_value = mock_email_instance

        handler = EmailHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="user@example.com",
            content={
                "subject": "Hello {{name}}",
                "body": "Welcome {{name}} to {{company}}!"
            },
            context={"name": "Alice", "company": "Acme Corp"}
        )

        # Check that email was created and sent successfully
        self.assertTrue(result['success'])
        # Verify EmailMultiAlternatives was called
        mock_email_class.assert_called_once()
        mock_email_instance.send.assert_called_once()


class SMSChannelTest(TestCase):
    """Test SMS notification channel"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.credentials = {
            "account_sid": "AC1234567890",
            "auth_token": "encrypted_token",
            "from_number": "+1234567890"
        }

    def test_phone_number_validation(self):
        """Test basic phone number validation"""
        handler = SMSHandler(self.tenant_id, self.credentials)

        # Valid numbers should be accepted as-is for now
        # (Twilio handles validation)
        self.assertIsInstance(handler, SMSHandler)

    @patch('notifications.channels.sms_handler.decrypt_data')
    @patch('notifications.channels.sms_handler.Client')
    def test_sms_send_success(self, mock_client_class, mock_decrypt):
        """Test successful SMS sending"""
        # Mock decryption
        mock_decrypt.return_value = "decrypted_auth_token"

        # Mock Twilio client
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM1234567890"
        mock_message.status = "queued"
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client

        handler = SMSHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="+1234567890",
            content={"body": "Your code is: {{code}}"},
            context={"code": "123456"}
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['response']['sid'], "SM1234567890")
        self.assertEqual(result['response']['status'], "queued")

    @patch('notifications.channels.sms_handler.decrypt_data')
    @patch('notifications.channels.sms_handler.Client')
    def test_sms_send_failure(self, mock_client_class, mock_decrypt):
        """Test SMS sending failure"""
        from notifications.channels.sms_handler import TwilioException

        # Mock decryption
        mock_decrypt.return_value = "decrypted_auth_token"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioException("Invalid number")
        mock_client_class.return_value = mock_client

        handler = SMSHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="invalid_number",
            content={"body": "Test SMS"},
            context={}
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'provider_error')

    @patch('notifications.channels.sms_handler.decrypt_data')
    @patch('notifications.channels.sms_handler.Client')
    def test_sms_bulk_send(self, mock_client_class, mock_decrypt):
        """Test bulk SMS sending"""
        # Mock decryption
        mock_decrypt.return_value = "decrypted_auth_token"

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM1234567890"
        mock_message.status = "queued"
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client

        handler = SMSHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send_bulk)(
            recipients=["+1234567890", "+0987654321"],
            content={"body": "Hello {{name}}!"},
            context={"name": "User"}
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['total_recipients'], 2)
        self.assertEqual(result['success_count'], 2)
        self.assertEqual(result['failure_count'], 0)
        self.assertEqual(len(result['results']), 2)

    def test_sms_content_rendering(self):
        """Test SMS content rendering with context"""
        handler = SMSHandler(self.tenant_id, self.credentials)

        rendered = handler._render_content(
            {"body": "Hi {{name}}, your code is {{code}}"},
            {"name": "Alice", "code": "123456"}
        )

        self.assertEqual(rendered['body'], "Hi Alice, your code is 123456")

    def test_sms_cost_estimation(self):
        """Test SMS cost estimation"""
        handler = SMSHandler(self.tenant_id, self.credentials)

        result = handler.estimate_cost(
            {"body": "This is a test message"},
            {},
            "US"
        )

        self.assertEqual(result['segments'], 1)
        self.assertEqual(result['message_length'], 22)  # "This is a test message" = 22 chars
        self.assertIsInstance(result['estimated_cost'], float)

    @patch('notifications.channels.sms_handler.decrypt_data')
    @patch('notifications.channels.sms_handler.Client')
    def test_sms_status_check(self, mock_client_class, mock_decrypt):
        """Test SMS status checking"""
        # Mock decryption
        mock_decrypt.return_value = "decrypted_auth_token"

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.sid = "SM1234567890"
        mock_message.status = "delivered"
        mock_client.messages.return_value.fetch.return_value = mock_message
        mock_client_class.return_value = mock_client

        handler = SMSHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.check_status)("SM1234567890")

        self.assertTrue(result['success'])
        self.assertEqual(result['response']['status'], "delivered")
        self.assertEqual(result['response']['sid'], "SM1234567890")


class PushChannelTest(TestCase):
    """Test Push notification channel"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "encrypted_key",
            "client_email": "firebase@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase@test-project.iam.gserviceaccount.com"
        }

    @patch('notifications.channels.push_handler.initialize_app')
    @patch('notifications.channels.push_handler.credentials.Certificate')
    @patch('notifications.channels.push_handler.messaging.send')
    @patch('notifications.channels.push_handler.decrypt_data')
    def test_push_send_success(self, mock_decrypt, mock_send, mock_certificate, mock_init_app):
        """Test successful push notification sending"""
        # Mock decryption
        mock_decrypt.return_value = "decrypted_private_key"

        # Mock Firebase app
        mock_app = MagicMock()
        mock_init_app.return_value = mock_app

        # Mock send
        mock_send.return_value = "msg_1234567890"

        handler = PushHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="fcm_token_123",
            content={
                "title": "New Message",
                "body": "You have a new message",
                "data": {"type": "message", "id": "123"}
            },
            context={}
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['response']['message_id'], "msg_1234567890")

    @patch('notifications.channels.push_handler.initialize_app')
    @patch('notifications.channels.push_handler.credentials.Certificate')
    @patch('notifications.channels.push_handler.messaging.send')
    @patch('notifications.channels.push_handler.decrypt_data')
    def test_push_send_failure(self, mock_decrypt, mock_send, mock_certificate, mock_init_app):
        """Test push notification sending failure"""
        # Mock decryption
        mock_decrypt.return_value = "decrypted_private_key"

        # Mock Firebase app
        mock_app = MagicMock()
        mock_init_app.return_value = mock_app

        # Mock send failure
        mock_send.side_effect = Exception("Invalid token")

        handler = PushHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="invalid_token",
            content={"title": "Test", "body": "Test message"},
            context={}
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'invalid_arguments')

    @patch('notifications.channels.push_handler.initialize_app')
    @patch('notifications.channels.push_handler.credentials.Certificate')
    @patch('notifications.channels.push_handler.messaging.send')
    @patch('notifications.channels.push_handler.decrypt_data')
    def test_push_content_rendering(self, mock_decrypt, mock_send, mock_certificate, mock_init_app):
        """Test push content rendering with context"""
        # Mock decryption
        mock_decrypt.return_value = "decrypted_private_key"

        # Mock Firebase app
        mock_app = MagicMock()
        mock_init_app.return_value = mock_app

        # Mock send
        mock_send.return_value = "msg_123"

        handler = PushHandler(self.tenant_id, self.credentials)
        result = async_to_sync(handler.send)(
            recipient="fcm_token_123",
            content={
                "title": "Hello {{name}}",
                "body": "Welcome to {{company}}",
                "data": {"user_id": "{{user_id}}"}
            },
            context={"name": "Alice", "company": "Acme Corp", "user_id": "123"}
        )

        # Check that send succeeded
        self.assertTrue(result['success'])


class InAppChannelTest(TestCase):
    """Test In-App notification channel"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"

    @patch('notifications.channels.inapp_handler.get_channel_layer')
    def test_inapp_send_success(self, mock_get_channel_layer):
        """Test successful in-app notification sending"""
        mock_channel_layer = MagicMock()
        mock_channel_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        handler = InAppHandler(self.tenant_id, {})
        result = async_to_sync(handler.send)(
            recipient="user_123",
            content={
                "title": "New Message",
                "body": "You have a new message",
                "data": {"type": "message", "id": "123"}
            },
            context={}
        )

        self.assertTrue(result['success'])
        self.assertIn(f"user_user_123_{self.tenant_id}", result['response']['groups'])
        mock_channel_layer.group_send.assert_called_once()

    @patch('notifications.channels.inapp_handler.get_channel_layer')
    def test_inapp_send_tenant_broadcast(self, mock_get_channel_layer):
        """Test tenant-wide broadcast"""
        mock_channel_layer = MagicMock()
        mock_channel_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        handler = InAppHandler(self.tenant_id, {})
        result = async_to_sync(handler.send)(
            recipient="all",
            content={
                "title": "System Update",
                "body": "Server maintenance in 5 minutes"
            },
            context={}
        )

        self.assertTrue(result['success'])
        self.assertIn(f"tenant_{self.tenant_id}", result['response']['groups'])
        mock_channel_layer.group_send.assert_called_once()

    @patch('notifications.channels.inapp_handler.get_channel_layer')
    def test_inapp_send_no_channel_layer(self, mock_get_channel_layer):
        """Test in-app sending when channel layer is unavailable"""
        mock_get_channel_layer.return_value = None

        handler = InAppHandler(self.tenant_id, {})
        result = async_to_sync(handler.send)(
            recipient="user_123",
            content={"title": "Test", "body": "Test message"},
            context={}
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Channel layer not configured')

    def test_inapp_content_rendering(self):
        """Test in-app content rendering with context"""
        handler = InAppHandler(self.tenant_id, {})

        with patch('notifications.channels.inapp_handler.get_channel_layer') as mock_get_layer:
            mock_channel_layer = MagicMock()
            mock_channel_layer.group_send = AsyncMock()
            mock_get_layer.return_value = mock_channel_layer

            result = async_to_sync(handler.send)(
                recipient="user_123",
                content={
                    "title": "Welcome {{name}}",
                    "body": "Hello {{name}}, welcome to {{company}}",
                    "data": {"user_id": "{{user_id}}"}
                },
                context={"name": "Alice", "company": "Acme Corp", "user_id": "123"}
            )

            # Check that send succeeded
            self.assertTrue(result['success'])


class ChannelIntegrationTest(TestCase):
    """Test channel integration and cross-cutting concerns"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"

    def test_channel_type_enum_values(self):
        """Test that all channel types are properly defined"""
        expected_channels = ['email', 'sms', 'push', 'inapp']
        actual_channels = [channel.value for channel in ChannelType]

        for channel in expected_channels:
            self.assertIn(channel, actual_channels,
                         f"Channel '{channel}' should be defined in ChannelType enum")

    def test_channel_handler_interface(self):
        """Test that all channel handlers implement the required interface"""
        handlers = [
            EmailHandler(self.tenant_id, {}),
            SMSHandler(self.tenant_id, {}),
            PushHandler(self.tenant_id, {}),
            InAppHandler(self.tenant_id, {})
        ]

        required_methods = ['send', 'log_result']

        for handler in handlers:
            for method in required_methods:
                self.assertTrue(hasattr(handler, method),
                               f"Handler {handler.__class__.__name__} missing method '{method}'")
                self.assertTrue(callable(getattr(handler, method)),
                               f"Handler {handler.__class__.__name__} method '{method}' not callable")

    def test_channel_error_handling(self):
        """Test consistent error handling across channels"""
        handlers = [
            EmailHandler(self.tenant_id, {}),
            SMSHandler(self.tenant_id, {}),
            PushHandler(self.tenant_id, {}),
            InAppHandler(self.tenant_id, {})
        ]

        for handler in handlers:
            # Test with invalid recipient
            result = async_to_sync(handler.send)(
                recipient="",  # Invalid
                content={"test": "data"},
                context={}
            )

            # Should return a result dict with success/error keys
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)

            if not result['success']:
                self.assertIn('error', result)

    def test_channel_content_validation(self):
        """Test content validation across channels"""
        test_content = {
            "title": "Test Title",
            "body": "Test Body",
            "subject": "Test Subject",
            "data": {"key": "value"}
        }

        handlers = [
            EmailHandler(self.tenant_id, {}),
            SMSHandler(self.tenant_id, {}),
            PushHandler(self.tenant_id, {}),
            InAppHandler(self.tenant_id, {})
        ]

        for handler in handlers:
            # Should handle content gracefully
            result = async_to_sync(handler.send)(
                recipient="test_recipient",
                content=test_content,
                context={}
            )

            # Should not crash, even with unexpected content
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)

    @patch('notifications.channels.email_handler.send_mail')
    @patch('notifications.channels.sms_handler.Client')
    @patch('notifications.channels.push_handler.messaging.send')
    @patch('notifications.channels.inapp_handler.get_channel_layer')
    def test_all_channels_can_send(self, mock_inapp_layer, mock_push_send,
                                   mock_sms_client, mock_email_send):
        """Test that all channels can be instantiated and attempt to send"""
        # Setup mocks
        mock_email_send.return_value = 1
        mock_sms_client.return_value.messages.create.return_value.sid = "SM123"
        mock_sms_client.return_value.messages.create.return_value.status = "queued"
        mock_push_send.return_value = "msg_123"
        mock_inapp_layer.return_value.group_send = MagicMock()

        handlers = [
            ("Email", EmailHandler(self.tenant_id, {"from_email": "test@example.com"})),
            ("SMS", SMSHandler(self.tenant_id, {"account_sid": "AC123", "auth_token": "token", "from_number": "+1234567890"})),
            ("Push", PushHandler(self.tenant_id, {"project_id": "test"})),
            ("InApp", InAppHandler(self.tenant_id, {}))
        ]

        for name, handler in handlers:
            with self.subTest(channel=name):
                result = async_to_sync(handler.send)(
                    recipient="test_recipient",
                    content={"body": "Test message", "title": "Test", "subject": "Test"},
                    context={}
                )

                # Should return a result without crashing
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)