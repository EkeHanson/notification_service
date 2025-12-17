import os
import django
import asyncio
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.channels.email_handler import EmailHandler
from notifications.models import TenantCredentials

@sync_to_async
def get_credentials(tenant_id, channel):
    return TenantCredentials.objects.filter(tenant_id=tenant_id, channel=channel).first()

async def main():
    tenant_id = '7ac6d583-c421-42bc-b94a-6e31f2bc9e63'
    channel = 'email'

    tc = await get_credentials(tenant_id, channel)
    if not tc:
        print('No TenantCredentials found')
        return

    handler = EmailHandler(tenant_id, tc.credentials)

    content = {
        'subject': 'Test Email from Notification Service',
        'body': 'This is a test email to verify emailing functionality.'
    }

    context = {}

    recipient = 'support@prolianceltd.com'  # Change to a real email if needed

    result = await handler.send(recipient, content, context)
    print('Send result:', result)

if __name__ == '__main__':
    asyncio.run(main())