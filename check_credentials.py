import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.models import TenantCredentials

tenant_id = '7ac6d583-c421-42bc-b94a-6e31f2bc9e63'
channel = 'email'

tc = TenantCredentials.objects.filter(tenant_id=tenant_id, channel=channel).first()
if not tc:
    print('No TenantCredentials found')
else:
    print('Credentials found')
    print('Active:', tc.is_active)
    print('Is custom:', tc.is_custom)
    creds = tc.credentials
    print('SMTP Host:', creds.get('smtp_host'))
    print('SMTP Port:', creds.get('smtp_port'))
    print('Username:', creds.get('username'))
    print('From Email:', creds.get('from_email'))
    print('Use SSL:', creds.get('use_ssl'))
    print('Use TLS:', creds.get('use_tls'))