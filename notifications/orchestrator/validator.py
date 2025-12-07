from notifications.utils.exceptions import TenantValidationError, ChannelNotConfiguredError
from notifications.models import TenantCredentials, ChannelType
from notifications.utils.encryption import encrypt_data
from django.conf import settings

def validate_tenant_and_channel(tenant_id: str, channel: str):
    # First try to get tenant-specific credentials
    creds = TenantCredentials.objects.filter(tenant_id=tenant_id, channel=channel, is_active=True).first()
    if creds:
        return creds.credentials

    # Fall back to default credentials if tenant-specific ones don't exist
    default_creds = _get_default_credentials(channel)
    if default_creds:
        # Create default credentials for this tenant to avoid repeated lookups
        TenantCredentials.objects.update_or_create(
            tenant_id=tenant_id,
            channel=channel,
            defaults={
                'credentials': _encrypt_credentials(default_creds, channel),
                'is_active': True
            }
        )
        return default_creds

    # If no default credentials available, raise error
    raise ChannelNotConfiguredError(f"Channel {channel} not configured for tenant {tenant_id} and no defaults available.")

def _get_default_credentials(channel: str) -> dict:
    """Get default credentials from settings"""
    if channel == ChannelType.EMAIL:
        return getattr(settings, 'DEFAULT_EMAIL_CREDENTIALS', {})

    elif channel == ChannelType.SMS:
        return getattr(settings, 'DEFAULT_SMS_CREDENTIALS', {})

    elif channel == ChannelType.PUSH:
        return getattr(settings, 'DEFAULT_PUSH_CREDENTIALS', {})

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