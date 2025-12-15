#!/usr/bin/env python3
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.orchestrator.validator import validate_tenant_and_channel
from notifications.channels.email_handler import EmailHandler
from asgiref.sync import async_to_sync

def run_probe(tenant_id, recipient):
    creds = validate_tenant_and_channel(tenant_id, 'email')
    print('Probe: got creds summary, passing to EmailHandler')
    handler = EmailHandler(tenant_id, creds)
    content = {'subject': 'Probe Subject', 'body': 'Probe body'}
    context = {}
    try:
        result = async_to_sync(handler.send)(recipient, content, context)
        print('Probe send result:', result)
    except Exception as e:
        print('Probe send exception:', e)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: celery_email_send_probe.py <tenant_id> <recipient>')
        sys.exit(1)
    tenant_id = sys.argv[1]
    recipient = sys.argv[2]
    run_probe(tenant_id, recipient)
