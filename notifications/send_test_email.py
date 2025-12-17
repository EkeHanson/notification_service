import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
    django.setup()
    from notifications.channels.email_handler import EmailHandler
    from notifications.models import TenantCredentials, ChannelType
    import uuid

    # Use a known tenant_id and recipient for test
    tenant_id = os.environ.get('TEST_TENANT_ID', '7ac6d583-c421-42bc-b94a-6e31f2bc9e63')
    recipient = os.environ.get('TEST_EMAIL_RECIPIENT', 'your_test_email@example.com')
    creds = TenantCredentials.objects.filter(tenant_id=tenant_id, channel=ChannelType.EMAIL.value).first()
    if not creds:
        print('No TenantCredentials found for tenant:', tenant_id)
        return
    handler = EmailHandler(tenant_id, creds.credentials)
    content = {
        'subject': 'Test Email from Notification Service',
        'body': 'This is a test email sent at {{now}}.'
    }
    context = {'now': django.utils.timezone.now()}
    result = handler.send_async(recipient, content, context)
    print('Send result:', result)

if __name__ == '__main__':
    main()
