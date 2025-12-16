# Email Channel Documentation

## Overview
The Email Channel handles sending email notifications through SMTP using tenant-specific credentials. It supports HTML and plain text emails with template rendering and context injection.

## Implementation Details


### Handler Class: `EmailHandler`
Located in `notifications/channels/email_handler.py`

```python
class EmailHandler(BaseHandler):
  def send_async(self, recipient: str, content: dict, context: dict, record_id: str = None) -> dict:
    """
    Dispatches an email send task asynchronously using Celery.
    Returns immediately after queuing the task.
    """
```

#### Usage
To send an email asynchronously:

```python
handler = EmailHandler(tenant_id, credentials)
handler.send_async(recipient, content, context)
```

This will queue the email to be sent in the background by Celery workers, improving response time and throughput.

### Required Credentials
Stored in `TenantCredentials` model with channel='email':

```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "tenant@example.com",
  "password": "encrypted_password",
  "from_email": "noreply@tenant.com",
  "use_tls": true
}
```

### Content Format
Email content should include:

```json
{
  "subject": "Welcome {{user_name}}!",
  "body": "Hello {{user_name}}, your account is ready."
}
```

### Context Injection
Placeholders like `{{user_name}}` are replaced with values from the context dict:

```json
{
  "user_name": "John Doe",
  "company": "Acme Corp"
}
```

### Error Handling
- **AUTH_ERROR**: Invalid SMTP credentials
- **NETWORK_ERROR**: Connection issues with SMTP server
- **CONTENT_ERROR**: Invalid email format or missing required fields

### Dependencies
- Django's `send_mail` function
- Tenant SMTP credentials (encrypted at rest)

### Usage Example
```python
handler = EmailHandler(tenant_id, credentials)
result = await handler.send(
    recipient="user@example.com",
    content={"subject": "Hi {{name}}", "body": "Welcome!"},
    context={"name": "Alice"}
)
```

### Limitations
- Currently uses synchronous `send_mail` (consider async SMTP library for high volume)
- No attachment support yet
- Basic template rendering (string format only)

### Future Enhancements
- HTML template support with CSS inlining
- Attachment handling
- DKIM/SPF validation
- Bounce handling and unsubscribe links

## API Integration

### Send Email Notification
**POST** `/api/notifications/records/`

**Request Body:**
```json
{
  "channel": "email",
  "recipient": "user@example.com",
  "content": {
    "subject": "Welcome {{name}}!",
    "body": "Hello {{name}}, welcome to our platform!"
  },
  "context": {
    "name": "John Doe"
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "pending"
}
```

### Using Templates
```json
{
  "channel": "email",
  "recipient": "user@example.com",
  "template_id": "uuid",
  "context": {
    "name": "John Doe",
    "company": "Acme Corp"
  }
}
```

## Frontend Integration (JavaScript/React)

### Send Email from Frontend
```javascript
async function sendWelcomeEmail(userEmail, userName) {
  const response = await fetch('/api/notifications/records/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      channel: 'email',
      recipient: userEmail,
      content: {
        subject: 'Welcome to our platform!',
        body: 'Hello {{name}}, welcome!'
      },
      context: {
        name: userName
      }
    })
  });

  const result = await response.json();
  console.log('Email queued:', result.id);
}
```

### Template Usage
```javascript
async function sendUsingTemplate(templateId, recipient, context) {
  const response = await fetch('/api/notifications/records/', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
      channel: 'email',
      recipient: recipient,
      template_id: templateId,
      context: context
    })
  });

  return await response.json();
}
```

### Check Delivery Status
```javascript
async function checkEmailStatus(notificationId) {
  const response = await fetch(`/api/notifications/records/${notificationId}/`, {
    headers: headers
  });

  const notification = await response.json();
  return {
    status: notification.status,
    failure_reason: notification.failure_reason,
    sent_at: notification.sent_at
  };
}
```