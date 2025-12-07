# Push Notification Channel Documentation

## Overview
The Push Channel handles sending mobile and web push notifications using Firebase Cloud Messaging (FCM). It supports both Android and iOS devices with rich notifications, custom data payloads, and topic-based messaging.

## Implementation Details

### Handler Class: `PushHandler`
Located in `notifications/channels/push_handler.py`

```python
class PushHandler(BaseHandler):
    def __init__(self, tenant_id: str, credentials: dict):
        super().__init__(tenant_id, credentials)
        # Decrypts sensitive Firebase credentials
        # Initializes Firebase app per tenant

    async def send(self, recipient: str, content: dict, context: dict) -> dict:
        # Renders title/body with context
        # Sends FCM message to device token
```

### Required Credentials
Stored in `TenantCredentials` model with channel='push':

```json
{
  "type": "service_account",
  "project_id": "tenant-fcm-project",
  "private_key_id": "key_id",
  "private_key": "encrypted_private_key",
  "client_email": "firebase-adminsdk@tenant.iam.gserviceaccount.com",
  "client_id": "client_id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

This is the standard Firebase service account JSON, with `private_key` encrypted.

### Content Format
Push content supports:

```json
{
  "title": "New Message from {{sender}}",
  "body": "You have a new notification",
  "data": {
    "type": "message",
    "id": "{{message_id}}",
    "action_url": "app://messages/{{message_id}}"
  }
}
```

### Context Injection
Placeholders in title, body, and data are replaced:

```json
{
  "sender": "HR Team",
  "message_id": "12345"
}
```

### Recipient Types
- **Device Token**: Individual device FCM token (e.g., from mobile app registration)
- **Topic**: Broadcast to all devices subscribed to a topic (future enhancement)

### Error Handling
- **AUTH_ERROR**: Invalid Firebase credentials
- **NETWORK_ERROR**: FCM API connection issues
- **PROVIDER_ERROR**: FCM errors (invalid token, quota exceeded)
- **CONTENT_ERROR**: Invalid message format

### Dependencies
- `firebase-admin` Python library
- Firebase project with FCM enabled
- Device tokens obtained from mobile/web apps

### Usage Example
```python
handler = PushHandler(tenant_id, credentials)
result = await handler.send(
    recipient="device_fcm_token_here",
    content={
        "title": "Welcome {{name}}!",
        "body": "Your account is ready",
        "data": {"user_id": "{{user_id}}"}
    },
    context={"name": "Alice", "user_id": "123"}
)
```

### Firebase App Management
- Each tenant gets a separate Firebase app instance
- Prevents credential conflicts between tenants
- Apps are initialized on handler creation

### Security Notes
- Private keys are encrypted at rest using AES-256
- Decrypted only in memory during message sending
- Firebase credentials grant admin access - store securely

### Device Token Management

#### Register Device Token
**POST** `/api/notifications/devices/`

**Request Body:**
```json
{
  "device_type": "android|ios|web",
  "device_token": "fcm_token_here",
  "device_id": "unique_device_id",
  "app_version": "1.0.0",
  "os_version": "14.0",
  "language": "en",
  "timezone": "America/New_York"
}
```

**Response:**
```json
{
  "id": "uuid",
  "device_type": "android",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### List Device Tokens
**GET** `/api/notifications/devices/`

#### Update Device Token
**PUT** `/api/notifications/devices/{id}/`

#### Test Push Notification
**POST** `/api/notifications/push-test/`

**Request Body:**
```json
{
  "device_token": "fcm_token_here",
  "title": "Test Notification",
  "body": "This is a test push notification"
}
```

### Platform-Specific Features

#### Android Configuration
```python
android_config = messaging.AndroidConfig(
    priority=messaging.AndroidConfig.Priority.HIGH,
    notification=messaging.AndroidNotification(
        icon='ic_notification',
        color='#FF0000',
        sound='default',
        click_action='OPEN_ACTIVITY'
    )
)
```

#### iOS Configuration
```python
apns_config = messaging.APNSConfig(
    payload=messaging.APNSPayload(
        aps=messaging.Aps(
            alert=messaging.ApsAlert(title="Title", body="Body"),
            badge=1,
            sound='default',
            thread_id='notification-thread'
        )
    )
)
```

#### Web Push Configuration
```python
webpush_config = messaging.WebpushConfig(
    notification=messaging.WebpushNotification(
        icon='/icon.png',
        badge='/badge.png',
        image='/hero-image.png'
    )
)
```

### Bulk Push Notifications

#### Send to Multiple Devices
```python
# Handler automatically handles bulk sending
result = await push_handler.send_bulk(
    recipients=["token1", "token2", "token3"],
    content={
        "title": "Bulk Announcement",
        "body": "Important update for all users"
    },
    context={}
)
```

### Topic-Based Messaging

#### Subscribe to Topic
```python
result = await push_handler.subscribe_to_topic(
    tokens=["token1", "token2"],
    topic="announcements"
)
```

#### Send to Topic
```python
result = await push_handler.send(
    recipient="topic_announcements",
    content={
        "title": "System Update",
        "body": "New features available"
    },
    context={}
)
```

### Analytics & Tracking

#### Push Analytics Data
- **Delivery Status**: sent, delivered, opened, failed
- **Platform Metrics**: Android, iOS, Web breakdown
- **Error Tracking**: FCM error codes and messages
- **Engagement Rates**: Open rates, click-through rates

#### Analytics API
**GET** `/api/notifications/push-analytics/?status=delivered&platform=android`

### Error Handling

#### Common FCM Errors
- **`INVALID_ARGUMENT`**: Malformed request
- **`UNREGISTERED`**: Token expired or invalid
- **`SENDER_ID_MISMATCH`**: Wrong Firebase project
- **`QUOTA_EXCEEDED`**: Rate limit exceeded

#### Automatic Retry Logic
```python
# Handler includes automatic retries for transient errors
# with exponential backoff
```

### Security Considerations

#### Token Encryption
- FCM tokens stored encrypted in database
- Access controlled by tenant and user isolation
- Token validation before sending

#### Rate Limiting
- Per-tenant rate limits
- Burst protection
- Fair usage policies

### Future Enhancements
- **Rich Media**: Images, videos, carousels
- **Interactive Notifications**: Action buttons, quick replies
- **Geofencing**: Location-based notifications
- **A/B Testing**: Content optimization
- **Scheduled Delivery**: Time-zone aware scheduling
- **User Preferences**: Granular opt-in/opt-out controls

## API Integration

### Send Push Notification
**POST** `/api/notifications/records/`

**Request Body:**
```json
{
  "channel": "push",
  "recipient": "fcm_device_token_here",
  "content": {
    "title": "New Message from {{sender}}",
    "body": "You have a new notification",
    "data": {
      "type": "message",
      "id": "{{message_id}}",
      "action_url": "app://messages/{{message_id}}"
    }
  },
  "context": {
    "sender": "HR Team",
    "message_id": "12345"
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

### Bulk Push Campaign
**POST** `/api/notifications/campaigns/`

```json
{
  "name": "Product Update Campaign",
  "channel": "push",
  "content": {
    "title": "New Feature Available!",
    "body": "Check out our latest update",
    "data": {"action": "open_app", "version": "2.0"}
  },
  "recipients": [
    {
      "recipient": "fcm_token_1",
      "context": {"user_name": "Alice"}
    },
    {
      "recipient": "fcm_token_2",
      "context": {"user_name": "Bob"}
    }
  ]
}
```

## Frontend Integration (JavaScript/React)

### Firebase Setup
```javascript
// Install dependencies
npm install firebase

// Initialize Firebase
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  messagingSenderId: "123456789",
  appId: "your-app-id"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);
```

### Request Notification Permission
```javascript
async function requestNotificationPermission() {
  try {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      const token = await getToken(messaging, {
        vapidKey: 'your-vapid-key'
      });
      console.log('FCM Token:', token);

      // Send token to backend
      await registerDeviceToken(token);
      return token;
    }
  } catch (error) {
    console.error('Error getting FCM token:', error);
  }
}
```

### Register Device Token
```javascript
async function registerDeviceToken(fcmToken) {
  // This typically happens during user registration
  // Store token in user profile for push notifications
  const response = await fetch('/api/user/device-token/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ fcm_token: fcmToken })
  });

  return await response.json();
}
```

### Handle Foreground Messages
```javascript
// Handle messages when app is in foreground
onMessage(messaging, (payload) => {
  console.log('Message received:', payload);

  // Show browser notification
  new Notification(payload.notification.title, {
    body: payload.notification.body,
    icon: '/icon.png'
  });

  // Handle custom data
  if (payload.data.action === 'open_app') {
    window.focus();
  }

  // Update UI
  updateNotificationBadge();
});
```

### Send Push Notification from Frontend
```javascript
async function sendPushNotification(recipientToken, title, body, customData = {}) {
  const response = await fetch('/api/notifications/records/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      channel: 'push',
      recipient: recipientToken,
      content: {
        title: title,
        body: body,
        data: customData
      }
    })
  });

  return await response.json();
}

// Example usage
await sendPushNotification(
  'fcm_token_here',
  'New Message',
  'You have a new message from HR',
  { action: 'open_messages', message_id: '123' }
);
```

### Service Worker for Background Messages
```javascript
// public/firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

const firebaseConfig = {
  // Same config as main app
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
  console.log('Received background message:', payload);

  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/icon.png',
    data: payload.data
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.notification.data.action === 'open_messages') {
    clients.openWindow('/messages');
  }
});
```