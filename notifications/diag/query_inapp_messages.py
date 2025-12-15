#!/usr/bin/env python3
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.models import InAppMessage
import json

def run(tenant_id):
    qs = InAppMessage.objects.filter(tenant_id=tenant_id).order_by('-created_at')[:50]
    items = list(qs.values('id','recipient','title','body','status','created_at','read_at'))
    print(json.dumps({'count': len(items), 'items': items}, default=str, indent=2))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: query_inapp_messages.py <tenant_id>')
        sys.exit(1)
    run(sys.argv[1])
