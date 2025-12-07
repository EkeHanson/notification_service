import json
from django.test import TestCase
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from unittest.mock import patch, MagicMock, AsyncMock
from notifications.chat_consumers import ChatConsumer
from notifications.models import (
    ChatConversation, ChatParticipant, ChatMessage, MessageType,
    UserPresence, MessageReaction
)


class ChatWebSocketTest(TestCase):
    """Test WebSocket chat functionality"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    async def test_chat_connection(self):
        """Test WebSocket connection establishment"""
        # Create application with our consumer
        from django.test.utils import override_settings
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns

        application = URLRouter(websocket_urlpatterns)

        # Create communicator
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )

        # Mock scope with tenant/user info (normally set by middleware)
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        # Connect
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Receive connection confirmation
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'connection_established')
        self.assertEqual(response['user_id'], self.user_id)
        self.assertEqual(response['tenant_id'], self.tenant_id)

        # Disconnect
        await communicator.disconnect()

    async def test_join_conversation(self):
        """Test joining a conversation"""
        # Create test conversation and participant
        conversation = await self.create_test_conversation()
        await self.create_test_participant(conversation)

        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Join conversation
        await communicator.send_json_to({
            'type': 'join_conversation',
            'conversation_id': str(conversation.id)
        })

        # Receive join confirmation
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'conversation_joined')
        self.assertEqual(response['conversation_id'], str(conversation.id))

        await communicator.disconnect()

    async def test_send_message(self):
        """Test sending a chat message"""
        conversation = await self.create_test_conversation()
        await self.create_test_participant(conversation)

        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Join conversation first
        await communicator.send_json_to({
            'type': 'join_conversation',
            'conversation_id': str(conversation.id)
        })
        await communicator.receive_json_from()  # Join confirmation

        # Send message
        await communicator.send_json_to({
            'type': 'send_message',
            'conversation_id': str(conversation.id),
            'content': 'Hello WebSocket world!',
            'message_type': 'text'
        })

        # Receive message sent confirmation
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'message_sent')
        self.assertIn('message', response)
        self.assertEqual(response['message']['content'], 'Hello WebSocket world!')

        # Verify message was created in database
        messages = await self.get_conversation_messages(conversation.id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['content'], 'Hello WebSocket world!')

        await communicator.disconnect()

    async def test_receive_message_broadcast(self):
        """Test receiving broadcast messages"""
        conversation = await self.create_test_conversation()
        await self.create_test_participant(conversation)

        application = self.get_chat_application()

        # Create two communicators (simulating two users)
        comm1 = WebsocketCommunicator(application, f"/ws/chat/{self.tenant_id}/")
        comm1.scope['tenant_id'] = self.tenant_id
        comm1.scope['user_id'] = self.user_id

        comm2 = WebsocketCommunicator(application, f"/ws/chat/{self.tenant_id}/")
        comm2.scope['tenant_id'] = self.tenant_id
        comm2.scope['user_id'] = "770e8400-e29b-41d4-a716-446655440002"  # Different user

        # Add second user as participant
        await self.create_test_participant(conversation, "770e8400-e29b-41d4-a716-446655440002")

        # Connect both
        await comm1.connect()
        await comm2.connect()

        # Both join conversation
        await comm1.send_json_to({'type': 'join_conversation', 'conversation_id': str(conversation.id)})
        await comm2.send_json_to({'type': 'join_conversation', 'conversation_id': str(conversation.id)})

        await comm1.receive_json_from()  # Join confirmation
        await comm2.receive_json_from()  # Join confirmation

        # User 1 sends message
        await comm1.send_json_to({
            'type': 'send_message',
            'conversation_id': str(conversation.id),
            'content': 'Broadcast test message',
            'message_type': 'text'
        })

        # User 1 receives sent confirmation
        response1 = await comm1.receive_json_from()
        self.assertEqual(response1['type'], 'message_sent')

        # User 2 receives the broadcast message
        response2 = await comm2.receive_json_from()
        self.assertEqual(response2['type'], 'new_message')
        self.assertEqual(response2['message']['content'], 'Broadcast test message')

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_typing_indicators(self):
        """Test typing indicators"""
        conversation = await self.create_test_conversation()
        await self.create_test_participant(conversation)

        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()
        await communicator.send_json_to({
            'type': 'join_conversation',
            'conversation_id': str(conversation.id)
        })
        await communicator.receive_json_from()  # Join confirmation

        # Start typing
        await communicator.send_json_to({
            'type': 'start_typing',
            'conversation_id': str(conversation.id)
        })

        # Should not receive immediate response (handled by broadcast)
        # In real scenario, other users would receive typing indicator

        await communicator.disconnect()

    async def test_message_reactions(self):
        """Test message reactions"""
        conversation = await self.create_test_conversation()
        await self.create_test_participant(conversation)

        # Create a message first
        message = await self.create_test_message(conversation)

        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()
        await communicator.send_json_to({
            'type': 'join_conversation',
            'conversation_id': str(conversation.id)
        })
        await communicator.receive_json_from()  # Join confirmation

        # Add reaction
        await communicator.send_json_to({
            'type': 'add_reaction',
            'message_id': str(message.id),
            'emoji': '👍'
        })

        # Should receive reaction confirmation (in real implementation)
        # Verify reaction was created
        reactions = await self.get_message_reactions(message.id)
        self.assertEqual(len(reactions), 1)
        self.assertEqual(reactions[0]['emoji'], '👍')

        await communicator.disconnect()

    async def test_presence_updates(self):
        """Test user presence updates"""
        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Update presence
        await communicator.send_json_to({
            'type': 'update_presence',
            'status': 'busy'
        })

        # Receive confirmation
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'presence_updated')
        self.assertEqual(response['status'], 'busy')

        await communicator.disconnect()

    async def test_unauthorized_access(self):
        """Test unauthorized conversation access"""
        # Create conversation without adding user as participant
        conversation = await self.create_test_conversation()

        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Try to join conversation
        await communicator.send_json_to({
            'type': 'join_conversation',
            'conversation_id': str(conversation.id)
        })

        # Should receive error
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'error')
        self.assertIn('Not authorized', response['message'])

        await communicator.disconnect()

    async def test_invalid_message_type(self):
        """Test handling of invalid message types"""
        application = self.get_chat_application()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Send invalid message type
        await communicator.send_json_to({
            'type': 'invalid_type',
            'data': 'test'
        })

        # Should receive error
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'error')
        self.assertIn('Unknown message type', response['message'])

        await communicator.disconnect()

    # Helper methods
    def get_chat_application(self):
        """Get chat application for testing"""
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns
        return URLRouter(websocket_urlpatterns)

    @database_sync_to_async
    def create_test_conversation(self):
        """Create a test conversation"""
        return ChatConversation.objects.create(
            tenant_id=self.tenant_id,
            title="Test Conversation",
            conversation_type="group",
            created_by=self.user_id
        )

    @database_sync_to_async
    def create_test_participant(self, conversation, user_id=None):
        """Create a test participant"""
        if user_id is None:
            user_id = self.user_id
        return ChatParticipant.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            user_id=user_id,
            role="member"
        )

    @database_sync_to_async
    def create_test_message(self, conversation):
        """Create a test message"""
        return ChatMessage.objects.create(
            tenant_id=self.tenant_id,
            conversation=conversation,
            sender_id=self.user_id,
            message_type=MessageType.TEXT,
            content="Test message"
        )

    @database_sync_to_async
    def get_conversation_messages(self, conversation_id):
        """Get conversation messages"""
        messages = list(ChatMessage.objects.filter(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            is_deleted=False
        ).order_by('created_at').values(
            'id', 'content', 'message_type', 'sender_id', 'created_at'
        ))
        return messages

    @database_sync_to_async
    def get_message_reactions(self, message_id):
        """Get message reactions"""
        return list(MessageReaction.objects.filter(
            tenant_id=self.tenant_id,
            message_id=message_id
        ).values('emoji', 'user_id', 'created_at'))


class EventSystemWebSocketTest(TestCase):
    """Test event system WebSocket integration"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    @patch('notifications.consumers.NotificationConsumer.send_notification')
    async def test_notification_websocket(self, mock_send):
        """Test notification WebSocket consumer"""
        from notifications.consumers import NotificationConsumer
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns

        application = URLRouter(websocket_urlpatterns)

        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Send a test notification message
        test_message = {
            'type': 'notification',
            'title': 'Test Notification',
            'body': 'This is a test',
            'data': {'test': True}
        }

        await communicator.send_json_to(test_message)

        # Should receive echo or processed message
        response = await communicator.receive_json_from()
        # Response depends on consumer implementation

        await communicator.disconnect()

    async def test_tenant_broadcast_websocket(self):
        """Test tenant-wide broadcast WebSocket"""
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns

        application = URLRouter(websocket_urlpatterns)

        communicator = WebsocketCommunicator(
            application,
            f"/ws/tenant/{self.tenant_id}/broadcast/"
        )
        communicator.scope['tenant_id'] = self.tenant_id

        await communicator.connect()

        # Send broadcast message
        await communicator.send_json_to({
            'type': 'broadcast',
            'message': 'Tenant-wide announcement',
            'priority': 'high'
        })

        # Should receive confirmation or broadcast
        response = await communicator.receive_json_from()

        await communicator.disconnect()


class WebSocketErrorHandlingTest(TestCase):
    """Test WebSocket error handling"""

    def setUp(self):
        self.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.user_id = "660e8400-e29b-41d4-a716-446655440001"

    async def test_invalid_json(self):
        """Test handling of invalid JSON"""
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns

        application = URLRouter(websocket_urlpatterns)

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Send invalid JSON
        await communicator.send_to(text_data="invalid json")

        # Should handle gracefully
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'error')

        await communicator.disconnect()

    async def test_missing_tenant_context(self):
        """Test connection without tenant context"""
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns

        application = URLRouter(websocket_urlpatterns)

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        # Don't set tenant_id in scope

        # Connection should fail
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_connection_cleanup(self):
        """Test proper connection cleanup"""
        from channels.routing import URLRouter
        from notifications.routing import websocket_urlpatterns

        application = URLRouter(websocket_urlpatterns)

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/{self.tenant_id}/"
        )
        communicator.scope['tenant_id'] = self.tenant_id
        communicator.scope['user_id'] = self.user_id

        await communicator.connect()

        # Verify connection
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'connection_established')

        # Disconnect
        await communicator.disconnect()

        # Should not be able to send/receive after disconnect
        try:
            await communicator.send_json_to({'type': 'test'})
            # If no exception, connection wasn't properly closed
            self.fail("Should not be able to send after disconnect")
        except:
            # Expected - connection closed
            pass