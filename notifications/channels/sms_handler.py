from .base_handler import BaseHandler
from notifications.utils.encryption import decrypt_data
import logging

logger = logging.getLogger('notifications.channels.sms')

# Optional Twilio import - handle gracefully if not available
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    logger.warning("Twilio SDK not available. SMS notifications will be disabled.")
    TWILIO_AVAILABLE = False
    # Create dummy classes to prevent import errors
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        @property
        def messages(self):
            return Messages()
    class Messages:
        def create(self, **kwargs):
            raise Exception("Twilio not available")
    class TwilioException(Exception):
        pass


class SMSHandler(BaseHandler):
    """
    SMS notification handler using Twilio API
    """

    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)
        self._client = None
        self._decrypted_creds = None

    def _get_decrypted_credentials(self) -> dict:
        """Decrypt and cache Twilio credentials"""
        if self._decrypted_creds is None:
            self._decrypted_creds = self.credentials.copy()
            sensitive_fields = ['auth_token']
            for field in sensitive_fields:
                if field in self._decrypted_creds:
                    self._decrypted_creds[field] = decrypt_data(self._decrypted_creds[field])
        return self._decrypted_creds

    def _get_twilio_client(self):
        """Get or create Twilio client instance"""
        if self._client is None:
            try:
                creds = self._get_decrypted_credentials()
                self._client = Client(creds['account_sid'], creds['auth_token'])
                logger.info(f"Initialized Twilio client for tenant {self.tenant_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client for tenant {self.tenant_id}: {str(e)}")
                raise
        return self._client

    def _render_content(self, content: dict, context: dict) -> dict:
        """Render SMS content with context variables"""
        try:
            rendered = {}

            # Render body - handle both single and double curly braces
            if 'body' in content:
                body = content['body']
                # Replace double curly braces with single ones for Python formatting
                for key, value in context.items():
                    body = body.replace(f'{{{{{key}}}}}', str(value))
                # Also handle single curly braces
                try:
                    body = body.format(**context)
                except KeyError:
                    pass  # Keep original if formatting fails
                rendered['body'] = body

            return rendered

        except Exception as e:
            logger.error(f"SMS content rendering error: {str(e)}")
            return content

    def _estimate_cost(self, message_length: int, country_code: str = 'US') -> dict:
        """Estimate SMS cost based on message length and destination"""
        # Basic cost estimation (actual costs vary by provider)
        segments = (message_length // 160) + 1 if message_length > 0 else 1

        # Cost per segment (approximate)
        cost_per_segment = 0.01  # USD

        return {
            'segments': segments,
            'estimated_cost': segments * cost_per_segment,
            'currency': 'USD',
            'message_length': message_length
        }

    async def send(self, recipient: str, content: dict, context: dict) -> dict:
        """
        Send SMS to a single recipient

        Args:
            recipient: Phone number in E.164 format (+1234567890)
            content: SMS content
            context: Template context

        Returns:
            dict: Success status and response
        """
        try:
            client = self._get_twilio_client()
            rendered_content = self._render_content(content, context)

            creds = self._get_decrypted_credentials()

            # Send SMS
            message = client.messages.create(
                body=rendered_content['body'],
                from_=creds['from_number'],
                to=recipient
            )

            logger.info(f"SMS sent successfully: {message.sid}")
            return {
                'success': True,
                'response': {
                    'sid': message.sid,
                    'status': message.status,
                    'recipient': recipient
                }
            }

        except TwilioException as e:
            error_code = getattr(e, 'code', None)
            if error_code == 21211:
                logger.error(f"Invalid phone number for tenant {self.tenant_id}: {recipient}")
                return {'success': False, 'error': 'invalid_number', 'response': None}
            elif error_code == 20003:
                logger.error(f"Authentication error for tenant {self.tenant_id}")
                return {'success': False, 'error': 'auth_error', 'response': None}
            else:
                logger.error(f"Twilio error for tenant {self.tenant_id}: {str(e)}")
                return {'success': False, 'error': 'provider_error', 'response': None}

        except Exception as e:
            logger.error(f"SMS send error for tenant {self.tenant_id} to {recipient}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}

    async def send_bulk(self, recipients: list, content: dict, context: dict) -> dict:
        """
        Send SMS to multiple recipients

        Args:
            recipients: List of phone numbers
            content: SMS content
            context: Template context

        Returns:
            dict: Bulk send results
        """
        try:
            results = []
            success_count = 0
            failure_count = 0

            for recipient in recipients:
                result = await self.send(recipient, content, context)
                results.append({
                    'recipient': recipient,
                    'success': result['success'],
                    'error': result.get('error'),
                    'sid': result.get('response', {}).get('sid')
                })

                if result['success']:
                    success_count += 1
                else:
                    failure_count += 1

            logger.info(f"Bulk SMS sent: {success_count} success, {failure_count} failures")

            return {
                'success': True,
                'total_recipients': len(recipients),
                'success_count': success_count,
                'failure_count': failure_count,
                'results': results
            }

        except Exception as e:
            logger.error(f"Bulk SMS send error: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}

    async def check_status(self, message_sid: str) -> dict:
        """
        Check delivery status of an SMS message

        Args:
            message_sid: Twilio message SID

        Returns:
            dict: Message status information
        """
        try:
            client = self._get_twilio_client()
            message = client.messages(message_sid).fetch()

            return {
                'success': True,
                'response': {
                    'sid': message.sid,
                    'status': message.status,
                    'date_sent': message.date_sent.isoformat() if message.date_sent else None,
                    'date_updated': message.date_updated.isoformat() if message.date_updated else None,
                    'error_code': message.error_code,
                    'error_message': message.error_message
                }
            }

        except TwilioException as e:
            logger.error(f"Status check error for SID {message_sid}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}

    def estimate_cost(self, content: dict, context: dict, country_code: str = 'US') -> dict:
        """
        Estimate cost for sending SMS

        Args:
            content: SMS content
            context: Template context
            country_code: Destination country code

        Returns:
            dict: Cost estimation
        """
        try:
            rendered_content = self._render_content(content, context)
            message_length = len(rendered_content.get('body', ''))

            return self._estimate_cost(message_length, country_code)

        except Exception as e:
            logger.error(f"Cost estimation error: {str(e)}")
            return {
                'segments': 1,
                'estimated_cost': 0.01,
                'currency': 'USD',
                'error': str(e)
            }