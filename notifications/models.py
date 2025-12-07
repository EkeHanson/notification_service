from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from enum import Enum
import uuid
import json
from django.db.models import JSONField
import logging

logger = logging.getLogger('notifications')

class ChannelType(Enum):
    EMAIL = 'email'
    SMS = 'sms'
    PUSH = 'push'
    INAPP = 'inapp'

class NotificationStatus(Enum):
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'

class FailureReason(Enum):
    AUTH_ERROR = 'auth_error'
    NETWORK_ERROR = 'network_error'
    PROVIDER_ERROR = 'provider_error'
    CONTENT_ERROR = 'content_error'
    UNKNOWN_ERROR = 'unknown_error'

class SoftDeleteQuerySet(models.query.QuerySet):
    def delete(self):
        self.update(is_deleted=True, deleted_at=timezone.now())

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def deleted_set(self):
        return super().get_queryset().filter(is_deleted=True)

def validate_template_content(value):
    if not isinstance(value, dict):
        raise ValidationError("Template content must be a dictionary with 'subject' or 'body'.")
    return value

class TenantCredentials(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in ChannelType])
    credentials = JSONField()  # e.g., {'smtp_host': '...', 'username': '...'} - encrypted separately
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        unique_together = [('tenant_id', 'channel')]
        indexes = [models.Index(fields=['tenant_id', 'channel'])]

class NotificationTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    channel = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in ChannelType])
    content = JSONField(validators=[validate_template_content])  # e.g., {'subject': 'Hi {{name}}', 'body': '...'}
    placeholders = JSONField(default=list)  # e.g., ['{{candidate_name}}', '{{interview_date}}']
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [models.Index(fields=['tenant_id', 'name', 'channel'])]

class NotificationRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in ChannelType])
    recipient = models.CharField(max_length=500)  # email, phone, token, etc.
    template_id = models.UUIDField(null=True, blank=True)  # Optional template
    context = JSONField(default=dict)  # Placeholders: {'candidate_name': 'John'}
    status = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in NotificationStatus], default=NotificationStatus.PENDING.value)
    failure_reason = models.CharField(max_length=20, choices=[(tag.value, tag.name) for tag in FailureReason], blank=True, null=True)
    provider_response = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['status', 'retry_count']),
        ]

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    notification_id = models.UUIDField()  # FK to NotificationRecord
    event = models.CharField(max_length=100)  # e.g., 'sent', 'failed', 'retry'
    details = JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_id = models.UUIDField(null=True, blank=True)  # Who triggered

    class Meta:
        indexes = [models.Index(fields=['tenant_id', 'timestamp'])]
        ordering = ['-timestamp']



class CampaignStatus(Enum):
    DRAFT = 'draft'
    SCHEDULED = 'scheduled'
    SENDING = 'sending'
    COMPLETED = 'completed'
    FAILED = 'failed'

class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    channel = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in ChannelType])
    template_id = models.UUIDField(null=True, blank=True)  # Or inline content
    content = JSONField(validators=[validate_template_content], null=True, blank=True)
    recipients = JSONField(default=list)  # List of {'recipient': '...', 'context': {...}}
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in CampaignStatus], default=CampaignStatus.DRAFT.value)
    schedule_time = models.DateTimeField(null=True, blank=True)  # For beat scheduling
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [models.Index(fields=['tenant_id', 'status'])]


class DeviceType(Enum):
    ANDROID = 'android'
    IOS = 'ios'
    WEB = 'web'

class DeviceToken(models.Model):
    """Store device tokens for push notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    device_type = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in DeviceType])
    device_token = models.CharField(max_length=500, unique=True)  # FCM token
    device_id = models.CharField(max_length=255, blank=True)  # Optional device identifier
    app_version = models.CharField(max_length=50, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        unique_together = [('user_id', 'device_id')]  # One device per user
        indexes = [
            models.Index(fields=['tenant_id', 'user_id']),
            models.Index(fields=['device_token']),
            models.Index(fields=['is_active', 'last_used']),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.device_type} - {self.device_token[:20]}..."


class PushNotificationStatus(Enum):
    SENT = 'sent'
    DELIVERED = 'delivered'
    OPENED = 'opened'
    FAILED = 'failed'

class PushAnalytics(models.Model):
    """Track push notification delivery and engagement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    notification_id = models.UUIDField()  # FK to NotificationRecord
    device_token_id = models.UUIDField()  # FK to DeviceToken
    fcm_message_id = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in PushNotificationStatus])
    platform = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in DeviceType])
    error_message = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'notification_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['platform', 'status']),
        ]


# Chat System Models
class ChatConversation(models.Model):
    """Chat conversations between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255, blank=True)
    conversation_type = models.CharField(max_length=20, choices=[
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
        ('channel', 'Channel')
    ], default='direct')
    created_by = models.UUIDField()  # User who created the conversation
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'conversation_type']),
            models.Index(fields=['tenant_id', 'last_message_at']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.conversation_type.title()} - {self.title or 'Untitled'}"


class ChatParticipant(models.Model):
    """Users participating in chat conversations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='participants')
    user_id = models.UUIDField()
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Administrator'),
        ('moderator', 'Moderator'),
        ('member', 'Member')
    ], default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        unique_together = [('conversation', 'user_id')]
        indexes = [
            models.Index(fields=['tenant_id', 'user_id']),
            models.Index(fields=['conversation', 'is_active']),
            models.Index(fields=['user_id', 'last_seen_at']),
        ]

    def __str__(self):
        return f"User {self.user_id} in {self.conversation}"


class MessageType(Enum):
    TEXT = 'text'
    EMOJI = 'emoji'
    FILE = 'file'
    IMAGE = 'image'
    SYSTEM = 'system'

class ChatMessage(models.Model):
    """Individual chat messages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.UUIDField()
    message_type = models.CharField(max_length=10, choices=[(tag.value, tag.name) for tag in MessageType], default=MessageType.TEXT.value)
    content = models.TextField()  # Message text or file metadata
    file_url = models.URLField(blank=True)  # For file/image messages
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # In bytes
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'conversation', 'created_at']),
            models.Index(fields=['conversation', 'is_deleted']),
            models.Index(fields=['sender_id', 'created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Message by {self.sender_id} in {self.conversation}"


class MessageReaction(models.Model):
    """Emoji reactions to messages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user_id = models.UUIDField()
    emoji = models.CharField(max_length=10)  # Unicode emoji
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()

    class Meta:
        unique_together = [('message', 'user_id', 'emoji')]
        indexes = [
            models.Index(fields=['tenant_id', 'message']),
            models.Index(fields=['user_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.emoji} by {self.user_id} on message {self.message.id}"


class TypingIndicator(models.Model):
    """Track users currently typing"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    user_id = models.UUIDField()
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        unique_together = [('conversation', 'user_id')]
        indexes = [
            models.Index(fields=['tenant_id', 'conversation']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"User {self.user_id} typing in {self.conversation}"


class UserPresence(models.Model):
    """Track user online/offline status"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(unique=True)
    status = models.CharField(max_length=20, choices=[
        ('online', 'Online'),
        ('away', 'Away'),
        ('busy', 'Busy'),
        ('offline', 'Offline')
    ], default='offline')
    last_seen = models.DateTimeField(auto_now=True)
    current_conversation = models.ForeignKey(ChatConversation, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"User {self.user_id} is {self.status}"


class SMSAnalytics(models.Model):
    """Track SMS delivery and costs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    notification_id = models.UUIDField()  # FK to NotificationRecord
    twilio_sid = models.CharField(max_length=255, unique=True)
    recipient = models.CharField(max_length=20)  # Phone number
    status = models.CharField(max_length=20, default='queued')  # Twilio status
    segments = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    price_unit = models.CharField(max_length=10, default='USD')
    error_code = models.CharField(max_length=10, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'notification_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['twilio_sid']),
            models.Index(fields=['recipient', 'status']),
        ]

    def __str__(self):
        return f"SMS {self.twilio_sid} - {self.status}"