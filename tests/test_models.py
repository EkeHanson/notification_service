import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from notifications.models import (
    NotificationRecord, TenantCredentials, NotificationTemplate,
    Campaign, CampaignStatus, ChannelType, NotificationStatus,
    FailureReason, DeviceToken, DeviceType, PushAnalytics,
    SMSAnalytics, ChatConversation, ChatParticipant, ChatMessage,
    MessageReaction, UserPresence, MessageType, TypingIndicator
)
from django.core.exceptions import ValidationError


class NotificationModelsTest(TestCase):
    """Test notification service models"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    def test_notification_record_creation(self):
        """Test NotificationRecord model creation"""
        record = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            recipient="test@example.com",
            context={"name": "Test User"}
        )

        self.assertEqual(record.status, NotificationStatus.PENDING.value)
        self.assertEqual(record.retry_count, 0)
        self.assertEqual(record.max_retries, 3)
        self.assertIsNotNone(record.created_at)

    def test_tenant_credentials_creation(self):
        """Test TenantCredentials model with encryption"""
        credentials = TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            credentials={
                "smtp_host": "smtp.gmail.com",
                "username": "test@example.com",
                "password": "secret_password"
            }
        )

        self.assertEqual(credentials.channel, ChannelType.EMAIL)
        self.assertIsInstance(credentials.credentials, dict)
        self.assertTrue(credentials.is_active)

    def test_notification_template_creation(self):
        """Test NotificationTemplate model"""
        template = NotificationTemplate.objects.create(
            tenant_id=self.tenant_id,
            name="Welcome Email",
            channel=ChannelType.EMAIL,
            content={
                "subject": "Welcome {{name}}!",
                "body": "Hello {{name}}, welcome!"
            },
            placeholders=["{{name}}"]
        )

        self.assertEqual(template.version, 1)
        self.assertTrue(template.is_active)
        self.assertEqual(template.placeholders, ["{{name}}"])

    def test_campaign_creation(self):
        """Test Campaign model"""
        campaign = Campaign.objects.create(
            tenant_id=self.tenant_id,
            name="Test Campaign",
            channel=ChannelType.PUSH,
            recipients=[
                {"recipient": "token1", "context": {"name": "User1"}},
                {"recipient": "token2", "context": {"name": "User2"}}
            ]
        )

        self.assertEqual(campaign.status, CampaignStatus.DRAFT.value)
        self.assertEqual(campaign.total_recipients, 2)
        self.assertEqual(campaign.sent_count, 0)

    def test_device_token_creation(self):
        """Test DeviceToken model"""
        device_token = DeviceToken.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            device_type=DeviceType.ANDROID,
            device_token="fcm_test_token_123",
            device_id="device_123",
            app_version="1.0.0"
        )

        self.assertEqual(device_token.device_type, DeviceType.ANDROID)
        self.assertTrue(device_token.is_active)
        self.assertIsNotNone(device_token.created_at)

    def test_push_analytics_creation(self):
        """Test PushAnalytics model"""
        analytics = PushAnalytics.objects.create(
            tenant_id=self.tenant_id,
            notification_id="550e8400-e29b-41d4-a716-446655440002",
            device_token_id="550e8400-e29b-41d4-a716-446655440003",
            fcm_message_id="msg_123",
            status="delivered",
            platform=DeviceType.ANDROID
        )

        self.assertEqual(analytics.status, "delivered")
        self.assertEqual(analytics.platform, DeviceType.ANDROID)
        self.assertIsNotNone(analytics.created_at)

    def test_sms_analytics_creation(self):
        """Test SMSAnalytics model"""
        analytics = SMSAnalytics.objects.create(
            tenant_id=self.tenant_id,
            notification_id="550e8400-e29b-41d4-a716-446655440002",
            twilio_sid="SM1234567890",
            recipient="+1234567890",
            status="delivered",
            segments=1,
            price=0.0075,
            price_unit="USD"
        )

        self.assertEqual(analytics.status, "delivered")
        self.assertEqual(analytics.segments, 1)
        self.assertEqual(float(analytics.price), 0.0075)

    def test_chat_conversation_creation(self):
        """Test ChatConversation model"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            title="Test Chat",
            conversation_type="group",
            created_by=self.user_id
        )

        self.assertEqual(conversation.conversation_type, "group")
        self.assertTrue(conversation.is_active)
        self.assertEqual(conversation.created_by, self.user_id)

    def test_chat_participant_creation(self):
        """Test ChatParticipant model"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        participant = ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id,
            role="admin"
        )

        self.assertEqual(participant.role, "admin")
        self.assertTrue(participant.is_active)
        self.assertIsNotNone(participant.joined_at)

    def test_chat_message_creation(self):
        """Test ChatMessage model"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        message = ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Hello world!"
        )

        self.assertEqual(message.message_type, MessageType.TEXT)
        self.assertEqual(message.content, "Hello world!")
        self.assertFalse(message.is_deleted)
        self.assertIsNotNone(message.created_at)

    def test_message_reaction_creation(self):
        """Test MessageReaction model"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        message = ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Hello!"
        )

        reaction = MessageReaction.objects.create(
            tenant_id=self.tenant_id,
            message=message,
            user_id=self.user_id,
            emoji="👍"
        )

        self.assertEqual(reaction.emoji, "👍")
        self.assertIsNotNone(reaction.created_at)

    def test_user_presence_creation(self):
        """Test UserPresence model"""
        presence = UserPresence.objects.create(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            status="online"
        )

        self.assertEqual(presence.status, "online")
        self.assertIsNotNone(presence.last_seen)

    def test_typing_indicator_creation(self):
        """Test TypingIndicator model"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        expires_at = timezone.now() + timedelta(seconds=10)
        indicator = TypingIndicator.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id,
            expires_at=expires_at
        )

        self.assertEqual(indicator.user_id, self.user_id)
        self.assertIsNotNone(indicator.started_at)

    def test_soft_delete_functionality(self):
        """Test soft delete functionality"""
        record = NotificationRecord.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            recipient="test@example.com"
        )

        # Soft delete
        record.soft_delete()

        self.assertTrue(record.is_deleted)
        self.assertIsNotNone(record.deleted_at)

        # Should not appear in default queryset
        self.assertEqual(NotificationRecord.objects.count(), 0)
        self.assertEqual(NotificationRecord.objects.all_with_deleted().count(), 1)

    def test_unique_constraints(self):
        """Test unique constraints"""
        # Test tenant credentials uniqueness
        TenantCredentials.objects.create(
            tenant_id=self.tenant_id,
            channel=ChannelType.EMAIL,
            credentials={"host": "smtp.test.com"}
        )

        with self.assertRaises(Exception):  # Should raise IntegrityError
            TenantCredentials.objects.create(
                tenant_id=self.tenant_id,
                channel=ChannelType.EMAIL,
                credentials={"host": "smtp.test2.com"}
            )

    def test_enum_choices(self):
        """Test enum field choices"""
        # Test ChannelType
        for channel in ChannelType:
            record = NotificationRecord.objects.create(
                tenant_id=self.tenant_id,
                channel=channel,
                recipient="test@example.com"
            )
            self.assertEqual(record.channel, channel)

        # Test MessageType
        for msg_type in MessageType:
            conversation = ChatConversation.objects.create(
                tenant_id=self.tenant_id,
                conversation_type="direct",
                created_by=self.user_id
            )
            message = ChatMessage.objects.create(
                tenant_id=self.tenant_id,
                conversation=conversation,
                sender_id=self.user_id,
                message_type=msg_type,
                content="Test content"
            )
            self.assertEqual(message.message_type, msg_type)

    def test_relationships(self):
        """Test model relationships"""
        # Create conversation with participants and messages
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            title="Test Conversation",
            conversation_type="group",
            created_by=self.user_id
        )

        # Add participants
        participant1 = ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id,
            role="admin"
        )

        participant2 = ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id="660e8400-e29b-41d4-a716-446655440002",
            role="member"
        )

        # Add messages
        message1 = ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Hello everyone!"
        )

        message2 = ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id="660e8400-e29b-41d4-a716-446655440002",
            message_type=MessageType.TEXT,
            content="Hi there!",
            reply_to=message1
        )

        # Test relationships
        self.assertEqual(conversation.participants.count(), 2)
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(message1.replies.count(), 1)
        self.assertEqual(message2.reply_to, message1)

    def test_validation(self):
        """Test model validation"""
        # Test template content validation
        with self.assertRaises(ValidationError):
            NotificationTemplate.objects.create(
                tenant_id=self.tenant_id,
                name="Invalid Template",
                channel=ChannelType.EMAIL,
                content="not a dict"  # Should be dict
            )

    def test_indexes(self):
        """Test database indexes are properly configured"""
        # This is more of a documentation test - in real scenarios
        # you'd check the actual database schema
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        # Test that commonly queried fields have proper indexing
        # by checking the model's Meta.indexes
        indexes = conversation._meta.indexes
        index_fields = []
        for index in indexes:
            if hasattr(index, 'fields'):
                index_fields.extend(index.fields)

        # Should have indexes on tenant_id, conversation_type, last_message_at, created_by
        expected_fields = ['tenant_id', 'conversation_type', 'last_message_at', 'created_by']
        for field in expected_fields:
            self.assertIn(field, index_fields,
                         f"Field '{field}' should be indexed in ChatConversation")

    def test_cascade_deletes(self):
        """Test cascade delete behavior"""
        conversation = ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            conversation_type="direct",
            created_by=self.user_id
        )

        participant = ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=self.user_id
        )

        message = ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Test"
        )

        reaction = MessageReaction.objects.create(
            tenant_id=self.tenant_id,
            message=message,
            user_id=self.user_id,
            emoji="👍"
        )

        # Delete conversation - should cascade to participants and messages
        conversation_id = conversation.id
        conversation.delete()

        self.assertFalse(ChatConversation.objects.filter(id=conversation_id).exists())
        self.assertFalse(ChatParticipant.objects.filter(conversation_id=conversation_id).exists())
        self.assertFalse(ChatMessage.objects.filter(conversation_id=conversation_id).exists())
        # Reactions should also be deleted due to cascade
        self.assertFalse(MessageReaction.objects.filter(message=message).exists())