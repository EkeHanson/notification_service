# Notification Service Setup Guide

This guide walks you through setting up the Notification Service for production use, including Kafka event processing, tenant credentials, and notification templates.

## 🚀 Quick Start

### 1. Environment Setup

Ensure you have the following services running:
- PostgreSQL database
- Redis (for Celery and WebSocket channels)
- Kafka (for event processing)
- Auth Service (for tenant validation)

### 2. Install Dependencies

```bash
cd notification_service
pip install -r requirements.txt
```

### 3. Database Setup

```bash
python manage.py migrate
```

### 4. Start Services

```bash
# Start the notification service
docker-compose up -d

# Start event processing (Kafka consumer)
python manage.py process_events --topics auth-events app-events security-events

# Start Celery workers for async notification sending
celery -A notification_service worker -l info
```

**Docker Environment Variables:**
The Docker containers automatically load all notification credentials from your `.env` file. For development/testing, use MailHog:

```bash
# For email notifications (Development/Testing with MailHog)
EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=test@example.com

# For production email (uncomment and configure)
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_SSL=False
# EMAIL_HOST_USER=your-email@gmail.com
# EMAIL_HOST_PASSWORD=your-app-password
# DEFAULT_FROM_EMAIL=noreply@yourcompany.com
```

**Testing Docker Configuration:**
After starting the containers, test that environment variables are loaded correctly:

```bash
# Enter the running container
docker exec -it notifications /bin/bash

# Run the environment test script
python test_docker_env.py
```

This will verify that all credentials and settings are properly configured in the Docker environment.

For **existing tenants** or **custom credentials**:
```bash
# Run tenant setup for custom credentials
python setup_tenant.py <tenant_id> --interactive
```

### 5. Tenant Setup (Automated or Automatic)

#### Option 1: Manual Setup (for custom credentials)
For tenants requiring custom notification credentials:

```bash
# Interactive setup (recommended for production)
python setup_tenant.py 550e8400-e29b-41d4-a716-446655440000 --interactive

# Or use default credentials for development
python setup_tenant.py 550e8400-e29b-41d4-a716-446655440000
```

#### Option 2: Automatic Setup (Plug-and-Play)
Tenants from the auth-service can now use the notification service immediately without setup:

```bash
# No setup required! Tenants automatically get default credentials
# Just start sending events via Kafka - the system will use fallbacks
```

**How it works:**
- When a tenant sends their first notification event via Kafka, the system automatically creates default credentials if none exist
- Default credentials use test/development settings suitable for initial setup
- Tenants can upgrade to custom credentials later using the manual setup process

**Default Credentials Location:**
The default credentials are defined in `notification_service/notification_service/settings.py`:

```python
# Default notification credentials (configurable via environment variables)
# These are used for new tenants who haven't set up custom credentials
DEFAULT_EMAIL_CREDENTIALS = {
    'smtp_host': env('EMAIL_HOST', default='mailhog'),          # MailHog for testing
    'smtp_port': int(env('EMAIL_PORT', default='1025') or '1025'),
    'username': env('EMAIL_HOST_USER', default=''),             # No auth for MailHog
    'password': env('EMAIL_HOST_PASSWORD', default=''),         # No auth for MailHog
    'from_email': env('DEFAULT_FROM_EMAIL', default='test@example.com'),
    'use_ssl': env.bool('EMAIL_USE_SSL', default=False)         # No SSL for MailHog
}

# Django global email configuration
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='mailhog')
EMAIL_PORT = env.int('EMAIL_PORT', default=1025)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='test@example.com')
```

**Credential Priority System:**
The system uses a smart credential hierarchy:

1. **Custom Tenant Credentials** (`is_custom=True`): Used exclusively when tenants configure their own credentials via API
2. **Auto-generated Defaults** (`is_custom=False`): Working defaults created automatically for new tenants
3. **Settings Defaults**: Fallback credentials from `settings.py` for brand new tenants

**Important:** Once a tenant sets up custom credentials (`is_custom=True`), the system will ONLY use those credentials - no automatic fallback to defaults. This ensures tenants are responsible for maintaining their own notification delivery.

**Updating Default Credentials:**
1. **Via Environment Variables** (recommended for production):
   ```bash
   # Email defaults
   export DEFAULT_SMTP_HOST="smtp.your-email-provider.com"
   export DEFAULT_SMTP_PORT="587"
   export DEFAULT_SMTP_USERNAME="your-email@domain.com"
   export DEFAULT_SMTP_PASSWORD="your-secure-password"
   export DEFAULT_FROM_EMAIL="noreply@yourdomain.com"
   export DEFAULT_SMTP_USE_SSL="False"

   # Django global email settings
   export EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
   export EMAIL_HOST="smtp.your-email-provider.com"
   export EMAIL_PORT="587"
   export EMAIL_USE_SSL="False"
   export EMAIL_HOST_USER="your-email@domain.com"
   export EMAIL_HOST_PASSWORD="your-secure-password"
   export DEFAULT_FROM_EMAIL="noreply@yourdomain.com"
   ```

2. **Via Settings File** (for development):
   Edit `notification_service/notification_service/settings.py` and modify the `DEFAULT_*_CREDENTIALS` dictionaries.

3. **Via API** (per tenant):
   Use the credentials API endpoint to set tenant-specific credentials.

#### Option 3: API-Based Setup (REST API)
Tenants can manage their credentials programmatically via REST API:

```bash
# List current credentials
GET /api/notifications/credentials/

# Create custom credentials (is_custom automatically set to true)
POST /api/notifications/credentials/
{
  "channel": "email",
  "credentials": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from_email": "noreply@yourcompany.com",
    "use_ssl": false,
    "use_tls": true
  },
  "is_custom": false,
  "is_active": true
}

# Update existing custom credentials
PUT /api/notifications/credentials/{id}/
{
  "credentials": {
    "smtp_host": "smtp.office365.com",
    "smtp_port": 587,
    "username": "new-email@company.com",
    "password": "new-password",
    "from_email": "noreply@company.com",
    "use_ssl": false,
    "use_tls": true
  },
  "is_active": true
}
```

**API Endpoints:**
- `GET /api/notifications/credentials/` - List tenant credentials (shows `is_custom` field)
- `POST /api/notifications/credentials/` - Create custom credentials (`is_custom` set to `true`)
- `PUT /api/notifications/credentials/{id}/` - Update existing credentials

**Important Notes:**
- Credentials created via API are marked as `is_custom=true`
- Custom credentials take priority and have **no automatic fallback**
- If custom credentials fail, tenants must fix them manually
- Only use custom credentials when you're confident they work

### 5. Start Services

```bash
# Start the web service
docker-compose up -d

# Start event processing
python manage.py process_events --topics auth-events app-events security-events
```

## 📧 Detailed Setup Instructions

### Step 1: Configure Kafka Consumers

The notification service processes events from Kafka topics. Configure your topics:

```bash
# Process authentication events
python manage.py process_events --topics auth-events

# Process all event types
python manage.py process_events --topics auth-events app-events security-events
```

**Environment Variables:**
```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_GROUP_ID=notification-service
```

### Step 2: Set Up Tenant Credentials

#### Email Credentials
```bash
# Interactive setup
python manage.py setup_tenant_credentials 550e8400-e29b-41d4-a716-446655440000 --email --interactive

# Required fields:
# - SMTP Host (smtp.gmail.com)
# - SMTP Port (587)
# - Username (your-email@gmail.com)
# - Password (app-specific password)
# - From Email (noreply@yourcompany.com)
# - Use TLS (true)
```

#### SMS Credentials (Twilio)
```bash
python manage.py setup_tenant_credentials 550e8400-e29b-41d4-a716-446655440000 --sms --interactive

# Required fields:
# - Account SID (ACxxxxxxxxxxxxxxxx)
# - Auth Token (your_auth_token)
# - From Number (+1234567890)
```

#### Push Credentials (Firebase)
```bash
python manage.py setup_tenant_credentials 550e8400-e29b-41d4-a716-446655440000 --push --interactive

# Required: Path to Firebase service account JSON file
# Download from Firebase Console > Project Settings > Service Accounts
```

### Step 3: Create Notification Templates

```bash
# Create default templates for all event types
python manage.py setup_notification_templates 550e8400-e29b-41d4-a716-446655440000

# Overwrite existing templates if needed
python manage.py setup_notification_templates 550e8400-e29b-41d4-a716-446655440000 --overwrite
```

## 🔧 Manual Setup (Alternative)

If you prefer manual setup instead of the automated script:

### 1. Create Credentials Manually

```python
from notifications.models import TenantCredentials
from notifications.utils.encryption import encrypt_data

# Email credentials
TenantCredentials.objects.create(
    tenant_id='550e8400-e29b-41d4-a716-446655440000',
    channel='email',
    credentials={
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'your-email@gmail.com',
        'password': encrypt_data('your-password'),
        'from_email': 'noreply@company.com',
        'use_tls': True
    }
)

# SMS credentials
TenantCredentials.objects.create(
    tenant_id='550e8400-e29b-41d4-a716-446655440000',
    channel='sms',
    credentials={
        'account_sid': 'ACxxxxxxxxxxxxxxxx',
        'auth_token': encrypt_data('your_auth_token'),
        'from_number': '+1234567890'
    }
)
```

### 2. Create Templates Manually

```python
from notifications.models import NotificationTemplate

# Welcome email template
NotificationTemplate.objects.create(
    tenant_id='550e8400-e29b-41d4-a716-446655440000',
    name='User Registration Welcome',
    channel='email',
    content={
        'subject': 'Welcome to {{tenant_name}}!',
        'body': 'Hi {{first_name}}, welcome to our platform!'
    },
    placeholders=['first_name', 'tenant_name']
)
```

## 📊 Event Processing

### Supported Event Types

The service automatically processes these event types:

#### Authentication Events
- `user.registration.completed` → Welcome email + in-app notification
- `user.password.reset.requested` → Password reset email/SMS
- `user.login.succeeded` → Security notification + in-app alert
- `user.login.failed` → Security alert (email/SMS/push/in-app)

#### Application Events
- `invoice.payment.failed` → Payment failure notification
- `task.assigned` → Task assignment alert
- `comment.mentioned` → Mention notification
- `content.liked` → Engagement notification

#### Security Events
- `auth.2fa.code.requested` → 2FA code delivery
- `auth.2fa.attempt.failed` → Failed 2FA alert
- `auth.2fa.method.changed` → Security settings change

#### Document Events
- `user.document.expiry.warning` → Document expiring soon (30, 14, 7, 3, 1 days)
- `user.document.expired` → Document has expired

#### In-App Notification Events
- Real-time WebSocket notifications for urgent alerts
- User-specific and tenant-wide broadcasts
- Automatic delivery to connected React clients

### Event Payload Format

#### Authentication Events
```json
{
  "event_type": "user.registration.completed",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T12:00:00Z",
  "payload": {
    "user_id": "uuid",
    "email": "user@example.com",
    "first_name": "John"
  },
  "metadata": {
    "source": "auth_service",
    "version": "1.0"
  }
}
```

#### Document Events
```json
{
  "event_type": "user.document.expiry.warning",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T12:00:00Z",
  "payload": {
    "full_name": "John Doe",
    "user_email": "john@example.com",
    "document_type": "Driver's Licence",
    "document_name": "Driver's Licence",
    "expiry_date": "2024-01-15",
    "days_left": 7,
    "message": "Your Driver's Licence is expiring soon. Please renew immediately to avoid employment disruption.",
    "timezone": "Africa/Lagos"
  },
  "metadata": {
    "event_id": "evt-uuid-here",
    "source": "application-system",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### 2FA Events with Tenant Details (Recommended Architecture)
```json
{
  "event_type": "auth.2fa.code.requested",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T12:00:00Z",
  "payload": {
    "user_id": "user-uuid",
    "user_email": "john@example.com",
    "user_first_name": "John",
    "user_last_name": "Doe",
    "2fa_code": "123456",
    "method": "email",
    "expires_at": "2024-01-01T12:15:00Z",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "tenant_details": {
      "name": "Acme Corporation",
      "logo_url": "https://acme.com/logo.png",
      "primary_color": "#007bff",
      "secondary_color": "#6c757d",
      "email_from": "noreply@acme.com"
    }
  },
  "metadata": {
    "event_id": "evt-uuid-here",
    "source": "auth-service",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

**Note:** Including `tenant_details` in the event payload eliminates the need for the notification service to make API calls back to the auth-service, improving decoupling and resilience.

#### Login Events
```json
{
  "event_type": "user.login.succeeded",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T12:00:00Z",
  "payload": {
    "user_email": "john@example.com",
    "login_time": "2024-01-01T12:00:00Z",
    "ip_address": "192.168.1.100",
    "location": "Lagos, Nigeria",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  },
  "metadata": {
    "event_id": "evt-uuid-here",
    "source": "auth-service",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

```json
{
  "event_type": "user.login.failed",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T12:00:00Z",
  "payload": {
    "user_email": "john@example.com",
    "login_time": "2024-01-01T12:00:00Z",
    "ip_address": "192.168.1.100",
    "location": "Unknown Location",
    "failure_reason": "Invalid password",
    "attempt_count": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  },
  "metadata": {
    "event_id": "evt-uuid-here",
    "source": "auth-service",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

## 🔍 Monitoring & Troubleshooting

### Check Service Health
```bash
curl http://localhost:3001/api/notifications/health/
```

### View Processing Logs
```bash
# Event processing logs
docker-compose logs notification-service

# Celery worker logs
docker-compose logs celery-worker
```

### Monitor Queues
```bash
# Flower dashboard (Celery monitoring)
open http://localhost:5556
```

### Common Issues

#### Email Testing with MailHog
```bash
# Start MailHog (included in docker-compose.yml)
docker-compose up mailhog

# View sent emails in browser
open http://localhost:8025

# Test email sending
curl -X POST http://localhost:3001/api/notifications/test-email/ \
  -H "Content-Type: application/json" \
  -d '{"recipient": "test@example.com", "subject": "Test", "body": "Hello {name}!", "context": {"name": "World"}}'
```

#### Kafka Connection Issues
```bash
# Check Kafka connectivity
python manage.py process_events --topics test --max-events 1
```

#### Template Rendering Errors
Templates support both `{variable}` and `{{variable}}` syntax. If variables aren't rendering:
```bash
# Check template content
python manage.py shell
>>> from notifications.models import NotificationTemplate
>>> template = NotificationTemplate.objects.filter(channel='email').first()
>>> print("Subject:", template.content.get('subject'))
>>> print("Body:", template.content.get('body'))
```

#### Credential Issues
```bash
# Check tenant credentials
python manage.py shell
>>> from notifications.models import TenantCredentials
>>> creds = TenantCredentials.objects.filter(tenant_id='your-tenant-id', channel='email')
>>> for cred in creds:
...     print(f"is_custom: {cred.is_custom}, active: {cred.is_active}")
...     print(f"credentials: {cred.credentials}")

# Reset to defaults (removes custom credentials)
>>> TenantCredentials.objects.filter(tenant_id='your-tenant-id', channel='email').delete()
```

#### Credential Priority Issues
- **Custom credentials** (`is_custom=True`): Used exclusively, no fallback
- **Auto-generated defaults** (`is_custom=False`): Working defaults for new tenants
- **Settings defaults**: Fallback for brand new tenants

If emails aren't sending with custom credentials, check that they're properly configured and working.

## 🚀 Production Deployment

### Docker Compose Setup

```yaml
version: '3.8'
services:
  notification-service:
    build: .
    environment:
      - DJANGO_SETTINGS_MODULE=notification_service.settings
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - DATABASE_URL=postgresql://...
    ports:
      - "3001:8000"
    depends_on:
      - postgres
      - redis
      - kafka

  celery-worker:
    build: .
    command: celery -A notification_service worker -l info
    environment:
      - DJANGO_SETTINGS_MODULE=notification_service.settings
    depends_on:
      - redis
      - notification-service
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/notifications

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Auth Service
AUTH_SERVICE_URL=http://localhost:8000

# Encryption
ENCRYPTION_KEY=your-32-character-encryption-key

# Email Configuration (Production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourcompany.com

# SMS (Production)
DEFAULT_TWILIO_ACCOUNT_SID=your-twilio-account-sid
DEFAULT_TWILIO_AUTH_TOKEN=your-twilio-auth-token
DEFAULT_TWILIO_FROM_NUMBER=+1234567890

# Push Notifications (Production)
DEFAULT_FIREBASE_PROJECT_ID=your-firebase-project-id
DEFAULT_FIREBASE_PRIVATE_KEY_ID=your-private-key-id
DEFAULT_FIREBASE_PRIVATE_KEY=your-private-key
DEFAULT_FIREBASE_CLIENT_EMAIL=firebase@your-project.iam.gserviceaccount.com
DEFAULT_FIREBASE_CLIENT_ID=your-client-id
DEFAULT_FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/firebase@your-project.iam.gserviceaccount.com
```

### Credential Management in Production

**Important:** The system uses a hierarchical credential system:

1. **Custom Tenant Credentials** (`is_custom=true`): Tenants configure via API, no fallback
2. **Auto-generated Defaults** (`is_custom=false`): Working defaults for new tenants
3. **Settings Defaults**: Fallback from environment variables

**Production Setup:**
- Configure working defaults in environment variables
- Tenants can override with custom credentials via API
- Monitor credential health and tenant notification delivery
- Custom credentials take precedence and have no automatic fallback

### Scaling Considerations

- **Horizontal Scaling**: Run multiple instances behind a load balancer
- **Celery Workers**: Scale based on notification volume
- **Database**: Use read replicas for analytics queries
- **Kafka**: Increase partitions for high-throughput topics

## 🧪 Testing Setup

### Run Tests
```bash
python run_tests.py
```

### Email Testing with MailHog
```bash
# Start MailHog (automatically included in docker-compose.yml)
docker-compose up mailhog

# Access MailHog web interface
open http://localhost:8025

# Send test email via API
curl -X POST http://localhost:3001/api/notifications/test-email/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "recipient": "test@example.com",
    "subject": "Test Email",
    "body": "Hello {name}, your code is {code}!",
    "context": {"name": "John", "code": "123456"}
  }'

# Check MailHog for the sent email
# Expected result: Properly branded email with tenant name, formatted timestamps, and working templates
```

### Email Branding & Templates
The system now supports:
- ✅ **Tenant-specific branding**: Shows actual tenant name instead of "Default Company"
- ✅ **Proper timestamp formatting**: Converts ISO dates to readable format
- ✅ **Template variable support**: Both `{variable}` and `{{variable}}` syntax
- ✅ **Fallback branding**: Uses tenant ID prefix when auth service unavailable

**Example Improved Email:**
```
Tenant 7ac6d583

Hi John Doe,

Your two-factor authentication code is: 123456

This code will expire at 2024-01-01 12:00:00 UTC.

Best regards,
Tenant 7ac6d583 Security Team
```

### Test Event Processing
```bash
# Process limited events for testing
python manage.py process_events --max-events 5 --topics test-events
```

### Sample Test Event
```python
from notifications.consumers.event_consumer import event_consumer
import json

test_event = {
    "event_type": "user.registration.completed",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z",
    "payload": {
        "user_id": "test-user-id",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    }
}

success = event_consumer.process_event(test_event)
print(f"Event processed: {success}")
```

### Template Testing
Templates now support both `{variable}` and `{{variable}}` syntax:
```python
# Test template rendering
from notifications.channels.email_handler import EmailHandler

handler = EmailHandler("test-tenant", {})
content = {
    "subject": "Welcome {name}!",
    "body": "Your code is {code} and expires at {expires_at}."
}
context = {
    "name": "John",
    "code": "123456",
    "expires_at": "2024-01-01T12:00:00Z"
}

rendered = handler._render_content(content, context)
print("Subject:", rendered['subject'])  # "Welcome John!"
print("Body:", rendered['body'])        # "Your code is 123456 and expires at 2024-01-01T12:00:00Z."
```

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs notification-service`
2. Verify credentials: `python manage.py setup_tenant_credentials <tenant_id> --all`
3. Test connectivity: `curl http://localhost:3001/api/notifications/health/`
4. Review event processing: `python manage.py process_events --topics test --max-events 1`

The notification service is now ready for production use! 🎉