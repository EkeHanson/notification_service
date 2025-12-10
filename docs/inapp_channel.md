# In-App Notification Channel Documentation

## Overview
The In-App Channel handles real-time notifications delivered through WebSockets using Django Channels. It broadcasts messages to connected users or tenant-wide groups, enabling instant alerts within web/mobile applications.

## Implementation Details

### Handler Class: `InAppHandler`
Located in `notifications/channels/inapp_handler.py`

```python
class InAppHandler(BaseHandler):
    async def send(self, recipient: str, content: dict, context: dict) -> dict:
        # Renders title/body with context
        # Broadcasts to WebSocket group using channel layer
```

### No External Credentials Required
Unlike other channels, in-app notifications use internal Redis-backed WebSocket groups. No `TenantCredentials` entry needed for this channel.

### Content Format
In-app content supports:

```json
{
  "title": "New Update",
  "body": "Your application status changed to {{status}}",
  "data": {
    "type": "status_update",
    "application_id": "{{app_id}}",
    "action_required": true
  }
}
```

### Context Injection
All string fields support placeholder replacement:

```json
{
  "status": "Approved",
  "app_id": "67890"
}
```

### Recipient Types
- **User-specific**: `recipient` = user ID (e.g., "123") → group `user_123_{tenant_id}`
- **Tenant-wide**: `recipient` = "all" → group `tenant_{tenant_id}`
- **Custom groups**: Future support for role-based groups

### WebSocket Integration
Uses Django Channels for real-time delivery:

```python
# Consumer example (in WebSocket consumer)
await self.channel_layer.group_add(
    f"user_{user_id}_{tenant_id}",
    self.channel_name
)

# Handler broadcasts to group
await channel_layer.group_send(
    group_name,
    {
        'type': 'inapp_notification',
        'title': title,
        'body': body,
        'data': data,
    }
)
```

### Message Structure
WebSocket clients receive:

```json
{
  "type": "inapp_notification",
  "title": "Welcome!",
  "body": "Your account is now active",
  "data": {
    "user_id": "123",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Error Handling
- **NETWORK_ERROR**: Redis/channel layer unavailable
- **CONTENT_ERROR**: Invalid message format
- **UNKNOWN_ERROR**: WebSocket broadcasting failures

### Dependencies
- Django Channels
- Redis (for channel layer backend)
- WebSocket consumers in client applications

### Usage Example
```python
handler = InAppHandler(tenant_id, {})  # No credentials needed
result = await handler.send(
    recipient="user_123",  # Or "all" for tenant broadcast
    content={
        "title": "Alert",
        "body": "New message from {{sender}}",
        "data": {"type": "message"}
    },
    context={"sender": "HR"}
)
```

### WebSocket URLs
```
# User-specific notifications
ws://localhost:3001/ws/notifications/{tenant_id}/?token={jwt_token}

# Tenant-wide broadcasts
ws://localhost:3001/ws/tenant/{tenant_id}/broadcast/
```

### Client Integration
Web applications must:

1. **Connect to WebSocket** with JWT authentication
2. **Handle different message types** (notifications, broadcasts, pings)
3. **Send heartbeat pings** to maintain connection
4. **Handle reconnections** gracefully
5. **Update UI** based on received notifications

### Authentication
```javascript
// Include JWT token in connection
const wsUrl = `ws://localhost:3001/ws/notifications/${tenantId}/?token=${jwtToken}`;
const socket = new WebSocket(wsUrl);
```

### Message Types Handled
- `connection_established` - Connection confirmation with queued message delivery
- `notification` - User-specific notifications (real-time or queued)
- `broadcast` - Tenant-wide announcements
- `pong` - Heartbeat responses
- `unread_count` - Notification count updates
- `mark_read` - Mark notification as read (delivery receipt)

### Connection Management
- Connections are tenant-isolated
- Automatic cleanup on disconnect
- Support for multiple concurrent connections per user

### Performance Considerations
- Redis pub/sub for scalable broadcasting
- Group-based messaging reduces individual sends
- No external API calls (fastest channel)

### Message Persistence for Offline Users ✅
In-app notifications now support persistence for offline users. Messages are stored in the database and delivered when users reconnect.

**Database Model:**
```python
class InAppMessage(models.Model):
    tenant_id = models.UUIDField()
    notification_record = models.OneToOneField(NotificationRecord)
    recipient = models.CharField()  # user_id or 'all'
    title = models.CharField()
    body = models.TextField()
    data = JSONField()
    status = models.CharField()  # pending, sent, delivered
    sent_at = models.DateTimeField(null=True)
    delivered_at = models.DateTimeField(null=True)
    read_at = models.DateTimeField(null=True)
    # ... additional fields
```

**Delivery Flow:**
1. Message saved to database with `pending` status
2. Attempt real-time delivery via WebSocket
3. If successful, status updated to `sent`
4. When user connects, queued messages are delivered and marked as `delivered`
5. Users can mark messages as `read` via WebSocket

**WebSocket Message Types:**
- `notification` - Real-time or queued notification
- `connection_established` - Connection confirmation with queued message delivery
- `mark_read` - Mark notification as read

### Future Enhancements
- Rich media support (images, links)
- User preferences (notification types to receive)
- Push fallback for disconnected users
- Message threading/conversations
- Message expiration and cleanup policies

## API Integration

### Send In-App Notification
**POST** `/api/notifications/records/`

**Request Body:**
```json
{
  "channel": "inapp",
  "recipient": "user_123",  // Or "all" for tenant broadcast
  "content": {
    "title": "New Update",
    "body": "Your application status changed to {{status}}",
    "data": {
      "type": "status_update",
      "application_id": "{{app_id}}",
      "action_required": true
    }
  },
  "context": {
    "status": "Approved",
    "app_id": "67890"
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

### Retrieve In-App Messages
**GET** `/api/notifications/inapp-messages/`

**Query Parameters:**
- `status` - Filter by status (pending, sent, delivered)
- `recipient` - Filter by recipient user ID
- `limit` - Number of messages to retrieve (default: 50)

**Response:**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "New Task Assigned",
      "body": "You have been assigned a new task",
      "data": {"task_id": "123"},
      "status": "delivered",
      "sent_at": "2024-01-01T12:00:00Z",
      "delivered_at": "2024-01-01T12:05:00Z",
      "read_at": "2024-01-01T12:10:00Z",
      "priority": "high"
    }
  ]
}
```

### Mark Message as Read
**POST** `/api/notifications/inapp-messages/{id}/mark-read/`

**Response:**
```json
{
  "success": true,
  "message": "Message marked as read"
}
```

## Frontend Integration (JavaScript/React)

### WebSocket Setup
```javascript
// Install dependencies
npm install @stomp/stompjs sockjs-client

import { Client } from '@stomp/stompjs';
import SockJS from 'sockjs-client';

class NotificationWebSocket {
  constructor() {
    this.client = null;
    this.isConnected = false;
  }

  connect(token) {
    const socket = new SockJS('/ws/notifications/');
    this.client = new Client({
      webSocketFactory: () => socket,
      connectHeaders: {
        'Authorization': `Bearer ${token}`
      },
      onConnect: () => {
        console.log('Connected to notification WebSocket');
        this.isConnected = true;

        // Subscribe to user-specific notifications
        this.client.subscribe('/user/queue/notifications', (message) => {
          const notification = JSON.parse(message.body);
          this.handleNotification(notification);
        });

        // Subscribe to tenant-wide notifications
        this.client.subscribe('/topic/tenant', (message) => {
          const notification = JSON.parse(message.body);
          this.handleNotification(notification);
        });
      },
      onDisconnect: () => {
        console.log('Disconnected from WebSocket');
        this.isConnected = false;
      },
      onStompError: (frame) => {
        console.error('STOMP error:', frame);
      }
    });

    this.client.activate();
  }

  disconnect() {
    if (this.client) {
      this.client.deactivate();
    }
  }

  handleNotification(notification) {
    console.log('Received notification:', notification);

    // Show in-app notification
    showToast(notification.title, notification.body);

    // Handle custom actions
    if (notification.data.action === 'redirect') {
      window.location.href = notification.data.url;
    }

    // Store in local notification history
    saveNotificationToHistory(notification);
  }
}

// Usage
const wsClient = new NotificationWebSocket();

// Connect when user logs in
wsClient.connect(localStorage.getItem('auth_token'));

// Disconnect on logout
wsClient.disconnect();
```

### Send In-App Notification from Frontend
```javascript
async function sendInAppNotification(recipient, title, body, customData = {}) {
  const response = await fetch('/api/notifications/records/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      channel: 'inapp',
      recipient: recipient,  // user_id or "all"
      content: {
        title: title,
        body: body,
        data: customData
      }
    })
  });

  return await response.json();
}

// Send to specific user
await sendInAppNotification(
  'user_123',
  'New Message',
  'You have a new message from HR',
  { action: 'open_messages', message_id: '123' }
);

// Send tenant-wide notification
await sendInAppNotification(
  'all',
  'System Maintenance',
  'Scheduled maintenance in 30 minutes',
  { type: 'maintenance', duration: '30min' }
);
```

### Complete React Integration Example
```javascript
import React, { useState, useEffect, useRef } from 'react';

function NotificationSystem({ tenantId, userToken }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    connectWebSocket();
    fetchNotificationHistory();

    return () => {
      disconnectWebSocket();
    };
  }, [tenantId, userToken]);

  const connectWebSocket = () => {
    try {
      const wsUrl = `ws://localhost:3001/ws/notifications/${tenantId}/?token=${userToken}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        startHeartbeat();
      };

      wsRef.current.onmessage = (event) => {
        handleWebSocketMessage(JSON.parse(event.data));
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code);
        setIsConnected(false);
        stopHeartbeat();
        scheduleReconnect();
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (error) {
      console.error('WebSocket connection error:', error);
      scheduleReconnect();
    }
  };

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    stopHeartbeat();
  };

  const scheduleReconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectTimeoutRef.current = setTimeout(() => {
      console.log('Attempting to reconnect WebSocket...');
      connectWebSocket();
    }, 5000); // Reconnect after 5 seconds
  };

  const startHeartbeat = () => {
    // Send ping every 30 seconds
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  };

  const stopHeartbeat = () => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
  };

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'connection_established':
        console.log('WebSocket connection confirmed');
        break;

      case 'notification':
        handleNewNotification(message);
        break;

      case 'broadcast':
        handleBroadcast(message);
        break;

      case 'unread_count':
        setUnreadCount(message.count);
        break;

      case 'pong':
        // Heartbeat response - connection is alive
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const handleNewNotification = (notification) => {
    // Add to notifications list
    setNotifications(prev => [notification, ...prev]);

    // Update unread count
    setUnreadCount(prev => prev + 1);

    // Show browser notification if permitted
    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.body,
        icon: '/notification-icon.png'
      });
    }

    // Handle custom actions
    if (notification.data?.action === 'redirect') {
      // Could redirect or open modal
      console.log('Redirect action:', notification.data.url);
    }
  };

  const handleBroadcast = (broadcast) => {
    // Handle tenant-wide broadcasts
    console.log('Tenant broadcast:', broadcast);
    // Could show global announcement
  };

  const fetchNotificationHistory = async () => {
    try {
      const response = await fetch('/api/notifications/records/?channel=inapp&limit=50', {
        headers: {
          'Authorization': `Bearer ${userToken}`
        }
      });

      const data = await response.json();
      setNotifications(data.results);

      // Calculate unread count
      const unread = data.results.filter(n => n.status !== 'read').length;
      setUnreadCount(unread);

    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      // Update local state
      setNotifications(prev =>
        prev.map(n =>
          n.id === notificationId ? { ...n, status: 'read' } : n
        )
      );

      setUnreadCount(prev => Math.max(0, prev - 1));

      // Send to WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'mark_read',
          notification_id: notificationId
        }));
      }

    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const requestUnreadCount = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'get_unread_count'
      }));
    }
  };

  return (
    <div className="notification-system">
      {/* Connection Status */}
      <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
        <span className="indicator"></span>
        {isConnected ? 'Real-time connected' : 'Real-time disconnected'}
      </div>

      {/* Notification Badge */}
      <div className="notification-badge" onClick={() => setShowHistory(!showHistory)}>
        <i className="bell-icon"></i>
        {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
      </div>

      {/* Notification History */}
      <div className="notification-history">
        {notifications.map(notification => (
          <div
            key={notification.id}
            className={`notification ${notification.status === 'read' ? 'read' : 'unread'}`}
            onClick={() => markAsRead(notification.id)}
          >
            <h4>{notification.title}</h4>
            <p>{notification.body}</p>
            <small>{new Date(notification.timestamp).toLocaleString()}</small>
            {notification.priority === 'high' && <span className="priority-high">!</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Message Payload Examples

#### User-Specific Notification
```json
{
  "type": "notification",
  "id": "uuid-123",
  "title": "Task Assigned",
  "body": "You have been assigned a new task: Review Q4 Report",
  "data": {
    "action": "redirect",
    "url": "/tasks/uuid-123",
    "priority": "high"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "priority": "high"
}
```

#### Tenant Broadcast
```json
{
  "type": "broadcast",
  "title": "System Maintenance",
  "body": "Scheduled maintenance in 30 minutes. Services may be unavailable.",
  "data": {
    "maintenance_start": "2024-01-01T12:30:00Z",
    "estimated_duration": "2 hours"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Connection Confirmation
```json
{
  "type": "connection_established",
  "message": "Connected to notification service",
  "user_id": "user-123",
  "tenant_id": "tenant-456",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Handling

#### Connection Errors
```javascript
wsRef.current.onerror = (error) => {
  console.error('WebSocket error:', error);
  setIsConnected(false);
  // Attempt to reconnect or show offline message
};
```

#### Message Parsing Errors
```javascript
try {
  const message = JSON.parse(event.data);
  handleWebSocketMessage(message);
} catch (error) {
  console.error('Failed to parse WebSocket message:', error);
}
```

### Performance Optimizations

#### Message Batching
- Group rapid notifications
- Debounce UI updates
- Use `requestAnimationFrame` for smooth animations

#### Memory Management
- Limit notification history size
- Clean up old notifications
- Use pagination for large lists

#### Network Efficiency
- Compress WebSocket messages
- Use binary protocols if needed
- Implement message queuing for offline users