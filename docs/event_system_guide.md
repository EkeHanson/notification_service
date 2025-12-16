# Event-Driven Notification System

This guide explains how to use the extended notification service that supports event-driven notifications for various application events.

## Overview

The notification service now supports **11 event types** across authentication, application, and security domains. Events are consumed from Kafka topics and automatically trigger notifications via appropriate channels.

## Supported Event Types

### 🔐 Authentication Events
- `user.registration.completed` → Welcome emails + in-app notifications
- `user.password.reset.requested` → Password reset emails/SMS
- `user.login.succeeded` → Security notification emails
- `user.login.failed` → Security alerts (email/SMS/push)

### 📱 Application Events
- `invoice.payment.failed` → Payment failure notifications (email/SMS/push)
- `task.assigned` → Task assignment alerts (email/in-app/push)
- `comment.mentioned` → Mention notifications (email/in-app/push)
- `content.liked` → Engagement notifications (in-app/push)

### 🔒 Security Events
- `auth.2fa.code.requested` → 2FA codes (SMS/email/in-app)
- `auth.2fa.attempt.failed` → 2FA failure alerts (email/SMS/push)
- `auth.2fa.method.changed` → Security setting updates (email/SMS/in-app)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Other Services │───▶│     Kafka       │───▶│ Notification    │
│ (Auth, HR, etc.)│    │   Topics        │    │ Service         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                │
                                                ▼
                                   ┌─────────────────┐
                                   │ Event Handlers  │
                                   │ - Auth Events   │
                                   │ - App Events    │
                                   │ - Security      │
                                   └─────────────────┘
                                                │
                                                ▼
                                   ┌─────────────────┐
                                   │ Channel Senders │
                                   │ - Email         │
                                   │ - SMS           │
                                   │ - Push          │
                                   │ - In-App        │
                                   └─────────────────┘
```

## Setup Instructions

### 1. Start Kafka Consumer

Run the Kafka consumer to process events:

```bash
# Using Docker
docker-compose exec notifications-service python manage.py start_kafka_consumer

# Or locally
python manage.py start_kafka_consumer
```

### 2. Seed Default Templates

Create default notification templates for all event types:

```bash
python manage.py seed_event_templates --tenant-id YOUR_TENANT_ID
```

### 3. Configure Kafka Topics

Ensure these topics exist in your Kafka cluster:
- `auth-events`
- `hr-events`
- `billing-events`
- `app-events`

## Publishing Events

### From Authentication Service

```python
from notifications.utils.kafka_producer import publish_event

# User registration with username + password
await publish_event('auth-events', {
    'event_type': 'user.registration.completed',
    'tenant_id': tenant_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': str(user.id),
        'username': user.username,  # Will show "Username: johndoe"
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'send_credentials': True,
        'temp_password': generated_temp_password,
        'login_link': 'https://app.example.com/login'
    }
})

# User registration with email + password (no username provided)
await publish_event('auth-events', {
    'event_type': 'user.registration.completed',
    'tenant_id': tenant_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': str(user.id),
        'username': '',  # Empty username, will show email instead
        'email': user.email,  # Will show "Email: user@example.com"
        'first_name': user.first_name,
        'last_name': user.last_name,
        'send_credentials': True,
        'temp_password': generated_temp_password,
        'login_link': 'https://app.example.com/login'
    }
})

# User registration without credentials
await publish_event('auth-events', {
    'event_type': 'user.registration.completed',
    'tenant_id': tenant_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': str(user.id),
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'send_credentials': False  # No credentials in email
    }
})

# Password reset
await publish_event('auth-events', {
    'event_type': 'user.password.reset.requested',
    'tenant_id': tenant_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': str(user.id),
        'email': user.email,
        'phone': user.phone,
        'reset_token': reset_token,
        'expires_at': expires_at.isoformat(),
        'ip_address': request.META.get('REMOTE_ADDR'),
        'reset_link': f'https://app.example.com/reset-password?token={reset_token}'  # Optional
    }
})
```

### From HR/Service Management

```python
# Task assignment
await publish_event('hr-events', {
    'event_type': 'task.assigned',
    'tenant_id': tenant_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': str(assignee.id),
        'task_id': str(task.id),
        'task_title': task.title,
        'task_description': task.description,
        'assigned_by': f"{assigner.first_name} {assigner.last_name}",
        'due_date': task.due_date.isoformat(),
        'priority': task.priority
    }
})
```

### From Billing Service

```python
# Payment failure
await publish_event('billing-events', {
    'event_type': 'invoice.payment.failed',
    'tenant_id': tenant_id,
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': str(user.id),
        'invoice_id': invoice.id,
        'amount': float(invoice.amount),
        'currency': invoice.currency,
        'failure_reason': 'insufficient_funds',
        'next_retry_date': retry_date.isoformat(),
        'payment_method': 'credit_card'
    }
})
```

## Customizing Notifications

### Override Default Templates

```python
# Create custom template for user registration
NotificationTemplate.objects.create(
    tenant_id=tenant_id,
    name='user_registration_completed_email',
    channel='email',
    content={
        'subject': 'Welcome to {{company_name}}, {{first_name}}!',
        'body': '''
        Dear {{first_name}},

        Welcome to {{company_name}}! Your account is now active.

        Best regards,
        {{company_name}} Team
        '''
    },
    placeholders=['first_name', 'company_name'],
    is_active=True
)
```

### Configure Channel Preferences

```python
# Disable SMS for certain events
# Update handler or create tenant-specific configuration
```

## Monitoring & Analytics

### Check Event Processing

```python
# View processed notifications
notifications = NotificationRecord.objects.filter(
    tenant_id=tenant_id,
    created_at__gte=datetime.now() - timedelta(days=1)
).values('channel', 'status').annotate(count=Count('id'))
```

### Monitor Kafka Consumer

```bash
# Check consumer logs
docker-compose logs notifications-service | grep kafka

# Monitor consumer lag
# Use Kafka tools or monitoring dashboard
```

## Error Handling

### Event Validation Errors
- Invalid event structure → logged and skipped
- Unsupported event type → logged and skipped
- Missing tenant ID → logged and skipped

### Notification Failures
- Channel-specific errors are retried automatically
- Failed notifications are logged with error details
- Analytics track success/failure rates

### Recovery
```bash
# Restart consumer on failure
docker-compose restart notifications-service

# Reprocess failed events (manual intervention may be needed)
```

## Testing Events

### Manual Event Publishing

```python
# Test event from Django shell
from notifications.events.registry import event_registry
from datetime import datetime

test_event = {
    'event_type': 'user.registration.completed',
    'tenant_id': 'your-tenant-id',
    'timestamp': datetime.utcnow().isoformat(),
    'payload': {
        'user_id': 'test-user-id',
        'username': 'testuser',  # Will show "Username: testuser"
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'send_credentials': True,
        'temp_password': 'TempPass123!',
        'login_link': 'https://app.example.com/login'
    }
}

result = event_registry.process_event(test_event)
print(f"Event processed: {result}")
```

### Mock Event Testing

```python
# Create mock event handlers for testing
from notifications.events.base_handler import BaseEventHandler

class MockEventHandler(BaseEventHandler):
    def can_handle(self, event_type):
        return event_type == 'test.event'

    def get_template_data(self, payload):
        return payload

    def _get_email_content(self, event_type, context):
        return {'subject': 'Test', 'body': 'Test email'}
```

## Best Practices

### Event Publishing
- Always include `tenant_id` for multi-tenant isolation
- Use ISO format for timestamps
- Include relevant user IDs for proper routing
- Keep payloads minimal but complete

### Template Design
- Use clear, actionable language
- Include relevant context (names, dates, amounts)
- Provide next steps or contact information
- Consider mobile-friendly formatting

### Monitoring
- Set up alerts for high failure rates
- Monitor Kafka consumer lag
- Track notification delivery times
- Log security-related events

### Performance
- Events are processed asynchronously
- Templates are cached for performance
- Failed notifications are retried with backoff
- Consider rate limiting for high-volume events

## Troubleshooting

### Consumer Not Starting
```bash
# Check Kafka connection
docker-compose logs kafka

# Verify environment variables
echo $KAFKA_BOOTSTRAP_SERVERS

# Check consumer logs
docker-compose logs notifications-service
```

### Events Not Processing
```bash
# Check event structure
# Verify tenant ID format
# Confirm event type is supported
# Check handler registration
```

### Templates Not Applied
```bash
# Verify template exists for tenant/channel
# Check template is_active flag
# Validate placeholder variables
```

## Future Extensions

- **Event Filtering**: Allow tenants to enable/disable specific events
- **Custom Handlers**: Support tenant-specific event handlers
- **Event Scheduling**: Delay notifications for specific times
- **Bulk Events**: Handle events affecting multiple users
- **Event Archiving**: Store processed events for audit/compliance