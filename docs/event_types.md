# Notification Service Event Types

This document defines all supported event types for the Notification Service, including their payloads, recommended channels, and default templates.

## Event Type Structure

Each event follows this structure:
```json
{
  "event_type": "category.action.subaction",
  "tenant_id": "uuid",
  "user_id": "uuid", // optional
  "timestamp": "2024-01-01T12:00:00Z",
  "payload": {
    // event-specific data
  },
  "metadata": {
    "source": "auth_service",
    "version": "1.0"
  }
}
```

## 🔐 Authentication Events

### `user.registration.completed`
**Description**: Sent when a new user completes registration
**Recommended Channels**: Email, In-App
**Priority**: High

**Payload:**
```json
{
  "user_id": "uuid",
  "username": "johndoe",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "registration_date": "2024-01-01T12:00:00Z",
  "verification_required": true,
  "send_credentials": true,
  "temp_password": "TempPass123!",  // Only if send_credentials is true
  "login_link": "https://app.example.com/login"  // Optional login URL
}
```

**Default Templates:**
- **Email**: Welcome email with account verification
- **In-App**: Welcome notification with next steps

### `user.password.reset.requested`
**Description**: Sent when user requests password reset
**Recommended Channels**: Email, SMS
**Priority**: High

**Payload:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "phone": "+1234567890",
  "reset_token": "token_hash",
  "expires_at": "2024-01-01T13:00:00Z",
  "ip_address": "192.168.1.1",
  "reset_link": "https://app.example.com/reset-password?token=abc123"  // Optional custom link
}
```

**Default Templates:**
- **Email**: Password reset link
- **SMS**: Reset code for mobile verification

### `user.login.succeeded`
**Description**: Sent on successful login (optional security feature)
**Recommended Channels**: Email, In-App
**Priority**: Low

**Payload:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "login_time": "2024-01-01T12:00:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "location": "New York, US"
}
```

**Default Templates:**
- **Email**: Login notification with device details
- **In-App**: Recent login activity

### `user.login.failed`
**Description**: Sent on failed login attempts
**Recommended Channels**: Email, SMS, Push
**Priority**: High

**Payload:**
```json
{
  "email": "user@example.com",
  "attempt_time": "2024-01-01T12:00:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "failure_reason": "invalid_password",
  "attempt_count": 3
}
```

**Default Templates:**
- **Email**: Security alert with details
- **SMS**: Urgent security notification
- **Push**: Immediate security alert

## 📱 Application Events

### `invoice.payment.failed`
**Description**: Sent when invoice payment fails
**Recommended Channels**: Email, SMS, Push
**Priority**: High

**Payload:**
```json
{
  "user_id": "uuid",
  "invoice_id": "inv_123",
  "amount": 99.99,
  "currency": "USD",
  "failure_reason": "insufficient_funds",
  "next_retry_date": "2024-01-02T12:00:00Z",
  "payment_method": "credit_card"
}
```

**Default Templates:**
- **Email**: Payment failure details with retry options
- **SMS**: Urgent payment reminder
- **Push**: Payment failed notification

### `task.assigned`
**Description**: Sent when a task is assigned to a user
**Recommended Channels**: Email, In-App, Push
**Priority**: Medium

**Payload:**
```json
{
  "user_id": "uuid",
  "task_id": "task_123",
  "task_title": "Review quarterly report",
  "task_description": "Please review and approve the Q4 financial report",
  "assigned_by": "manager@example.com",
  "due_date": "2024-01-15T17:00:00Z",
  "priority": "high"
}
```

**Default Templates:**
- **Email**: Task details with action buttons
- **In-App**: Task assignment notification
- **Push**: New task alert

### `comment.mentioned`
**Description**: Sent when user is mentioned in a comment
**Recommended Channels**: Email, In-App, Push
**Priority**: Medium

**Payload:**
```json
{
  "user_id": "uuid",
  "comment_id": "comment_123",
  "comment_text": "Hey @john, can you review this?",
  "author_id": "uuid",
  "author_name": "Jane Smith",
  "entity_type": "document",
  "entity_id": "doc_456",
  "entity_title": "Project Proposal",
  "mentioned_at": "2024-01-01T12:00:00Z"
}
```

**Default Templates:**
- **Email**: Mention notification with context
- **In-App**: Real-time mention alert
- **Push**: Instant mention notification

### `content.liked`
**Description**: Sent when user's content receives a like/engagement
**Recommended Channels**: In-App, Push
**Priority**: Low

**Payload:**
```json
{
  "user_id": "uuid",
  "content_id": "post_123",
  "content_type": "post",
  "content_title": "My project update",
  "liked_by": "uuid",
  "liker_name": "Alice Johnson",
  "like_count": 15,
  "engagement_type": "like"
}
```

**Default Templates:**
- **In-App**: Engagement notification
- **Push**: Content interaction alert

## 🔒 Security Events

### `auth.2fa.code.requested`
**Description**: Sent when 2FA code is requested
**Recommended Channels**: SMS, Email, In-App
**Priority**: High

**Payload:**
```json
{
  "user_id": "uuid",
  "method": "sms", // sms, email, app
  "code": "123456", // only included for testing
  "expires_at": "2024-01-01T12:05:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

**Default Templates:**
- **SMS**: 2FA code delivery
- **Email**: Backup 2FA code
- **In-App**: 2FA request notification

### `auth.2fa.attempt.failed`
**Description**: Sent when 2FA verification fails
**Recommended Channels**: Email, SMS, Push
**Priority**: High

**Payload:**
```json
{
  "user_id": "uuid",
  "attempt_time": "2024-01-01T12:00:00Z",
  "method": "sms",
  "ip_address": "192.168.1.1",
  "failure_reason": "invalid_code",
  "attempt_count": 2,
  "remaining_attempts": 3
}
```

**Default Templates:**
- **Email**: 2FA failure alert
- **SMS**: Security warning
- **Push**: Failed verification alert

### `auth.2fa.method.changed`
**Description**: Sent when user changes 2FA method
**Recommended Channels**: Email, SMS, In-App
**Priority**: Medium

**Payload:**
```json
{
  "user_id": "uuid",
  "old_method": "sms",
  "new_method": "app",
  "changed_at": "2024-01-01T12:00:00Z",
  "ip_address": "192.168.1.1",
  "change_reason": "user_initiated"
}
```

**Default Templates:**
- **Email**: Security settings change confirmation
- **SMS**: 2FA method update notification
- **In-App**: Settings change alert

## Event Processing Flow

1. **Event Reception**: Events received via Kafka consumer
2. **Validation**: Event structure and tenant validation
3. **Template Resolution**: Find appropriate template for event type
4. **Channel Selection**: Determine best channels based on event type
5. **Content Rendering**: Apply context to templates
6. **Notification Dispatch**: Send via selected channels
7. **Logging**: Record delivery status and analytics

## Configuration

Events can be configured per tenant with:
- Custom templates
- Channel preferences
- Priority overrides
- Rate limiting rules
- User opt-out settings

## Implementation

### Event Handler Interface
```python
class EventHandler:
    def can_handle(self, event_type: str) -> bool:
        pass

    def get_default_channels(self, event_type: str) -> list:
        pass

    def get_template_data(self, event_payload: dict) -> dict:
        pass

    def process_event(self, event: dict) -> NotificationRecord:
        pass
```

### Registration
```python
# In apps.py or settings.py
EVENT_HANDLERS = {
    'user.registration.completed': UserRegistrationHandler(),
    'user.password.reset.requested': PasswordResetHandler(),
    # ... etc
}