import json
import logging
from datetime import datetime, timedelta
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import (
    ChatConversation, ChatParticipant, ChatMessage, MessageReaction,
    TypingIndicator, UserPresence, MessageType
)

logger = logging.getLogger('notifications.chat')

class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality
    """

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Extract tenant and user from JWT token (assuming middleware sets this)
            self.tenant_id = self.scope.get('tenant_id')
            self.user_id = self.scope.get('user_id')

            if not self.tenant_id or not self.user_id:
                await self.close(code=4001)  # Unauthorized
                return

            # Join user's personal group for direct messages
            self.user_group = f"chat_user_{self.tenant_id}_{self.user_id}"
            await self.channel_layer.group_add(self.user_group, self.channel_name)

            # Update user presence to online
            await self.update_presence('online')

            await self.accept()
            await self.send_json({
                'type': 'connection_established',
                'message': 'Connected to chat service',
                'user_id': self.user_id,
                'tenant_id': self.tenant_id,
                'timestamp': timezone.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Chat connection error: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            # Update presence to offline
            await self.update_presence('offline')

            # Leave user group
            if hasattr(self, 'user_group'):
                await self.channel_layer.group_discard(self.user_group, self.channel_name)

            # Leave conversation group if in one
            if hasattr(self, 'conversation_group'):
                await self.channel_layer.group_discard(self.conversation_group, self.channel_name)

            # Clear typing indicators
            await self.clear_typing_indicators()

        except Exception as e:
            logger.error(f"Chat disconnect error: {str(e)}")

    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        try:
            message_type = content.get('type')

            handlers = {
                'join_conversation': self.join_conversation,
                'leave_conversation': self.leave_conversation,
                'send_message': self.send_message,
                'edit_message': self.edit_message,
                'delete_message': self.delete_message,
                'add_reaction': self.add_reaction,
                'remove_reaction': self.remove_reaction,
                'start_typing': self.start_typing,
                'stop_typing': self.stop_typing,
                'mark_read': self.mark_read,
                'update_presence': self.update_presence_message,
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(content)
            else:
                await self.send_json({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })

        except Exception as e:
            logger.error(f"Chat message handling error: {str(e)}")
            await self.send_json({
                'type': 'error',
                'message': 'Internal server error'
            })

    async def join_conversation(self, content):
        """Join a conversation room"""
        conversation_id = content.get('conversation_id')
        if not conversation_id:
            await self.send_json({'type': 'error', 'message': 'conversation_id required'})
            return

        # Verify user is participant
        is_participant = await self.is_conversation_participant(conversation_id)
        if not is_participant:
            await self.send_json({'type': 'error', 'message': 'Not authorized for this conversation'})
            return

        # Leave previous conversation if any
        if hasattr(self, 'conversation_group'):
            await self.channel_layer.group_discard(self.conversation_group, self.channel_name)

        # Join new conversation
        self.conversation_id = conversation_id
        self.conversation_group = f"chat_conversation_{self.tenant_id}_{conversation_id}"
        await self.channel_layer.group_add(self.conversation_group, self.channel_name)

        # Update user presence
        await self.update_presence('online', conversation_id)

        # Send conversation history
        history = await self.get_conversation_history(conversation_id)
        await self.send_json({
            'type': 'conversation_joined',
            'conversation_id': conversation_id,
            'history': history
        })

    async def leave_conversation(self, content):
        """Leave a conversation room"""
        if hasattr(self, 'conversation_group'):
            await self.channel_layer.group_discard(self.conversation_group, self.channel_name)
            delattr(self, 'conversation_group')

        await self.update_presence('online')  # Still online, just not in conversation

        await self.send_json({'type': 'conversation_left'})

    async def send_message(self, content):
        """Send a message to the current conversation"""
        if not hasattr(self, 'conversation_group'):
            await self.send_json({'type': 'error', 'message': 'Not in a conversation'})
            return

        conversation_id = content.get('conversation_id')
        message_content = content.get('content', '').strip()
        message_type = content.get('message_type', 'text')
        reply_to_id = content.get('reply_to')

        if not message_content and message_type == 'text':
            await self.send_json({'type': 'error', 'message': 'Message content required'})
            return

        # Validate message type
        if message_type not in [mt.value for mt in MessageType]:
            await self.send_json({'type': 'error', 'message': 'Invalid message type'})
            return

        # Create message
        message_data = await self.create_message(
            conversation_id, message_content, message_type, reply_to_id
        )

        if message_data:
            # Broadcast to conversation
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )

            # Send confirmation to sender
            await self.send_json({
                'type': 'message_sent',
                'message': message_data
            })

    async def edit_message(self, content):
        """Edit a message"""
        message_id = content.get('message_id')
        new_content = content.get('content', '').strip()

        if not message_id or not new_content:
            await self.send_json({'type': 'error', 'message': 'message_id and content required'})
            return

        # Update message
        updated_message = await self.update_message(message_id, new_content)
        if updated_message:
            # Broadcast update
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'message_updated',
                    'message': updated_message
                }
            )

    async def delete_message(self, content):
        """Soft delete a message"""
        message_id = content.get('message_id')

        if not message_id:
            await self.send_json({'type': 'error', 'message': 'message_id required'})
            return

        # Delete message
        deleted_message = await self.delete_message_record(message_id)
        if deleted_message:
            # Broadcast deletion
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'message_deleted',
                    'message_id': message_id
                }
            )

    async def add_reaction(self, content):
        """Add emoji reaction to message"""
        message_id = content.get('message_id')
        emoji = content.get('emoji')

        if not message_id or not emoji:
            await self.send_json({'type': 'error', 'message': 'message_id and emoji required'})
            return

        # Add reaction
        reaction_data = await self.add_message_reaction(message_id, emoji)
        if reaction_data:
            # Broadcast reaction
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'reaction_added',
                    'reaction': reaction_data
                }
            )

    async def remove_reaction(self, content):
        """Remove emoji reaction from message"""
        message_id = content.get('message_id')
        emoji = content.get('emoji')

        if not message_id or not emoji:
            await self.send_json({'type': 'error', 'message': 'message_id and emoji required'})
            return

        # Remove reaction
        removed = await self.remove_message_reaction(message_id, emoji)
        if removed:
            # Broadcast removal
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'reaction_removed',
                    'message_id': message_id,
                    'user_id': self.user_id,
                    'emoji': emoji
                }
            )

    async def start_typing(self, content):
        """Start typing indicator"""
        if hasattr(self, 'conversation_group'):
            # Create typing indicator
            await self.set_typing_indicator(True)

            # Broadcast typing start
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'user_typing',
                    'user_id': self.user_id,
                    'is_typing': True
                }
            )

    async def stop_typing(self, content):
        """Stop typing indicator"""
        if hasattr(self, 'conversation_group'):
            # Remove typing indicator
            await self.set_typing_indicator(False)

            # Broadcast typing stop
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    'type': 'user_typing',
                    'user_id': self.user_id,
                    'is_typing': False
                }
            )

    async def mark_read(self, content):
        """Mark messages as read"""
        conversation_id = content.get('conversation_id')
        message_id = content.get('message_id')

        if conversation_id:
            await self.mark_conversation_read(conversation_id)
        elif message_id:
            await self.mark_message_read(message_id)

        await self.send_json({'type': 'messages_marked_read'})

    async def update_presence_message(self, content):
        """Update user presence"""
        status = content.get('status', 'online')
        await self.update_presence(status)
        await self.send_json({'type': 'presence_updated', 'status': status})

    # WebSocket event handlers for group messages
    async def chat_message(self, event):
        """Handle incoming chat messages"""
        await self.send_json({
            'type': 'new_message',
            'message': event['message']
        })

    async def message_updated(self, event):
        """Handle message updates"""
        await self.send_json({
            'type': 'message_updated',
            'message': event['message']
        })

    async def message_deleted(self, event):
        """Handle message deletions"""
        await self.send_json({
            'type': 'message_deleted',
            'message_id': event['message_id']
        })

    async def reaction_added(self, event):
        """Handle reaction additions"""
        await self.send_json({
            'type': 'reaction_added',
            'reaction': event['reaction']
        })

    async def reaction_removed(self, event):
        """Handle reaction removals"""
        await self.send_json({
            'type': 'reaction_removed',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'emoji': event['emoji']
        })

    async def user_typing(self, event):
        """Handle typing indicators"""
        await self.send_json({
            'type': 'typing_indicator',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        })

    # Database operations
    @database_sync_to_async
    def is_conversation_participant(self, conversation_id):
        """Check if user is participant in conversation"""
        return ChatParticipant.objects.filter(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            user_id=self.user_id,
            is_active=True
        ).exists()

    @database_sync_to_async
    def get_conversation_history(self, conversation_id, limit=50):
        """Get recent conversation history"""
        messages = ChatMessage.objects.filter(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            is_deleted=False
        ).order_by('-created_at')[:limit]

        # Convert to list and reverse for chronological order
        message_list = []
        for msg in reversed(messages):
            message_list.append({
                'id': str(msg.id),
                'sender_id': str(msg.sender_id),
                'message_type': msg.message_type,
                'content': msg.content,
                'file_url': msg.file_url,
                'file_name': msg.file_name,
                'file_size': msg.file_size,
                'reply_to': str(msg.reply_to.id) if msg.reply_to else None,
                'edited_at': msg.edited_at.isoformat() if msg.edited_at else None,
                'created_at': msg.created_at.isoformat(),
                'reactions': [
                    {
                        'user_id': str(r.user_id),
                        'emoji': r.emoji,
                        'created_at': r.created_at.isoformat()
                    } for r in msg.reactions.all()
                ]
            })

        return message_list

    @database_sync_to_async
    def create_message(self, conversation_id, content, message_type, reply_to_id=None):
        """Create a new chat message"""
        try:
            # Validate reply_to if provided
            reply_to = None
            if reply_to_id:
                reply_to = ChatMessage.objects.get(
                    id=reply_to_id,
                    tenant_id=self.tenant_id,
                    conversation_id=conversation_id
                )

            # Create message
            message = ChatMessage.objects.create(
                tenant_id=self.tenant_id,
                conversation_id=conversation_id,
                sender_id=self.user_id,
                message_type=message_type,
                content=content,
                reply_to=reply_to
            )

            # Update conversation last_message_at
            ChatConversation.objects.filter(
                id=conversation_id,
                tenant_id=self.tenant_id
            ).update(last_message_at=message.created_at)

            # Update participant last_seen_at
            ChatParticipant.objects.filter(
                conversation_id=conversation_id,
                user_id=self.user_id,
                tenant_id=self.tenant_id
            ).update(last_seen_at=message.created_at)

            return {
                'id': str(message.id),
                'sender_id': str(message.sender_id),
                'message_type': message.message_type,
                'content': message.content,
                'file_url': message.file_url,
                'file_name': message.file_name,
                'file_size': message.file_size,
                'reply_to': str(message.reply_to.id) if message.reply_to else None,
                'created_at': message.created_at.isoformat(),
                'reactions': []
            }

        except Exception as e:
            logger.error(f"Create message error: {str(e)}")
            return None

    @database_sync_to_async
    def update_message(self, message_id, new_content):
        """Update message content"""
        try:
            message = ChatMessage.objects.get(
                id=message_id,
                tenant_id=self.tenant_id,
                sender_id=self.user_id,  # Only sender can edit
                is_deleted=False
            )

            message.content = new_content
            message.edited_at = timezone.now()
            message.save()

            return {
                'id': str(message.id),
                'content': message.content,
                'edited_at': message.edited_at.isoformat()
            }

        except ChatMessage.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Update message error: {str(e)}")
            return None

    @database_sync_to_async
    def delete_message_record(self, message_id):
        """Soft delete message"""
        try:
            message = ChatMessage.objects.get(
                id=message_id,
                tenant_id=self.tenant_id,
                sender_id=self.user_id,  # Only sender can delete
                is_deleted=False
            )

            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.save()

            return {
                'id': str(message.id),
                'deleted_at': message.deleted_at.isoformat()
            }

        except ChatMessage.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Delete message error: {str(e)}")
            return None

    @database_sync_to_async
    def add_message_reaction(self, message_id, emoji):
        """Add emoji reaction to message"""
        try:
            # Check if reaction already exists
            reaction, created = MessageReaction.objects.get_or_create(
                tenant_id=self.tenant_id,
                message_id=message_id,
                user_id=self.user_id,
                emoji=emoji,
                defaults={}
            )

            if created:
                return {
                    'message_id': message_id,
                    'user_id': str(self.user_id),
                    'emoji': emoji,
                    'created_at': reaction.created_at.isoformat()
                }
            return None  # Reaction already exists

        except Exception as e:
            logger.error(f"Add reaction error: {str(e)}")
            return None

    @database_sync_to_async
    def remove_message_reaction(self, message_id, emoji):
        """Remove emoji reaction from message"""
        try:
            deleted, _ = MessageReaction.objects.filter(
                tenant_id=self.tenant_id,
                message_id=message_id,
                user_id=self.user_id,
                emoji=emoji
            ).delete()

            return deleted > 0

        except Exception as e:
            logger.error(f"Remove reaction error: {str(e)}")
            return False

    @database_sync_to_async
    def set_typing_indicator(self, is_typing):
        """Set or remove typing indicator"""
        try:
            if is_typing and hasattr(self, 'conversation_id'):
                # Create or update typing indicator
                expires_at = timezone.now() + timedelta(seconds=10)
                TypingIndicator.objects.update_or_create(
                    tenant_id=self.tenant_id,
                    conversation_id=self.conversation_id,
                    user_id=self.user_id,
                    defaults={'expires_at': expires_at}
                )
            else:
                # Remove typing indicator
                TypingIndicator.objects.filter(
                    tenant_id=self.tenant_id,
                    user_id=self.user_id
                ).delete()

        except Exception as e:
            logger.error(f"Typing indicator error: {str(e)}")

    @database_sync_to_async
    def clear_typing_indicators(self):
        """Clear all typing indicators for user"""
        try:
            TypingIndicator.objects.filter(
                tenant_id=self.tenant_id,
                user_id=self.user_id
            ).delete()
        except Exception as e:
            logger.error(f"Clear typing indicators error: {str(e)}")

    @database_sync_to_async
    def update_presence(self, status, current_conversation=None):
        """Update user presence status"""
        try:
            presence, created = UserPresence.objects.update_or_create(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                defaults={
                    'status': status,
                    'current_conversation_id': current_conversation
                }
            )

            # Broadcast presence change to user's contacts/groups
            # This would be implemented based on your social graph

        except Exception as e:
            logger.error(f"Update presence error: {str(e)}")

    @database_sync_to_async
    def mark_conversation_read(self, conversation_id):
        """Mark all messages in conversation as read"""
        try:
            ChatParticipant.objects.filter(
                tenant_id=self.tenant_id,
                conversation_id=conversation_id,
                user_id=self.user_id
            ).update(last_seen_at=timezone.now())

        except Exception as e:
            logger.error(f"Mark conversation read error: {str(e)}")

    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark specific message as read"""
        try:
            # Update last_seen_at to message timestamp
            message = ChatMessage.objects.get(
                id=message_id,
                tenant_id=self.tenant_id
            )

            ChatParticipant.objects.filter(
                tenant_id=self.tenant_id,
                conversation_id=message.conversation_id,
                user_id=self.user_id
            ).update(last_seen_at=message.created_at)

        except Exception as e:
            logger.error(f"Mark message read error: {str(e)}")