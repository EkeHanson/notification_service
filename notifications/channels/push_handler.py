from .base_handler import BaseHandler
from notifications.utils.encryption import decrypt_data
from typing import Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger('notifications.channels.push')

# Optional Firebase import - handle gracefully if not available
try:
    from firebase_admin import credentials, messaging, initialize_app, exceptions
    FIREBASE_AVAILABLE = True
except ImportError:
    logger.warning("Firebase Admin SDK not available. Push notifications will be disabled.")
    FIREBASE_AVAILABLE = False
    # Create dummy classes to prevent import errors
    class credentials:
        Certificate = lambda x: None
    class messaging:
        @staticmethod
        def send(app, message):
            raise Exception("Firebase not available")
        @staticmethod
        def subscribe_to_topic(tokens, topic, app):
            raise Exception("Firebase not available")
        @staticmethod
        def unsubscribe_from_topic(tokens, topic, app):
            raise Exception("Firebase not available")
        class Message:
            pass
        class Notification:
            pass
        class AndroidConfig:
            class Priority:
                HIGH = 'high'
                NORMAL = 'normal'
        class APNSConfig:
            pass
        class WebpushConfig:
            pass
        class Aps:
            pass
        class ApsAlert:
            pass
        class APNSPayload:
            pass
        class AndroidNotification:
            pass
        class WebpushNotification:
            pass
    class initialize_app:
        pass
    class exceptions:
        class FirebaseError(Exception):
            pass
        class InvalidArgumentError(Exception):
            pass
        class UnregisteredError(Exception):
            pass
        class SenderIdMismatchError(Exception):
            pass

class PushHandler(BaseHandler):
    """
    Enhanced push notification handler with Firebase Cloud Messaging
    """

    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)
        self._firebase_app = None
        self._decrypted_creds = None

    def _get_decrypted_credentials(self) -> dict:
        """Decrypt and cache Firebase credentials"""
        if self._decrypted_creds is None:
            self._decrypted_creds = self.credentials.copy()
            sensitive_fields = ['private_key', 'client_secret', 'refresh_token']
            for field in sensitive_fields:
                if field in self._decrypted_creds:
                    self._decrypted_creds[field] = decrypt_data(self._decrypted_creds[field])
        return self._decrypted_creds

    def _get_firebase_app(self):
        """Get or create Firebase app instance"""
        if self._firebase_app is None:
            try:
                creds = self._get_decrypted_credentials()
                cred = credentials.Certificate(creds)
                self._firebase_app = initialize_app(cred, name=f'tenant_{self.tenant_id}')
                logger.info(f"Initialized Firebase app for tenant {self.tenant_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase app for tenant {self.tenant_id}: {str(e)}")
                raise
        return self._firebase_app

    def _render_content(self, content: dict, context: dict) -> dict:
        """Render notification content with context variables"""
        try:
            rendered = {}

            # Render basic fields
            for field in ['title', 'body', 'image_url', 'icon']:
                if field in content:
                    rendered[field] = content[field].format(**context)

            # Handle data payload
            if 'data' in content:
                rendered['data'] = {}
                for key, value in content['data'].items():
                    if isinstance(value, str):
                        try:
                            rendered['data'][key] = value.format(**context)
                        except KeyError:
                            rendered['data'][key] = value
                    else:
                        rendered['data'][key] = value

            return rendered

        except KeyError as e:
            logger.warning(f"Missing context variable in push notification: {e}")
            return content
        except Exception as e:
            logger.error(f"Content rendering error in push notification: {str(e)}")
            return content

    def _create_fcm_message(self, recipient: str, content: dict, message_type: str = 'token') -> messaging.Message:
        """Create FCM message based on recipient type"""

        # Build notification payload
        notification = None
        if 'title' in content or 'body' in content:
            notification = messaging.Notification(
                title=content.get('title'),
                body=content.get('body'),
                image=content.get('image_url')
            )

        # Build message based on type
        if message_type == 'token':
            # Single device token
            message = messaging.Message(
                notification=notification,
                data=content.get('data', {}),
                token=recipient,
                android=self._get_android_config(content),
                apns=self._get_apns_config(content),
                webpush=self._get_webpush_config(content)
            )
        elif message_type == 'topic':
            # Topic-based messaging
            message = messaging.Message(
                notification=notification,
                data=content.get('data', {}),
                topic=recipient,
                android=self._get_android_config(content),
                apns=self._get_apns_config(content),
                webpush=self._get_webpush_config(content)
            )
        else:
            raise ValueError(f"Unsupported message type: {message_type}")

        return message

    def _get_android_config(self, content: dict) -> messaging.AndroidConfig:
        """Get Android-specific configuration"""
        try:
            priority = content.get('priority', 'normal')
            # Try to use Priority enum if available
            if hasattr(messaging.AndroidConfig, 'Priority'):
                android_priority = messaging.AndroidConfig.Priority.HIGH if priority == 'high' else messaging.AndroidConfig.Priority.NORMAL
                return messaging.AndroidConfig(
                    priority=android_priority,
                    notification=messaging.AndroidNotification(
                        icon=content.get('icon', 'ic_notification'),
                        color=content.get('color'),
                        sound=content.get('sound', 'default'),
                        click_action=content.get('click_action')
                    )
                )
            else:
                # Fallback for older SDK versions
                return messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon=content.get('icon', 'ic_notification'),
                        color=content.get('color'),
                        sound=content.get('sound', 'default'),
                        click_action=content.get('click_action')
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to create Android config: {e}")
            # Return minimal config
            return messaging.AndroidConfig()

    def _get_apns_config(self, content: dict) -> messaging.APNSConfig:
        """Get iOS-specific configuration"""
        priority = content.get('priority', 'normal')
        apns_priority = 10 if priority == 'high' else 5

        return messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=content.get('title'),
                        body=content.get('body')
                    ),
                    badge=content.get('badge', 1),
                    sound=content.get('sound', 'default'),
                    thread_id=content.get('thread_id')
                )
            ),
            headers={'apns-priority': str(apns_priority)}
        )

    def _get_webpush_config(self, content: dict) -> messaging.WebpushConfig:
        """Get web push configuration"""
        return messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                icon=content.get('icon'),
                badge=content.get('badge_icon'),
                image=content.get('image_url'),
                require_interaction=content.get('require_interaction', False)
            ),
            headers={'Urgency': 'high' if content.get('priority') == 'high' else 'normal'}
        )

    async def send(self, recipient: str, content: dict, context: dict) -> dict:
        """
        Send push notification to a single recipient

        Args:
            recipient: FCM token, topic name, or 'all' for broadcast
            content: Notification content
            context: Template context

        Returns:
            dict: Success status and response
        """
        try:
            app = self._get_firebase_app()
            rendered_content = self._render_content(content, context)

            # Determine message type
            if recipient.startswith('topic_'):
                message_type = 'topic'
                topic_name = recipient.replace('topic_', '')
            elif recipient == 'all':
                message_type = 'topic'
                topic_name = f"tenant_{self.tenant_id}"
            else:
                message_type = 'token'
                topic_name = None

            # Create message
            if message_type == 'token':
                message = self._create_fcm_message(recipient, rendered_content, 'token')
            else:
                message = self._create_fcm_message(topic_name, rendered_content, 'topic')

            # Send message
            response = messaging.send(app, message)

            logger.info(f"Push notification sent successfully: {response}")
            return {
                'success': True,
                'response': {
                    'message_id': response,
                    'recipient': recipient,
                    'message_type': message_type
                }
            }

        except Exception as e:
            error_str = str(e).lower()
            if 'invalid' in error_str or 'argument' in error_str:
                logger.error(f"Invalid FCM arguments for tenant {self.tenant_id}: {str(e)}")
                return {'success': False, 'error': 'invalid_arguments', 'response': None}
            elif 'unregistered' in error_str or 'not registered' in error_str:
                logger.warning(f"FCM token unregistered for tenant {self.tenant_id}: {str(e)}")
                return {'success': False, 'error': 'token_unregistered', 'response': None}
            elif 'sender' in error_str or 'mismatch' in error_str:
                logger.error(f"FCM sender ID mismatch for tenant {self.tenant_id}: {str(e)}")
                return {'success': False, 'error': 'sender_id_mismatch', 'response': None}
            else:
                logger.error(f"Push send error for tenant {self.tenant_id} to {recipient}: {str(e)}")
                return {'success': False, 'error': str(e), 'response': None}
        except Exception as e:
            logger.error(f"Push send error for tenant {self.tenant_id} to {recipient}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}

    async def send_bulk(self, recipients: List[str], content: dict, context: dict) -> dict:
        """
        Send push notification to multiple recipients efficiently

        Args:
            recipients: List of FCM tokens
            content: Notification content
            context: Template context

        Returns:
            dict: Bulk send results
        """
        try:
            results = []
            success_count = 0
            failure_count = 0

            # For large batches, consider using topics or FCM's batch send
            # For now, send individually (FCM has rate limits)
            for recipient in recipients:
                result = await self.send(recipient, content, context)
                results.append({
                    'recipient': recipient,
                    'success': result['success'],
                    'error': result.get('error'),
                    'message_id': result.get('response', {}).get('message_id')
                })

                if result['success']:
                    success_count += 1
                else:
                    failure_count += 1

            logger.info(f"Bulk push notification sent: {success_count} success, {failure_count} failures")

            return {
                'success': True,
                'total_recipients': len(recipients),
                'success_count': success_count,
                'failure_count': failure_count,
                'results': results
            }

        except Exception as e:
            logger.error(f"Bulk push send error: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}

    async def subscribe_to_topic(self, tokens: List[str], topic: str) -> dict:
        """
        Subscribe device tokens to a topic

        Args:
            tokens: List of FCM tokens
            topic: Topic name

        Returns:
            dict: Subscription results
        """
        try:
            app = self._get_firebase_app()
            response = messaging.subscribe_to_topic(tokens, topic, app)

            return {
                'success': True,
                'response': {
                    'success_count': response.success_count,
                    'failure_count': response.failure_count,
                    'errors': [{'index': e.index, 'reason': e.reason} for e in response.errors]
                }
            }

        except Exception as e:
            logger.error(f"Topic subscription error: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}

    async def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> dict:
        """
        Unsubscribe device tokens from a topic

        Args:
            tokens: List of FCM tokens
            topic: Topic name

        Returns:
            dict: Unsubscription results
        """
        try:
            app = self._get_firebase_app()
            response = messaging.unsubscribe_from_topic(tokens, topic, app)

            return {
                'success': True,
                'response': {
                    'success_count': response.success_count,
                    'failure_count': response.failure_count,
                    'errors': [{'index': e.index, 'reason': e.reason} for e in response.errors]
                }
            }

        except Exception as e:
            logger.error(f"Topic unsubscription error: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}