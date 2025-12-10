#!/usr/bin/env python3
import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

from notifications.orchestrator.validator import validate_tenant_and_channel
from notifications.models import TenantCredentials
import smtplib
import socket

def mask(s):
    s = s or ''
    return (s[:6] + '...') if len(s) > 6 else s

def probe(tenant_id, channel='email'):
    print(f'PROBE: tenant={tenant_id} channel={channel}')
    try:
        # Use validator to get decrypted or default creds
        creds = validate_tenant_and_channel(tenant_id, channel)
    except Exception as e:
        print('PROBE: validator error', e)
        # fallback: try raw TenantCredentials
        tc = TenantCredentials.objects.filter(tenant_id=tenant_id, channel=channel).first()
        if not tc:
            print('PROBE: no TenantCredentials found')
            return
        creds = tc.credentials

    pwd = creds.get('password', '') if isinstance(creds, dict) else ''
    print('PROBE: creds summary - smtp_host=%s smtp_port=%s username=%s password_preview=%s password_len=%d looks_encrypted=%s' % (
        creds.get('smtp_host'), creds.get('smtp_port'), creds.get('username'), mask(pwd), len(pwd), str(str(pwd).startswith('gAAAA'))
    ))

    if not creds.get('smtp_host') or not creds.get('username'):
        print('PROBE: missing smtp host or username, skipping auth probe')
        return

    try:
        timeout = 10
        if creds.get('use_ssl'):
            conn = smtplib.SMTP_SSL(host=creds.get('smtp_host'), port=int(creds.get('smtp_port') or 465), timeout=timeout)
        else:
            conn = smtplib.SMTP(host=creds.get('smtp_host'), port=int(creds.get('smtp_port') or 587), timeout=timeout)
        conn.ehlo()
        if creds.get('use_tls') and not creds.get('use_ssl'):
            conn.starttls()
            conn.ehlo()
        try:
            conn.login(creds.get('username'), creds.get('password'))
            print('PROBE: SMTP auth OK')
        except Exception as e:
            print('PROBE: SMTP auth FAILED:', e)
        finally:
            try:
                conn.quit()
            except Exception:
                pass

    except (socket.timeout, socket.error) as e:
        print('PROBE: SMTP connection error', e)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: celery_smtp_probe.py <tenant_id> [channel]')
        sys.exit(1)
    tenant_id = sys.argv[1]
    channel = sys.argv[2] if len(sys.argv) > 2 else 'email'
    probe(tenant_id, channel)
