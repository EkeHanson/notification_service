# Diagnostic script to check for recent login NotificationRecords
import os
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django environment (adjust if needed)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.models import NotificationRecord

# Adjust this to your tenant_id and recipient (username/email/user_id)
TENANT_ID = input('Enter tenant_id: ').strip()
RECIPIENT = input('Enter recipient (username/email/user_id): ').strip()

# Query for recent login notifications (last 10 minutes)
since = timezone.now() - timedelta(minutes=10)
qs = NotificationRecord.objects.filter(
    tenant_id=TENANT_ID,
    recipient=RECIPIENT,
    channel='inapp',
    created_at__gte=since
).order_by('-created_at')

print(f"Found {qs.count()} in-app NotificationRecords for tenant_id={TENANT_ID}, recipient={RECIPIENT} in last 10 minutes:")
for n in qs:
    print(f"ID: {n.id}, Created: {n.created_at}, Context: {n.context}")
