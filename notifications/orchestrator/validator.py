from notifications.utils.exceptions import TenantValidationError, ChannelNotConfiguredError
from notifications.models import TenantCredentials, ChannelType
from notifications.utils.encryption import encrypt_data
from django.conf import settings
import logging

logger = logging.getLogger('notifications.orchestrator')

def validate_tenant_and_channel(tenant_id: str, channel: str):
    # First check if tenant has ANY credentials (custom or auto-generated)
    existing_creds = TenantCredentials.objects.filter(
        tenant_id=tenant_id,
        channel=channel,
        is_active=True,
        is_deleted=False  # Ensure not soft-deleted
    ).first()

    if existing_creds:
        # If tenant has custom credentials, decrypt sensitive fields and return
        if existing_creds.is_custom:
            logger.info(f"Using custom tenant credentials for {channel}")
            return _decrypt_credentials(existing_creds.credentials, channel)
        # If tenant has auto-generated defaults, fall back to .env settings
        else:
            logger.info(f"Tenant has auto-generated credentials, falling back to .env settings for {channel}")
            return _get_env_credentials(channel)

    # If no credentials exist for this tenant, use .env defaults
    logger.info(f"No tenant credentials found, using .env defaults for {channel}")
    default_creds = _get_env_credentials(channel)
    if default_creds:
        # Create default credentials for this tenant (marked as non-custom)
        try:
            TenantCredentials.objects.get_or_create(
                tenant_id=tenant_id,
                channel=channel,
                defaults={
                    'credentials': _encrypt_credentials(default_creds, channel),
                    'is_active': True,
                    'is_custom': False  # Mark as auto-generated, not custom
                }
            )
        except Exception as e:
            # Handle race condition or other database errors
            logger.warning(f"Could not create default credentials for tenant {tenant_id}, channel {channel}: {e}")
        return default_creds

    # If no default credentials available, raise error
    raise ChannelNotConfiguredError(f"Channel {channel} not configured for tenant {tenant_id} and no defaults available.")

def _get_default_credentials(channel: str) -> dict:
    """Get default credentials from settings"""
    if channel == ChannelType.EMAIL.value:
        return getattr(settings, 'DEFAULT_EMAIL_CREDENTIALS', {})

    elif channel == ChannelType.SMS.value:
        return getattr(settings, 'DEFAULT_SMS_CREDENTIALS', {})

    elif channel == ChannelType.PUSH.value:
        return getattr(settings, 'DEFAULT_PUSH_CREDENTIALS', {})

    return {}

def _get_env_credentials(channel: str) -> dict:
    """Get credentials directly from environment variables (.env file)"""
    if channel == ChannelType.EMAIL.value:
        # Read from EMAIL_* variables that are set in .env
        return {
            'smtp_host': getattr(settings, 'EMAIL_HOST', 'mailhog'),
            'smtp_port': int(getattr(settings, 'EMAIL_PORT', 1025)),
            'username': getattr(settings, 'EMAIL_HOST_USER', ''),
            'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'test@example.com'),
            'use_ssl': getattr(settings, 'EMAIL_USE_SSL', 'False').lower() == 'true',
            'use_tls': getattr(settings, 'EMAIL_USE_TLS', 'False').lower() == 'true'
        }

    elif channel == ChannelType.SMS.value:
        return {
            'account_sid': getattr(settings, 'DEFAULT_TWILIO_ACCOUNT_SID', ''),
            'auth_token': getattr(settings, 'DEFAULT_TWILIO_AUTH_TOKEN', ''),
            'from_number': getattr(settings, 'DEFAULT_TWILIO_FROM_NUMBER', '')
        }

    elif channel == ChannelType.PUSH.value:
        return {
            'project_id': getattr(settings, 'DEFAULT_FIREBASE_PROJECT_ID', ''),
            'private_key_id': getattr(settings, 'DEFAULT_FIREBASE_PRIVATE_KEY_ID', ''),
            'private_key': getattr(settings, 'DEFAULT_FIREBASE_PRIVATE_KEY', ''),
            'client_email': getattr(settings, 'DEFAULT_FIREBASE_CLIENT_EMAIL', ''),
            'client_id': getattr(settings, 'DEFAULT_FIREBASE_CLIENT_ID', ''),
            'client_x509_cert_url': getattr(settings, 'DEFAULT_FIREBASE_CLIENT_X509_CERT_URL', '')
        }

    return {}

def _encrypt_credentials(credentials: dict, channel: str) -> dict:
    """Encrypt sensitive fields in credentials"""
    encrypted = credentials.copy()

    # Fields that need encryption
    sensitive_fields = {
        ChannelType.EMAIL: ['password'],
        ChannelType.SMS: ['auth_token'],
        ChannelType.PUSH: ['private_key']
    }

    for field in sensitive_fields.get(channel, []):
        if field in encrypted:
            encrypted[field] = encrypt_data(encrypted[field])

    return encrypted

def _decrypt_credentials(credentials: dict, channel: str) -> dict:
    """Decrypt sensitive fields in credentials"""
    from notifications.utils.encryption import decrypt_data
    decrypted = credentials.copy()

    # Fields that need decryption
    sensitive_fields = {
        ChannelType.EMAIL: ['password'],
        ChannelType.SMS: ['auth_token'],
        ChannelType.PUSH: ['private_key']
    }

    for field in sensitive_fields.get(channel, []):
        if field in decrypted and decrypted[field]:  # Only decrypt if field exists and is not empty
            try:
                decrypted[field] = decrypt_data(decrypted[field])
            except Exception as e:
                # If decryption fails, assume it's already plain text (like empty string for MailHog)
                logger.warning(f"Failed to decrypt {field} for {channel}, using as plain text: {e}")
                # Keep the original value

    return decrypted