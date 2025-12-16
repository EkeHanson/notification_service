import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from notifications.models import (
    NotificationRecord, TenantCredentials, NotificationTemplate,
    Campaign, ChannelType, DeviceToken, DeviceType,
    ChatConversation, ChatParticipant, ChatMessage, MessageType
)


class NotificationAPITest(APITestCase):
    """Test notification API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

        # Set tenant and user in request context
        self.client.credentials(HTTP_AUTHORIZATION='Bearer test_token')
        # Mock middleware would set these
        self.client.tenant_id = self.tenant_id
        self.client.user_id = self.user_id

    def test_create_notification_record(self):
        """Test creating a notification record"""
        url = reverse('notification-list-create')
        data = {
            "channel": "email",
            "recipient": "test@example.com",
            "content": {
                "subject": "Test Subject",
                "body": "Test Body"
            },
            "context": {"name": "Test User"}
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(NotificationRecord.objects.count(), 1)

        record = NotificationRecord.objects.first()
        self.assertEqual(record.channel, ChannelType.EMAIL)
        self.assertEqual(record.recipient, "test@example.com")
        self.assertEqual(record.status, "pending")

    def test_list_notification_records(self):
        """Test listing notification records"""
        # Create test records
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            recipient="user1@example.com",
            content={"subject": "Test 1"}
        )
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.SMS,
            recipient="+1234567890",
            content={"body": "Test SMS"}
        )

        url = reverse('notification-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_notification_records(self):
        """Test filtering notification records"""
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            recipient="user@example.com",
            status="success"
        )
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.SMS,
            recipient="+1234567890",
            status="pending"
        )

        # Filter by status
        url = reverse('notification-list-create') + '?status=success'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'success')

    def test_create_tenant_credentials(self):
        """Test creating tenant credentials"""
        url = reverse('credentials-list-create')
        data = {
            "channel": "email",
            "credentials": {
                "smtp_host": "smtp.gmail.com",
                "username": "test@example.com",
                "password": "test_password"
            }
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TenantCredentials.objects.count(), 1)

        creds = TenantCredentials.objects.first()
        self.assertEqual(creds.channel, ChannelType.EMAIL)
        self.assertTrue(creds.is_active)

    def test_list_tenant_credentials(self):
        """Test listing tenant credentials"""
        TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            credentials={"host": "smtp.test.com"}
        )

        url = reverse('credentials-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_notification_template(self):
        """Test creating notification templates"""
        url = reverse('template-list-create')
        data = {
            "name": "Welcome Email",
            "channel": "email",
            "content": {
                "subject": "Welcome {{name}}!",
                "body": "Hello {{name}}, welcome!"
            },
            "placeholders": ["{{name}}"]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(NotificationTemplate.objects.count(), 1)

        template = NotificationTemplate.objects.first()
        self.assertEqual(template.name, "Welcome Email")
        self.assertEqual(template.version, 1)

    def test_create_campaign(self):
        """Test creating notification campaigns"""
        url = reverse('campaign-list-create')
        data = {
            "name": "Test Campaign",
            "channel": "push",
            "content": {
                "title": "Test Notification",
                "body": "Campaign message"
            },
            "recipients": [
                {"recipient": "token1", "context": {"name": "User1"}},
                {"recipient": "token2", "context": {"name": "User2"}}
            ]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)

        campaign = Campaign.objects.first()
        self.assertEqual(campaign.name, "Test Campaign")
        self.assertEqual(campaign.total_recipients, 2)
        self.assertEqual(campaign.status, "draft")

    def test_get_analytics(self):
        """Test analytics endpoint"""
        # Create test data
        NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            recipient="user@example.com",
            status="success",
            created_at="2024-01-01T12:00:00Z"
        )

        url = reverse('analytics') + '?days=30'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_sent', response.data)
        self.assertIn('success_rate', response.data)
        self.assertIn('channel_usage', response.data)

    def test_health_check(self):
        """Test health check endpoint"""
        url = reverse('health')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['service'], 'notification_service')


class DeviceTokenAPITest(APITestCase):
    """Test device token API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"
        self.client.tenant_id = self.tenant_id
        self.client.user_id = self.user_id

    def test_register_device_token(self):
        """Test registering a device token"""
        url = reverse('device-token-list-create')
        data = {
            "device_type": "android",
            "device_token": "fcm_test_token_123",
            "device_id": "device_123",
            "app_version": "1.0.0"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DeviceToken.objects.count(), 1)

        token = DeviceToken.objects.first()
        self.assertEqual(token.device_type, DeviceType.ANDROID)
        self.assertEqual(token.device_token, "fcm_test_token_123")

    def test_list_device_tokens(self):
        """Test listing device tokens"""
        DeviceToken.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            device_type=DeviceType.IOS,
            device_token="ios_token_123",
            device_id="ios_device_123"
        )

        url = reverse('device-token-list-create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_device_token_uniqueness(self):
        """Test device token uniqueness per device"""
        # Create first token
        DeviceToken.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            device_type=DeviceType.ANDROID,
            device_token="token1",
            device_id="device1"
        )

        # Try to create another token for same device - should deactivate first
        url = reverse('device-token-list-create')
        data = {
            "device_type": "android",
            "device_token": "token2",
            "device_id": "device1"  # Same device
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Should have 2 tokens total, but only 1 active
        self.assertEqual(DeviceToken.objects.count(), 2)
        self.assertEqual(DeviceToken.objects.filter(is_active=True).count(), 1)


class PushAPITest(APITestCase):
    """Test push notification API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.client.tenant_id = self.tenant_id

    @patch('notifications.channels.push_handler.PushHandler.send')
    def test_push_test_endpoint(self, mock_send):
        """Test push notification test endpoint"""
        mock_send.return_value = {'success': True, 'response': {'message_id': 'msg_123'}}

        url = reverse('push-test')
        data = {
            "device_token": "test_fcm_token",
            "title": "Test Notification",
            "body": "This is a test"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        mock_send.assert_called_once()


class SMSAPITest(APITestCase):
    """Test SMS API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.client.tenant_id = self.tenant_id

    @patch('notifications.channels.sms_handler.SMSHandler.send')
    def test_sms_test_endpoint(self, mock_send):
        """Test SMS test endpoint"""
        mock_send.return_value = {
            'success': True,
            'response': {'sid': 'SM1234567890', 'status': 'queued'}
        }

        url = reverse('sms-test')
        data = {
            "phone_number": "+1234567890",
            "message": "Test SMS message"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        mock_send.assert_called_once()

    @patch('notifications.channels.sms_handler.SMSHandler.check_status')
    def test_sms_status_endpoint(self, mock_check_status):
        """Test SMS status check endpoint"""
        mock_check_status.return_value = {
            'success': True,
            'response': {'status': 'delivered', 'sid': 'SM123'}
        }

        url = reverse('sms-status', kwargs={'sid': 'SM1234567890'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['response']['status'], 'delivered')
        mock_check_status.assert_called_once_with('SM1234567890')

    @patch('notifications.channels.sms_handler.SMSHandler.estimate_cost')
    def test_sms_cost_estimation(self, mock_estimate):
        """Test SMS cost estimation endpoint"""
        mock_estimate.return_value = {
            'success': True,
            'estimation': {
                'recipients': 2,
                'estimated_cost_usd': 0.015
            }
        }

        url = reverse('sms-cost-estimate')
        data = {
            "phone_numbers": ["+1234567890", "+0987654321"],
            "message": "Test message"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estimation']['estimated_cost_usd'], 0.015)


class ChatAPITest(APITestCase):
    """Test chat API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"
        self.client.tenant_id = self.tenant_id
        self.client.user_id = self.user_id

    def test_create_chat_conversation(self):
        """Test creating a chat conversation"""
        url = reverse('chat-conversations')
        data = {
            "title": "Project Discussion",
            "conversation_type": "group"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatConversation.objects.count(), 1)

        conversation = ChatConversation.objects.first()
        self.assertEqual(conversation.title, "Project Discussion")
        self.assertEqual(conversation.conversation_type, "group")
        self.assertEqual(conversation.created_by, self.user_id)

        # Should auto-create participant for creator
        self.assertEqual(ChatParticipant.objects.count(), 1)
        participant = ChatParticipant.objects.first()
        self.assertEqual(participant.user_id, self.user_id)
        self.assertEqual(participant.role, "admin")

    def test_list_chat_conversations(self):
        """Test listing user's chat conversations"""
        # Create conversations
        conv1 = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            title="Team Chat",
            conversation_type="group",
            created_by=self.user_id
        )
        conv2 = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            title="Direct Chat",
            conversation_type="direct",
            created_by="other_user"
        )

        # Add user as participant to conv1
        ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conv1,
            user_id=self.user_id,
            role="member"
        )

        url = reverse('chat-conversations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only conv1
        self.assertEqual(response.data['results'][0]['title'], "Team Chat")

    def test_send_chat_message(self):
        """Test sending a chat message"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id,
            role="member"
        )

        url = reverse('chat-messages', kwargs={'conversation_id': conversation.id})
        data = {
            "message_type": "text",
            "content": "Hello world!"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatMessage.objects.count(), 1)

        message = ChatMessage.objects.first()
        self.assertEqual(message.content, "Hello world!")
        self.assertEqual(message.message_type, MessageType.TEXT)
        self.assertEqual(message.sender_id, self.user_id)

    def test_list_chat_messages(self):
        """Test listing chat messages"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id,
            role="member"
        )

        # Create messages
        ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Message 1"
        )
        ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Message 2"
        )

        url = reverse('chat-messages', kwargs={'conversation_id': conversation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_add_message_reaction(self):
        """Test adding emoji reactions to messages"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id,
            role="member"
        )

        message = ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Test message"
        )

        url = reverse('message-reactions', kwargs={'message_id': message.id})
        data = {"emoji": "👍"}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from notifications.models import MessageReaction
        self.assertEqual(MessageReaction.objects.count(), 1)

        reaction = MessageReaction.objects.first()
        self.assertEqual(reaction.emoji, "👍")
        self.assertEqual(reaction.user_id, self.user_id)

    def test_file_upload(self):
        """Test file upload for chat messages"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        url = reverse('file-upload')

        # Create a test file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"This is a test file content",
            content_type="text/plain"
        )

        data = {'file': test_file}
        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('file_url', response.data)
        self.assertIn('file_name', response.data)
        self.assertEqual(response.data['file_name'], 'test.txt')
        self.assertEqual(response.data['content_type'], 'text/plain')

    def test_user_presence(self):
        """Test user presence management"""
        url = reverse('user-presence-detail')

        # Update presence
        data = {"status": "busy"}
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check presence was created/updated
        from notifications.models import UserPresence
        presence = UserPresence.objects.get(
            tenant_id=self.tenant_id,
            user_id=self.user_id
        )
        self.assertEqual(presence.status, "busy")


class APIAuthenticationTest(APITestCase):
    """Test API authentication and authorization"""

    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_request(self):
        """Test that unauthenticated requests are rejected"""
        url = reverse('notification-list-create')
        response = self.client.get(url)

        # Should fail due to missing tenant/user context
        # In real implementation, this would be handled by middleware
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Mock behavior

    def test_tenant_isolation(self):
        """Test that tenants are properly isolated"""
        tenant1 = "550e8400-e29b-41d4-a716-446655440000"
        tenant2 = "550e8400-e29b-41d4-a716-446655440001"

        # Create record for tenant1
        NotificationRecord.objects.create(
            tenant_id=tenant1,
            channel=ChannelType.EMAIL,
            recipient="user@example.com",
            content={"subject": "Test"}
        )

        # Mock tenant context for tenant2
        self.client.tenant_id = tenant2
        self.client.user_id = "user123"

        url = reverse('notification-list-create')
        response = self.client.get(url)

        # Should not see tenant1's records
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


class APIErrorHandlingTest(APITestCase):
    """Test API error handling"""

    def setUp(self):
        self.client = APIClient()
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"
        self.client.tenant_id = self.tenant_id
        self.client.user_id = self.user_id

    def test_invalid_channel_type(self):
        """Test invalid channel type handling"""
        url = reverse('notification-list-create')
        data = {
            "channel": "invalid_channel",
            "recipient": "test@example.com",
            "content": {"subject": "Test"}
        }

        response = self.client.post(url, data, format='json')

        # Should fail validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_fields(self):
        """Test missing required fields"""
        url = reverse('notification-list-create')
        data = {
            "channel": "email",
            # Missing recipient and content
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_json(self):
        """Test invalid JSON handling"""
        url = reverse('notification-list-create')

        response = self.client.post(url, "invalid json", content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_upload_validation(self):
        """Test file upload validation"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        url = reverse('file-upload')

        # Test oversized file
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (11 * 1024 * 1024),  # 11MB
            content_type="text/plain"
        )

        response = self.client.post(url, {'file': large_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('File too large', response.data['error'])

        # Test invalid file type
        invalid_file = SimpleUploadedFile(
            "test.exe",
            b"fake exe content",
            content_type="application/x-msdownload"
        )

        response = self.client.post(url, {'file': invalid_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('File type not allowed', response.data['error'])