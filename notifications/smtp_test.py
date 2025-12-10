import smtplib, ssl
from notifications.models import TenantCredentials
from notifications.utils.encryption import decrypt_data

tenant_id='7ac6d583-c421-42bc-b94a-6e31f2bc9e63'
channel='email'

tc=TenantCredentials.objects.filter(tenant_id=tenant_id, channel=channel).first()
if not tc:
    print('No TenantCredentials found')
    raise SystemExit(1)
creds=tc.credentials
username=creds.get('username')
enc_pw=creds.get('password')
password = decrypt_data(enc_pw) if enc_pw and str(enc_pw).startswith('gAAAA') else creds.get('password')
host=creds.get('smtp_host')
port_ssl = int(creds.get('smtp_port') or 465)
print('HOST', host, 'PORT_SSL', port_ssl, 'USER', username, 'PW_LEN', len(password))

# Try SMTP_SSL
try:
    context=ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port_ssl, context=context, timeout=20) as s:
        s.set_debuglevel(1)
        s.login(username, password)
    print('AUTH_OK_SSL')
except Exception as e:
    print('AUTH_ERR_SSL', type(e).__name__, str(e))

# Try STARTTLS on 587
try:
    with smtplib.SMTP(host, 587, timeout=20) as s:
        s.set_debuglevel(1)
        s.ehlo()
        s.starttls(context=ssl.create_default_context())
        s.ehlo()
        s.login(username, password)
    print('AUTH_OK_STARTTLS')
except Exception as e:
    print('AUTH_ERR_STARTTLS', type(e).__name__, str(e))
