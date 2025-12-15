from .base_handler import BaseHandler
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime
import json
import logging
import uuid
from notifications.models import InAppMessage, InAppMessageStatus
from django.utils import timezone

logger = logging.getLogger('notifications.channels.inapp')

class InAppHandler(BaseHandler):
    """
    Handler for real-time in-app notifications via WebSocket
    """

    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)
        self.notification_id = None

    async def send(self, recipient: str, content: dict, context: dict, record_id: str = None) -> dict:
        """
        Send in-app notification via WebSocket

        Args:
            recipient: User ID, 'all' for tenant broadcast, or group name
            content: Notification content (title, body, data)
            context: Template context for string formatting

        Returns:
            dict: Success status and response data
        """
        try:
            logger.info(f"🔔 INAPP SEND: Starting for tenant {self.tenant_id}, recipient {recipient}")
            # Generate unique notification ID
            self.notification_id = str(uuid.uuid4())
            logger.info(f"🔔 Generated notification ID: {self.notification_id}")

            # Render content with context
            rendered_content = self._render_content(content, context)
            logger.info(f"🔔 Rendered content: {rendered_content}")

            # Save message to database for persistence
            inapp_message = None
            if record_id:
                from notifications.models import NotificationRecord
                try:
                    record = NotificationRecord.objects.get(id=record_id, tenant_id=self.tenant_id)
                    inapp_message = InAppMessage.objects.create(
                        tenant_id=self.tenant_id,
                        notification_record=record,
                        recipient=recipient,
                        title=rendered_content.get('title', ''),
                        body=rendered_content.get('body', ''),
                        data=rendered_content.get('data', {}),
                        priority=rendered_content.get('data', {}).get('priority', 'normal'),
                        message_type=self._determine_message_type(recipient)[0]
                    )
                    logger.info(f"💾 Saved in-app message {inapp_message.id} for notification {record_id}")
                except NotificationRecord.DoesNotExist:
                    logger.warning(f"❌ NotificationRecord {record_id} not found for in-app message")
                except Exception as e:
                    logger.error(f"❌ Error saving in-app message: {str(e)}")

            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.error(f"❌ Channel layer not configured for tenant {self.tenant_id}")
                if inapp_message:
                    inapp_message.status = InAppMessageStatus.FAILED.value
                    inapp_message.save(update_fields=['status'])
                return {'success': False, 'error': 'Channel layer not configured', 'response': None}

            # Determine message type and target groups
            message_type, target_groups = self._determine_message_type(recipient)
            logger.info(f"🎯 Message type: {message_type}, Target groups: {target_groups}")

            # Prepare message payload
            message_payload = self._prepare_message_payload(rendered_content, message_type)
            logger.info(f"📦 Message payload: {json.dumps(message_payload, indent=2)}")

            # Send to all target groups
            sent_groups = []
            for group_name in target_groups:
                try:
                    logger.info(f"📤 Sending to group: {group_name}")
                    await channel_layer.group_send(group_name, message_payload)
                    sent_groups.append(group_name)
                    logger.info(f"✅ Sent {message_type} to group: {group_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to send to group {group_name}: {str(e)}")

            if sent_groups:
                logger.info(f"🎉 SUCCESS: In-app notification sent to {len(sent_groups)} groups for tenant {self.tenant_id}")
                # Mark message as sent
                if inapp_message:
                    inapp_message.mark_sent()
                return {
                    'success': True,
                    'response': {
                        'notification_id': self.notification_id,
                        'groups': sent_groups,
                        'recipient': recipient,
                        'message_type': message_type
                    }
                }
            else:
                logger.error(f"❌ FAILURE: No groups received the message for tenant {self.tenant_id}")
                # Mark as failed
                if inapp_message:
                    inapp_message.status = InAppMessageStatus.FAILED.value
                    inapp_message.save(update_fields=['status'])
                return {'success': False, 'error': 'No groups received the message', 'response': None}

        except Exception as e:
            logger.error(f"❌ INAPP SEND ERROR for tenant {self.tenant_id} to {recipient}: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            # Mark message as failed
            if inapp_message:
                inapp_message.status = InAppMessageStatus.FAILED.value
                inapp_message.save(update_fields=['status'])
            return {'success': False, 'error': str(e), 'response': None}

    def _render_content(self, content: dict, context: dict) -> dict:
        """Render notification content with context variables"""
        try:
            rendered = {}

            # Render title
            if 'title' in content:
                rendered['title'] = content['title'].format(**context)

            # Render body
            if 'body' in content:
                rendered['body'] = content['body'].format(**context)

            # Handle data payload (merge with context if needed)
            if 'data' in content:
                rendered['data'] = content['data']
                # Allow data to also use context variables
                if isinstance(rendered['data'], dict):
                    rendered['data'] = self._render_data_with_context(rendered['data'], context)

            return rendered

        except KeyError as e:
            logger.warning(f"Missing context variable: {e}")
            # Return original content if formatting fails
            return content
        except Exception as e:
            logger.error(f"Content rendering error: {str(e)}")
            return content

    def _render_data_with_context(self, data: dict, context: dict) -> dict:
        """Render data dictionary with context variables"""
        rendered_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                try:
                    rendered_data[key] = value.format(**context)
                except KeyError:
                    rendered_data[key] = value  # Keep original if formatting fails
            elif isinstance(value, dict):
                rendered_data[key] = self._render_data_with_context(value, context)
            else:
                rendered_data[key] = value

        return rendered_data

    def _determine_message_type(self, recipient: str) -> tuple:
        """
        Determine message type and target groups based on recipient

        Returns:
            tuple: (message_type, target_groups)
        """
        if recipient == 'all':
            # Tenant-wide broadcast
            return 'tenant_broadcast', [f"tenant_{self.tenant_id}"]

        elif recipient.startswith('group_'):
            # Custom group broadcast
            group_name = recipient.replace('group_', '')
            return 'group_notification', [f"group_{group_name}_{self.tenant_id}"]

        elif recipient.isdigit() or len(recipient) > 10:  # Assuming user ID
            # User-specific notification
            return 'inapp_notification', [f"user_{recipient}_{self.tenant_id}"]

        else:
            # Default to user-specific
            return 'inapp_notification', [f"user_{recipient}_{self.tenant_id}"]

    def _prepare_message_payload(self, content: dict, message_type: str) -> dict:
        """Prepare the WebSocket message payload"""
        payload = {
            'type': message_type,
            'id': self.notification_id,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id,
        }

        # Add content fields
        if 'title' in content:
            payload['title'] = content['title']
        if 'body' in content:
            payload['body'] = content['body']
        if 'data' in content:
            payload['data'] = content['data']

        # Add priority if specified
        if 'priority' in content.get('data', {}):
            payload['priority'] = content['data']['priority']
        else:
            payload['priority'] = 'normal'

        return payload

    async def send_bulk(self, recipients: list, content: dict, context: dict, record_id: str = None) -> dict:
        """
        Send notification to multiple recipients efficiently

        Args:
            recipients: List of user IDs
            content: Notification content
            context: Template context

        Returns:
            dict: Bulk send results
        """
        try:
            results = []
            success_count = 0
            failure_count = 0

            # Group recipients by type for efficient sending
            user_recipients = [r for r in recipients if r != 'all' and not r.startswith('group_')]

            # Send to individual users
            for recipient in user_recipients:
                result = await self.send(recipient, content, context)
                results.append({
                    'recipient': recipient,
                    'success': result['success'],
                    'error': result.get('error')
                })

                if result['success']:
                    success_count += 1
                else:
                    failure_count += 1

            # Send tenant-wide if 'all' is in recipients
            if 'all' in recipients:
                result = await self.send('all', content, context)
                results.append({
                    'recipient': 'all',
                    'success': result['success'],
                    'error': result.get('error')
                })

                if result['success']:
                    success_count += 1
                else:
                    failure_count += 1

            logger.info(f"Bulk in-app notification sent: {success_count} success, {failure_count} failures")

            return {
                'success': True,
                'total_recipients': len(recipients),
                'success_count': success_count,
                'failure_count': failure_count,
                'results': results
            }

        except Exception as e:
            logger.error(f"Bulk in-app send error: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}