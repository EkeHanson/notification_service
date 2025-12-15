#!/usr/bin/env python3
import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.models import InAppMessage, NotificationRecord, NotificationStatus

def create(tenant_id, recipient='all', title='Test in-app', body='This is a test in-app message'):
    record = NotificationRecord.objects.create(
        tenant_id=tenant_id,
        channel='inapp',
        recipient=recipient,
        context={},
        status=NotificationStatus.PENDING.value
    )

    msg = InAppMessage.objects.create(
        tenant_id=tenant_id,
        notification_record=record,
        recipient=recipient,
        title=title,
        body=body,
        status='sent',
        expires_at=timezone.now() + timedelta(days=7)
    )
    print('Created InAppMessage:', msg.id)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: create_test_inapp.py <tenant_id> [recipient]')
        sys.exit(1)
    tenant_id = sys.argv[1]
    recipient = sys.argv[2] if len(sys.argv) > 2 else 'all'
    create(tenant_id, recipient)
