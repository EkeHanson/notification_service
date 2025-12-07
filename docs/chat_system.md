# Chat System Documentation

## Overview

The Chat System provides real-time messaging functionality with support for text messages, emojis, file sharing, and threaded conversations. It includes WebSocket-based real-time communication, message history, reactions, and presence indicators.

## Core Features

### 🎯 **Real-time Messaging**
- Instant message delivery via WebSockets
- Message history and pagination
- Read receipts and typing indicators
- Online/offline presence status

### 💬 **Message Types**
- **Text**: Plain text messages
- **Emoji**: Unicode emoji support
- **File**: Document and image sharing
- **Image**: Optimized image display
- **System**: Automated status messages

### 👥 **Conversation Types**
- **Direct**: One-on-one private messaging
- **Group**: Multi-user group chats
- **Channel**: Broadcast-style channels

### 🎨 **Rich Interactions**
- Emoji reactions to messages
- Message threading (replies)
- File attachments with previews
- Message editing and deletion
- @mentions and notifications

## Architecture

### Database Models

#### ChatConversation
```python
{
  "id": "uuid",
  "tenant_id": "uuid",
  "title": "Project Discussion",
  "conversation_type": "group|direct|channel",
  "created_by": "uuid",
  "is_active": true,
  "last_message_at": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T10:00:00Z"
}
```

#### ChatParticipant
```python
{
  "id": "uuid",
  "conversation": "uuid",
  "user_id": "uuid",
  "role": "admin|moderator|member",
  "joined_at": "2024-01-01T10:00:00Z",
  "last_seen_at": "2024-01-01T12:00:00Z",
  "is_active": true
}
```

#### ChatMessage
```python
{
  "id": "uuid",
  "conversation": "uuid",
  "sender_id": "uuid",
  "message_type": "text|emoji|file|image|system",
  "content": "Hello world!",
  "file_url": "/media/chat-files/...",
  "file_name": "document.pdf",
  "file_size": 1024000,
  "reply_to": "uuid",  // Optional
  "edited_at": "2024-01-01T12:05:00Z",
  "is_deleted": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### MessageReaction
```python
{
  "id": "uuid",
  "message": "uuid",
  "user_id": "uuid",
  "emoji": "👍",
  "created_at": "2024-01-01T12:01:00Z"
}
```

#### UserPresence
```python
{
  "id": "uuid",
  "user_id": "uuid",
  "status": "online|away|busy|offline",
  "last_seen": "2024-01-01T12:00:00Z",
  "current_conversation": "uuid"
}
```

## API Endpoints

### Conversations

#### List/Create Conversations
```
GET/POST /api/notifications/chat/conversations/
```

**Create Request:**
```json
{
  "title": "Project Team Chat",
  "conversation_type": "group"
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Project Team Chat",
  "conversation_type": "group",
  "participant_count": 1,
  "last_message": null,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### Get/Update/Delete Conversation
```
GET/PUT/DELETE /api/notifications/chat/conversations/{id}/
```

### Participants

#### List/Add Participants
```
GET/POST /api/notifications/chat/conversations/{conversation_id}/participants/
```

**Add Participant:**
```json
{
  "user_id": "uuid",
  "role": "member"
}
```

### Messages

#### List/Send Messages
```
GET/POST /api/notifications/chat/conversations/{conversation_id}/messages/
```

**Send Message:**
```json
{
  "message_type": "text",
  "content": "Hello everyone! 👋",
  "reply_to": "uuid"  // Optional
}
```

**Send File:**
```json
{
  "message_type": "file",
  "content": "Check out this document",
  "file_url": "/media/chat-files/doc.pdf",
  "file_name": "project_plan.pdf",
  "file_size": 2048000
}
```

**Response:**
```json
{
  "id": "uuid",
  "sender_id": "uuid",
  "message_type": "text",
  "content": "Hello everyone! 👋",
  "reactions": [],
  "reply_count": 0,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### Get/Update/Delete Message
```
GET/PUT/DELETE /api/notifications/chat/conversations/{conversation_id}/messages/{id}/
```

### Reactions

#### List/Add Reactions
```
GET/POST /api/notifications/chat/messages/{message_id}/reactions/
```

**Add Reaction:**
```json
{
  "emoji": "👍"
}
```

### Presence

#### List User Presence
```
GET /api/notifications/chat/presence/
```

#### Update My Presence
```
GET/PUT /api/notifications/chat/presence/me/
```

**Update Presence:**
```json
{
  "status": "busy",
  "current_conversation": "uuid"
}
```

### File Upload

#### Upload File
```
POST /api/notifications/chat/upload/
```

**Multipart Form Data:**
- `file`: File to upload

**Response:**
```json
{
  "file_url": "/media/chat-files/tenant_123/document.pdf",
  "file_name": "document.pdf",
  "file_size": 2048000,
  "content_type": "application/pdf"
}
```

## WebSocket API

### Connection
```
WebSocket: ws://localhost:3001/ws/chat/{tenant_id}/
```

### Authentication
JWT token required in connection headers or initial message.

### Message Format
All WebSocket messages use JSON format:

```json
{
  "type": "message_type",
  "data": {...}
}
```

### Client → Server Messages

#### Join Conversation
```json
{
  "type": "join_conversation",
  "conversation_id": "uuid"
}
```

#### Send Message
```json
{
  "type": "send_message",
  "conversation_id": "uuid",
  "content": "Hello world!",
  "message_type": "text"
}
```

#### Start/Stop Typing
```json
{
  "type": "start_typing",
  "conversation_id": "uuid"
}
```

```json
{
  "type": "stop_typing",
  "conversation_id": "uuid"
}
```

#### Add/Remove Reaction
```json
{
  "type": "add_reaction",
  "message_id": "uuid",
  "emoji": "👍"
}
```

```json
{
  "type": "remove_reaction",
  "message_id": "uuid",
  "emoji": "👍"
}
```

#### Mark as Read
```json
{
  "type": "mark_read",
  "conversation_id": "uuid"
}
```

#### Update Presence
```json
{
  "type": "update_presence",
  "status": "away"
}
```

### Server → Client Messages

#### Connection Established
```json
{
  "type": "connection_established",
  "message": "Connected to chat service",
  "user_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### New Message
```json
{
  "type": "new_message",
  "message": {
    "id": "uuid",
    "sender_id": "uuid",
    "content": "Hello!",
    "message_type": "text",
    "created_at": "2024-01-01T12:00:00Z",
    "reactions": []
  }
}
```

#### Message Updated
```json
{
  "type": "message_updated",
  "message": {
    "id": "uuid",
    "content": "Hello world!",
    "edited_at": "2024-01-01T12:05:00Z"
  }
}
```

#### Message Deleted
```json
{
  "type": "message_deleted",
  "message_id": "uuid"
}
```

#### Reaction Added/Removed
```json
{
  "type": "reaction_added",
  "reaction": {
    "message_id": "uuid",
    "user_id": "uuid",
    "emoji": "👍",
    "created_at": "2024-01-01T12:01:00Z"
  }
}
```

#### Typing Indicator
```json
{
  "type": "typing_indicator",
  "user_id": "uuid",
  "is_typing": true
}
```

## Frontend Integration

### React Chat Component Example

```javascript
import React, { useState, useEffect, useRef } from 'react';

function ChatRoom({ conversationId }) {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [socket, setSocket] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket(`ws://localhost:3001/ws/chat/${tenantId}/`);
    ws.onopen = () => {
      // Join conversation
      ws.send(JSON.stringify({
        type: 'join_conversation',
        conversation_id: conversationId
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    setSocket(ws);
    return () => ws.close();
  }, [conversationId]);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'new_message':
        setMessages(prev => [...prev, data.message]);
        break;
      case 'typing_indicator':
        setIsTyping(data.is_typing);
        break;
      // Handle other message types...
    }
  };

  const sendMessage = () => {
    if (!newMessage.trim()) return;

    socket.send(JSON.stringify({
      type: 'send_message',
      conversation_id: conversationId,
      content: newMessage,
      message_type: 'text'
    }));

    setNewMessage('');
  };

  const handleTyping = (e) => {
    setNewMessage(e.target.value);

    // Send typing indicators
    if (e.target.value && !isTyping) {
      socket.send(JSON.stringify({
        type: 'start_typing',
        conversation_id: conversationId
      }));
    } else if (!e.target.value && isTyping) {
      socket.send(JSON.stringify({
        type: 'stop_typing',
        conversation_id: conversationId
      }));
    }
  };

  return (
    <div className="chat-room">
      <div className="messages">
        {messages.map(message => (
          <div key={message.id} className="message">
            <strong>{message.sender_id}:</strong> {message.content}
            {message.reactions.length > 0 && (
              <div className="reactions">
                {message.reactions.map((reaction, index) => (
                  <span key={index}>{reaction.emoji}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {isTyping && <div className="typing">Someone is typing...</div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="message-input">
        <input
          type="text"
          value={newMessage}
          onChange={handleTyping}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
```

### File Upload Example

```javascript
const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/notifications/chat/upload/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    },
    body: formData
  });

  const result = await response.json();

  // Send file message
  socket.send(JSON.stringify({
    type: 'send_message',
    conversation_id: conversationId,
    content: `Shared a file: ${result.file_name}`,
    message_type: 'file',
    file_url: result.file_url,
    file_name: result.file_name,
    file_size: result.file_size
  }));
};
```

## Security Features

### Authentication
- JWT token validation for WebSocket connections
- User identity verification for all operations
- Tenant isolation enforcement

### Authorization
- Conversation membership validation
- Message ownership checks for edits/deletes
- Role-based permissions (admin/moderator/member)

### Content Validation
- File type and size restrictions
- Message content sanitization
- Rate limiting for spam prevention

## Performance Optimizations

### Database Indexing
- Composite indexes on frequently queried fields
- Optimized queries with select_related/prefetch_related
- Efficient pagination for message history

### WebSocket Scaling
- Redis-backed channel layers for horizontal scaling
- Connection pooling and load balancing
- Message broadcasting optimization

### Caching
- User presence caching
- Conversation metadata caching
- File URL caching

## Monitoring & Analytics

### Message Metrics
- Messages sent per conversation/user
- File upload statistics
- Real-time connection counts

### Performance Monitoring
- WebSocket connection latency
- Message delivery times
- Database query performance

### User Engagement
- Active conversation tracking
- User participation metrics
- Feature usage analytics

## Future Enhancements

### Advanced Features
- **Voice Messages**: Audio recording and playback
- **Video Calls**: WebRTC integration
- **Screen Sharing**: Real-time collaboration
- **Message Encryption**: End-to-end security
- **Offline Support**: Service worker caching

### AI Integration
- **Smart Replies**: AI-generated response suggestions
- **Content Moderation**: Automated inappropriate content detection
- **Translation**: Real-time message translation
- **Sentiment Analysis**: Message tone detection

### Advanced Chat Features
- **Threaded Conversations**: Nested reply chains
- **Polls and Surveys**: Interactive content
- **Calendar Integration**: Meeting scheduling
- **Task Management**: Action item tracking

This chat system provides a solid foundation for real-time communication with room for extensive customization and feature expansion.