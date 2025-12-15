
# Chat System – Backend-Verified Documentation

## Overview

The chat system provides real-time, multi-tenant messaging with support for direct, group, and channel conversations. It uses Django Channels and WebSockets for instant delivery, with robust models for conversations, participants, messages, reactions, and presence. All chat traffic is routed through the API Gateway for authentication and service isolation.

---

## Core Features

- **Real-time Messaging:** Instant delivery via WebSockets, with message history, read receipts, and typing indicators.
- **Conversation Types:** Direct (1:1), group, and channel (broadcast).
- **Rich Interactions:** Emoji reactions, file/image sharing, message editing/deletion, and presence indicators.
- **Security:** JWT authentication, tenant isolation, and role-based permissions.

---

## Architecture

### 1. **WebSocket Routing**

- **Frontend connects to:**  
  `ws://<gateway-host>:9090/ws/chat/{tenant_id}/?token={jwt}`
- **API Gateway:**  
  Proxies `/ws/chat/{tenant_id}/` to the notification service’s `/ws/chat/{tenant_id}/`.
- **Notification Service:**  
  Handles chat via `ChatConsumer`, which manages group membership and message broadcasting.

### 2. **Database Models**

- **ChatConversation:**  
  Stores conversation metadata (type, title, participants, etc.).
- **ChatParticipant:**  
  Tracks user membership, roles, and last seen per conversation.
- **ChatMessage:**  
  Stores messages, including type (text, emoji, file, image, system), content, and metadata.
- **MessageReaction:**  
  Tracks emoji reactions per message.
- **UserPresence:**  
  Tracks online/offline/away/busy status and current conversation.

### 3. **API Gateway & Service URLs**

- All WebSocket and REST API traffic is routed through the API Gateway.
- The gateway uses `MICROSERVICE_URLS` to map service names to internal URLs.
- The notification service is available at `http://notifications:3002` (Docker) or `localhost:3002` (local).

---

## WebSocket API

### **Connection**

- **URL:**  
  `ws://localhost:9090/ws/chat/{tenant_id}/?token={jwt}`
- **Authentication:**  
  JWT token is required as a query parameter (`?token=...`).

### **Client → Server Messages**

- **Join Conversation:**  
  ```json
  { "type": "join_conversation", "conversation_id": "uuid" }
  ```
- **Send Message:**  
  ```json
  { "type": "send_message", "conversation_id": "uuid", "content": "Hello", "message_type": "text" }
  ```
- **Start/Stop Typing:**  
  ```json
  { "type": "start_typing", "conversation_id": "uuid" }
  { "type": "stop_typing", "conversation_id": "uuid" }
  ```
- **Add/Remove Reaction:**  
  ```json
  { "type": "add_reaction", "message_id": "uuid", "emoji": "👍" }
  { "type": "remove_reaction", "message_id": "uuid", "emoji": "👍" }
  ```
- **Mark as Read:**  
  ```json
  { "type": "mark_read", "conversation_id": "uuid" }
  ```
- **Update Presence:**  
  ```json
  { "type": "update_presence", "status": "away" }
  ```

### **Server → Client Messages**

- **Connection Established:**  
  ```json
  { "type": "connection_established", "message": "Connected to chat service", "user_id": "uuid", "tenant_id": "uuid", "timestamp": "..." }
  ```
- **New Message:**  
  ```json
  { "type": "new_message", "message": { ... } }
  ```
- **Message Updated/Deleted:**  
  ```json
  { "type": "message_updated", "message": { ... } }
  { "type": "message_deleted", "message_id": "uuid" }
  ```
- **Reaction Added/Removed:**  
  ```json
  { "type": "reaction_added", "reaction": { ... } }
  { "type": "reaction_removed", "message_id": "uuid", "user_id": "uuid", "emoji": "👍" }
  ```
- **Typing Indicator:**  
  ```json
  { "type": "typing_indicator", "user_id": "uuid", "is_typing": true }
  ```

---

## REST API Endpoints

- **Conversations:**  
  - `GET/POST /api/notifications/chat/conversations/`
  - `GET/PUT/DELETE /api/notifications/chat/conversations/{id}/`
- **Participants:**  
  - `GET/POST /api/notifications/chat/conversations/{conversation_id}/participants/`
- **Messages:**  
  - `GET/POST /api/notifications/chat/conversations/{conversation_id}/messages/`
  - `GET/PUT/DELETE /api/notifications/chat/conversations/{conversation_id}/messages/{id}/`
- **Reactions:**  
  - `GET/POST /api/notifications/chat/messages/{message_id}/reactions/`
- **Presence:**  
  - `GET /api/notifications/chat/presence/`
  - `GET/PUT /api/notifications/chat/presence/me/`
- **File Upload:**  
  - `POST /api/notifications/chat/upload/` (multipart form)

---

## Backend Flow

1. **User connects via WebSocket** (through API Gateway) and authenticates with JWT.
2. **User sends `join_conversation`** to join a chat group.
3. **Messages sent with `send_message`** are broadcast to all group members.
4. **Typing, reactions, and presence** are handled in real time via group events.
5. **All events are tenant-isolated** and permission-checked.

---

## Troubleshooting

- **If users do not receive messages:**  
  - Ensure frontend connects to `/ws/chat/{tenant_id}/`, not `/ws/notifications/{tenant_id}/`.
  - Confirm both sender and recipient join the same conversation group.
  - Check JWT token validity and tenant/user IDs.
  - Review backend logs for group join and message broadcast events.

- **API Gateway:**  
  - Proxies all `/ws/chat/...` traffic to the notification service.
  - Uses `MICROSERVICE_URLS` for service discovery.

- **Docker:**  
  - Both services must be on the same Docker network.
  - Ports: 9090 (gateway), 3002 (notification service).

---

## Example React Integration

```js
const ws = new WebSocket(`ws://localhost:9090/ws/chat/${tenantId}/?token=${jwt}`);
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join_conversation', conversation_id }));
};
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // handle data.type: new_message, typing_indicator, etc.
};
```

---

## Security

- **JWT authentication** for all WebSocket and REST API calls.
- **Tenant isolation** and role-based permissions enforced in backend.
- **Rate limiting** and content validation for spam and abuse prevention.

---

## Summary

- **Connect to `/ws/chat/{tenant_id}/` for chat.**
- **All chat is routed through the API Gateway.**
- **Backend uses Django Channels, group-based routing, and robust models.**
- **REST API and WebSocket API are both available for full-featured chat.**

This documentation is fully aligned with your backend code and deployment. For any integration, always use the `/ws/chat/{tenant_id}/` path for chat, and ensure JWT authentication is provided.

Let me know if you need a frontend code sample, troubleshooting help, or further customization!