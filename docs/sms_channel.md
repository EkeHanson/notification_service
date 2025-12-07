# SMS Channel Documentation

## Overview
The SMS Channel handles sending text message notifications using the Twilio API. It supports international SMS delivery with tenant-specific Twilio credentials and automatic carrier routing.

## Implementation Details

### Handler Class: `SMSHandler`
Located in `notifications/channels/sms_handler.py`

**Note**: Current implementation appears incomplete. Expected structure:

```python
from .base_handler import BaseHandler
from twilio.rest import Client
import logging

logger = logging.getLogger('notifications.channels.sms')

class SMSHandler(BaseHandler):
    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)
        self.client = Client(
            self.credentials['account_sid'],
            self.credentials['auth_token']
        )

    async def send(self, recipient: str, content: dict, context: dict) -> dict:
        try:
            # Render message with context
            message_body = content.get('body', '').format(**context)

            message = self.client.messages.create(
                body=message_body,
                from_=self.credentials['from_number'],
                to=recipient
            )

            return {
                'success': True,
                'response': {
                    'sid': message.sid,
                    'status': message.status
                }
            }

        except Exception as e:
            logger.error(f"SMS send error for tenant {self.tenant_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'response': None}
```

### Required Credentials
Stored in `TenantCredentials` model with channel='sms':

```json
{
  "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "auth_token": "encrypted_auth_token",
  "from_number": "+1234567890"
}
```

### Content Format
SMS content should include:

```json
{
  "body": "Hi {{user_name}}, your verification code is {{code}}"
}
```

**Limitations**: SMS messages are limited to 160 characters (GSM-7) or 70 characters (UCS-2).

### Context Injection
Placeholders are replaced with context values:

```json
{
  "user_name": "John Doe",
  "code": "123456"
}
```

### Error Handling
- **AUTH_ERROR**: Invalid Twilio credentials
- **NETWORK_ERROR**: API connection issues
- **PROVIDER_ERROR**: Twilio API errors (invalid number, insufficient balance)
- **CONTENT_ERROR**: Message too long or invalid format

### Dependencies
- `twilio` Python library
- Active Twilio account with SMS-enabled number
- Sufficient Twilio balance for SMS costs

### Usage Example
```python
handler = SMSHandler(tenant_id, credentials)
result = await handler.send(
    recipient="+1234567890",
    content={"body": "Hello {{name}}, code: {{otp}}"},
    context={"name": "Alice", "otp": "1234"}
)
```

### Cost Considerations
- SMS costs vary by destination country
- International SMS typically $0.01-$0.05 per message
- Monitor usage via Twilio dashboard

### SMS Analytics & Tracking

#### SMS Analytics Data
- **Delivery Status**: queued, sent, delivered, failed, undelivered
- **Cost Tracking**: Price per SMS, total segments, currency
- **Error Codes**: Twilio error codes and messages
- **Performance Metrics**: Delivery rates, failure reasons

#### Analytics API
**GET** `/api/notifications/sms-analytics/?status=delivered&created_at__date=2024-01-01`

### Testing & Utility APIs

#### Test SMS Sending
**POST** `/api/notifications/sms-test/`

**Request Body:**
```json
{
  "phone_number": "+1234567890",
  "message": "Test SMS from notification service"
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "status": "queued",
    "to": "+1234567890",
    "from": "+1234567890",
    "price": null,
    "price_unit": "USD"
  }
}
```

#### Check SMS Status
**GET** `/api/notifications/sms-status/{sid}/`

**Response:**
```json
{
  "success": true,
  "response": {
    "sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "status": "delivered",
    "to": "+1234567890",
    "from": "+1234567890",
    "date_sent": "2024-01-01T12:00:00Z",
    "date_delivered": "2024-01-01T12:00:30Z",
    "price": "0.0075",
    "error_code": null,
    "error_message": null
  }
}
```

#### Cost Estimation
**POST** `/api/notifications/sms-cost-estimate/`

**Request Body:**
```json
{
  "phone_numbers": ["+1234567890", "+1987654321"],
  "message": "Your verification code is: 123456"
}
```

**Response:**
```json
{
  "success": true,
  "estimation": {
    "recipients": 2,
    "message_length": 32,
    "segments_per_message": 1,
    "total_segments": 2,
    "estimated_cost_usd": 0.015,
    "cost_per_sms": 0.0075
  }
}
```

### Advanced Features

#### Phone Number Validation
```python
# Automatic E.164 formatting
handler = SMSHandler(tenant_id, credentials)
# "+1234567890" -> "+1234567890" (valid)
# "1234567890" -> "+11234567890" (US assumed)
# "123" -> ValueError (too short)
```

#### Bulk SMS Optimization
```python
# Efficient bulk sending
result = await sms_handler.send_bulk(
    recipients=["+1234567890", "+1987654321"],
    content={"body": "Hello {{name}}!"},
    context={"name": "User"}
)
```

#### Message Segmentation
- **GSM-7**: 160 characters per segment
- **UCS-2**: 70 characters per segment
- **Automatic splitting** for long messages
- **Cost calculation** based on segments

### Twilio Integration Details

#### Required Credentials
```json
{
  "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "auth_token": "encrypted_auth_token_here",
  "from_number": "+1234567890"
}
```

#### Supported Status Values
- `queued`: Message queued for sending
- `sent`: Message sent to carrier
- `delivered`: Message delivered to device
- `undelivered`: Message failed delivery
- `failed`: Permanent failure

### Error Handling

#### Common Twilio Errors
- **`21211`**: Invalid 'To' phone number
- **`21612`**: 'From' phone number not valid
- **`21614`**: 'To' number is not valid
- **`30001`**: Queue overflow
- **`30002`**: Account suspended

#### Automatic Retry Logic
```python
# Built-in retry for transient failures
# Exponential backoff: 60s * 2^retry_count
```

### Cost Management

#### Pricing Structure
- **Base Cost**: $0.0075 per SMS (US)
- **International**: Varies by country ($0.01-$0.05)
- **Segments**: Multiplied by message parts
- **Billing**: Per segment delivered

#### Cost Optimization
- **Concatenation**: Long messages split efficiently
- **Validation**: Prevent sending to invalid numbers
- **Estimation**: Pre-calculate costs before sending
- **Monitoring**: Track spending by tenant

### Security Considerations

#### Credential Protection
- Auth tokens encrypted at rest
- Access controlled by tenant isolation
- Secure API communication with Twilio

#### Content Validation
- Phone number format validation
- Message length limits enforced
- Template injection prevention

### Future Enhancements
- MMS support (media attachments)
- Two-way SMS (replies/inbound)
- Delivery status webhooks
- Unicode character optimization
- Advanced segmentation algorithms
- Bulk SMS campaign management
- SMS scheduling and automation

## API Integration

### Send SMS Notification
**POST** `/api/notifications/records/`

**Request Body:**
```json
{
  "channel": "sms",
  "recipient": "+1234567890",
  "content": {
    "body": "Your verification code is: {{code}}"
  },
  "context": {
    "code": "123456"
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

### Required Credentials Setup
**POST** `/api/notifications/credentials/`

```json
{
  "channel": "sms",
  "credentials": {
    "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "auth_token": "your_auth_token",
    "from_number": "+1234567890"
  }
}
```

## Frontend Integration (JavaScript/React)

### Send SMS from Frontend
```javascript
async function sendOTP(phoneNumber, otpCode) {
  const response = await fetch('/api/notifications/records/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      channel: 'sms',
      recipient: phoneNumber,
      content: {
        body: 'Your verification code is: {{code}}'
      },
      context: {
        code: otpCode
      }
    })
  });

  const result = await response.json();
  console.log('SMS queued:', result.id);
  return result;
}

// Usage
const result = await sendOTP('+1234567890', '123456');
```

### Check SMS Delivery Status
```javascript
async function checkSMSStatus(notificationId) {
  const response = await fetch(`/api/notifications/records/${notificationId}/`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    }
  });

  const notification = await response.json();
  return {
    status: notification.status,
    failure_reason: notification.failure_reason,
    sent_at: notification.sent_at
  };
}

// Poll for status (for critical SMS)
async function waitForSMSDelivery(notificationId, maxWaitMs = 30000) {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    const status = await checkSMSStatus(notificationId);

    if (status.status === 'success') {
      return { success: true, status };
    }

    if (status.status === 'failed') {
      return { success: false, status };
    }

    // Wait 2 seconds before checking again
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  return { success: false, error: 'Timeout waiting for delivery' };
}
```

### Handle SMS Responses in UI
```javascript
// SMS sending with user feedback
async function sendVerificationSMS(phoneNumber) {
  try {
    const result = await sendOTP(phoneNumber, generateOTP());

    // Show loading state
    showToast('Sending SMS...', 'info');

    // Wait for delivery confirmation
    const deliveryResult = await waitForSMSDelivery(result.id);

    if (deliveryResult.success) {
      showToast('SMS sent successfully!', 'success');
    } else {
      showToast('Failed to send SMS. Please try again.', 'error');
    }

  } catch (error) {
    console.error('SMS error:', error);
    showToast('Error sending SMS', 'error');
  }
}