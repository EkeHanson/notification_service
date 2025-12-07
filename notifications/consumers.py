import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from notifications.services.auth_service import auth_service_client
import jwt
from django.conf import settings

logger = logging.getLogger('notifications.consumers')

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time in-app notifications
    """

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Extract tenant_id from query parameters or headers
            self.tenant_id = self.scope['url_route']['kwargs'].get('tenant_id')
            self.user_id = None
            self.groups_joined = []

            # Authenticate user
            if await self.authenticate():
                await self.accept()
                logger.info(f"WebSocket connected for user {self.user_id} in tenant {self.tenant_id}")

                # Join user-specific group
                await self.join_user_group()

                # Send welcome message
                await self.send_welcome_message()
            else:
                logger.warning("WebSocket authentication failed")
                await self.close(code=4001)  # Unauthorized

        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            await self.close(code=4000)  # Internal error

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            # Leave all groups
            for group in self.groups_joined:
                await self.channel_layer.group_discard(group, self.channel_name)

            logger.info(f"WebSocket disconnected for user {self.user_id} in tenant {self.tenant_id}")
        except Exception as e:
            logger.error(f"WebSocket disconnection error: {str(e)}")

    async def authenticate(self) -> bool:
        """Authenticate WebSocket connection"""
        try:
            # Get token from query parameters or headers
            token = None

            # Try query parameter first
            token = self.scope['query_string'].decode().split('token=')[1].split('&')[0] if 'token=' in self.scope['query_string'].decode() else None

            # Try Authorization header
            if not token:
                auth_header = dict(self.scope['headers']).get(b'authorization', b'').decode()
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]

            if not token:
                logger.warning("No authentication token provided")
                return False

            # Validate token with auth service
            token_data = auth_service_client.validate_tenant_token(token)
            if not token_data:
                logger.warning("Invalid authentication token")
                return False

            # Extract user and tenant info
            self.user_id = token_data.get('user_id')
            self.tenant_id = token_data.get('tenant_id') or self.tenant_id

            if not self.user_id or not self.tenant_id:
                logger.warning("Missing user_id or tenant_id in token")
                return False

            return True

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    async def join_user_group(self):
        """Join user-specific notification group"""
        try:
            user_group = f"user_{self.user_id}_{self.tenant_id}"
            await self.channel_layer.group_add(user_group, self.channel_name)
            self.groups_joined.append(user_group)

            # Also join tenant-wide group for broadcasts
            tenant_group = f"tenant_{self.tenant_id}"
            await self.channel_layer.group_add(tenant_group, self.channel_name)
            self.groups_joined.append(tenant_group)

            logger.debug(f"User {self.user_id} joined groups: {self.groups_joined}")

        except Exception as e:
            logger.error(f"Error joining groups: {str(e)}")

    async def send_welcome_message(self):
        """Send welcome message on connection"""
        try:
            welcome_data = {
                'type': 'connection_established',
                'message': 'Connected to notification service',
                'user_id': self.user_id,
                'tenant_id': self.tenant_id,
                'timestamp': self.get_current_timestamp()
            }

            await self.send(text_data=json.dumps(welcome_data))

        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")

    async def inapp_notification(self, event):
        """Handle in-app notification messages"""
        try:
            # Extract notification data
            notification_data = {
                'type': 'notification',
                'id': event.get('id'),
                'title': event.get('title'),
                'body': event.get('body'),
                'data': event.get('data', {}),
                'timestamp': event.get('timestamp', self.get_current_timestamp()),
                'priority': event.get('priority', 'normal')
            }

            # Send to WebSocket
            await self.send(text_data=json.dumps(notification_data))

            logger.debug(f"Sent notification to user {self.user_id}: {notification_data['title']}")

        except Exception as e:
            logger.error(f"Error sending in-app notification: {str(e)}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': self.get_current_timestamp()
                }))

            elif message_type == 'mark_read':
                # Mark notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)

            elif message_type == 'get_unread_count':
                # Send unread notification count
                await self.send_unread_count()

            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing received message: {str(e)}")

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        try:
            from notifications.models import NotificationRecord
            NotificationRecord.objects.filter(
                id=notification_id,
                tenant_id=self.tenant_id
            ).update(status='read')
            logger.info(f"Marked notification {notification_id} as read")
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")

    @database_sync_to_async
    def send_unread_count(self):
        """Send count of unread notifications"""
        try:
            from notifications.models import NotificationRecord
            unread_count = NotificationRecord.objects.filter(
                tenant_id=self.tenant_id,
                recipient=str(self.user_id),
                channel='inapp',
                status__in=['pending', 'sent']
            ).count()

            count_data = {
                'type': 'unread_count',
                'count': unread_count,
                'timestamp': self.get_current_timestamp()
            }

            # Use sync_to_async to call async method
            import asyncio
            asyncio.create_task(self.send(text_data=json.dumps(count_data)))

        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")

    def get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    async def notification_broadcast(self, event):
        """Handle tenant-wide broadcasts"""
        try:
            broadcast_data = {
                'type': 'broadcast',
                'title': event.get('title'),
                'body': event.get('body'),
                'data': event.get('data', {}),
                'timestamp': event.get('timestamp', self.get_current_timestamp())
            }

            await self.send(text_data=json.dumps(broadcast_data))

        except Exception as e:
            logger.error(f"Error sending broadcast: {str(e)}")


class TenantNotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer for tenant-wide notification broadcasts
    """

    async def connect(self):
        """Handle tenant broadcast connection"""
        try:
            self.tenant_id = self.scope['url_route']['kwargs'].get('tenant_id')

            # Simple tenant validation (could be enhanced)
            if self.tenant_id:
                await self.accept()

                # Join tenant broadcast group
                tenant_group = f"tenant_{self.tenant_id}"
                await self.channel_layer.group_add(tenant_group, self.channel_name)

                logger.info(f"Tenant broadcast connection established for {self.tenant_id}")
            else:
                await self.close(code=4002)  # Bad request

        except Exception as e:
            logger.error(f"Tenant broadcast connection error: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle disconnection"""
        try:
            if hasattr(self, 'tenant_id'):
                tenant_group = f"tenant_{self.tenant_id}"
                await self.channel_layer.group_discard(tenant_group, self.channel_name)
        except Exception as e:
            logger.error(f"Tenant broadcast disconnection error: {str(e)}")

    async def tenant_broadcast(self, event):
        """Handle tenant-wide broadcasts"""
        try:
            broadcast_data = {
                'type': 'tenant_broadcast',
                'title': event.get('title'),
                'body': event.get('body'),
                'data': event.get('data', {}),
                'timestamp': event.get('timestamp', self.get_current_timestamp())
            }

            await self.send(text_data=json.dumps(broadcast_data))

        except Exception as e:
            logger.error(f"Error sending tenant broadcast: {str(e)}")

    def get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()