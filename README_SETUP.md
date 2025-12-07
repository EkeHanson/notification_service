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

For **new tenants** (automatic setup):
```bash
# Configure your email credentials in .env file first
# Then start the notification service
docker-compose up -d

# Start event processing
python manage.py process_events --topics auth-events app-events security-events

# Tenants can now send events immediately - no manual setup required!
```

**Docker Environment Variables:**
The Docker containers automatically load all notification credentials from your `.env` file. Make sure to uncomment and configure the appropriate variables:

```bash
# For email notifications
EMAIL_HOST=mail.privateemail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=support@cmvp.net
EMAIL_HOST_PASSWORD=your-actual-password
DEFAULT_FROM_EMAIL=support@cmvp.net
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
# Just start sending events - the system will use fallbacks
```

**How it works:**
- When a tenant sends their first notification event, the system automatically creates default credentials if none exist
- Default credentials are configured globally in `notification_service/settings.py` and can be overridden via environment variables
- Tenants can upgrade to custom credentials later using the manual setup process or API

**Default Credentials Location:**
The default credentials are defined in `notification_service/notification_service/settings.py`:

```python
# Default notification credentials (configurable via environment variables)
DEFAULT_EMAIL_CREDENTIALS = {
    'smtp_host': env('DEFAULT_SMTP_HOST', default='smtp.gmail.com'),
    'smtp_port': env.int('DEFAULT_SMTP_PORT', default=587),
    'username': env('DEFAULT_SMTP_USERNAME', default='test@example.com'),
    'password': env('DEFAULT_SMTP_PASSWORD', default='test_password'),
    'from_email': env('DEFAULT_FROM_EMAIL', default='noreply@example.com'),
    'use_ssl': env.bool('DEFAULT_SMTP_USE_SSL', default=False)
}

# Django global email configuration
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='test@example.com')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='test_password')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@example.com')
```

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

# Create/update credentials
POST /api/notifications/credentials/
{
  "channel": "email",
  "credentials": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from_email": "noreply@yourcompany.com",
    "use_tls": true
  },
  "is_active": true
}

# Update existing credentials
PUT /api/notifications/credentials/{id}/
{
  "credentials": {
    "smtp_host": "smtp.office365.com",
    "smtp_port": 587,
    "username": "new-email@company.com",
    "password": "new-password",
    "from_email": "noreply@company.com",
    "use_tls": true
  }
}
```

**API Endpoints:**
- `GET /api/notifications/credentials/` - List tenant credentials
- `POST /api/notifications/credentials/` - Create or update credentials (use same channel to update existing)

**Note:** Individual credential updates/deletes require admin access. For programmatic credential management, use POST with the same channel to update existing credentials.

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
- `user.registration.completed` → Welcome email
- `user.password.reset.requested` → Password reset email/SMS
- `user.login.succeeded` → Security notification
- `user.login.failed` → Security alert

#### Application Events
- `invoice.payment.failed` → Payment failure notification
- `task.assigned` → Task assignment alert
- `comment.mentioned` → Mention notification
- `content.liked` → Engagement notification

#### Security Events
- `auth.2fa.code.requested` → 2FA code delivery
- `auth.2fa.attempt.failed` → Failed 2FA alert
- `auth.2fa.method.changed` → Security settings change

### Event Payload Format

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

#### Kafka Connection Issues
```bash
# Check Kafka connectivity
python manage.py process_events --topics test --max-events 1
```

#### Template Rendering Errors
```bash
# Check template placeholders
python manage.py shell
>>> from notifications.models import NotificationTemplate
>>> template = NotificationTemplate.objects.first()
>>> print(template.placeholders)
```

#### Credential Encryption Issues
```bash
# Re-encrypt credentials
python manage.py setup_tenant_credentials <tenant_id> --all --interactive
```

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

# Email (optional defaults)
DEFAULT_FROM_EMAIL=noreply@example.com
```

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

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs notification-service`
2. Verify credentials: `python manage.py setup_tenant_credentials <tenant_id> --all`
3. Test connectivity: `curl http://localhost:3001/api/notifications/health/`
4. Review event processing: `python manage.py process_events --topics test --max-events 1`

The notification service is now ready for production use! 🎉