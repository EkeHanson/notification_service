import logging
from rest_framework import serializers
from notifications.models import (
    NotificationRecord, TenantCredentials, NotificationTemplate, ChannelType,
    NotificationStatus, DeviceType, DeviceToken, PushAnalytics, SMSAnalytics,
    Campaign, CampaignStatus, ChatConversation, ChatParticipant, ChatMessage,
    MessageReaction, UserPresence, MessageType, TypingIndicator,
    InAppMessage, InAppMessageStatus
)
from notifications.utils.encryption import encrypt_data  # For input

logger = logging.getLogger('notifications')


# NotificationRecordSerializer is defined below; we add channel field and recipient
# validation into that single serializer implementation to avoid duplicate classes.


class TenantCredentialsSerializer(serializers.ModelSerializer):
    credentials = serializers.JSONField()  # Include in response

    class Meta:
        model = TenantCredentials
        fields = ['id', 'channel', 'credentials', 'is_custom', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        logger.info(f"Creating tenant credentials for tenant {self.context['request'].tenant_id}")
        creds = validated_data.pop('credentials')
        # TODO: Encrypt sensitive fields - disabled for testing
        # channel = validated_data.get('channel')
        #
        # if channel == 'email' and 'password' in creds:
        #     creds['password'] = encrypt_data(creds['password'])
        # elif channel == 'sms' and 'auth_token' in creds:
        #     creds['auth_token'] = encrypt_data(creds['auth_token'])
        # elif channel == 'push' and 'private_key' in creds:
        #     creds['private_key'] = encrypt_data(creds['private_key'])

        validated_data['credentials'] = creds
        validated_data['tenant_id'] = self.context['request'].tenant_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        creds = validated_data.pop('credentials', None)
        if creds:
            # Encrypt sensitive fields based on channel
            channel = instance.channel

            if channel == 'email' and 'password' in creds:
                creds['password'] = encrypt_data(creds['password'])
            elif channel == 'sms' and 'auth_token' in creds:
                creds['auth_token'] = encrypt_data(creds['auth_token'])
            elif channel == 'push' and 'private_key' in creds:
                creds['private_key'] = encrypt_data(creds['private_key'])

            validated_data['credentials'] = creds

        return super().update(instance, validated_data)
    

class NotificationTemplateSerializer(serializers.ModelSerializer):
    content = serializers.JSONField()

    class Meta:
        model = NotificationTemplate
        fields = ['id', 'name', 'channel', 'content', 'placeholders', 'version', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['tenant_id'] = self.context['request'].tenant_id
        instance = super().create(validated_data)
        instance.version = 1
        instance.save()
        return instance

class NotificationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRecord
        fields = '__all__'
        read_only_fields = ['id', 'status', 'sent_at', 'retry_count', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['tenant_id'] = self.context['request'].tenant_id
        instance = super().create(validated_data)
        # Enqueue immediately
        from notifications.tasks.tasks import send_notification_task
        send_notification_task.delay(
            str(instance.id), validated_data['channel'], validated_data['recipient'],
            {}, validated_data.get('context', {})  # No content field, use context
        )
        return instance


class InAppMessageSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = InAppMessage
        fields = [
            'id', 'recipient', 'message_type',
            'title', 'body', 'data', 'priority', 'status',
            'sent_at', 'delivered_at', 'read_at', 'expires_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sent_at', 'delivered_at', 'read_at', 'created_at', 'updated_at']
    


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['id', 'sent_count', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['tenant_id'] = self.context['request'].tenant_id
        instance = super().create(validated_data)
        instance.total_recipients = len(validated_data['recipients'])
        instance.save()
        # Enqueue bulk send
        from notifications.tasks.tasks import send_bulk_campaign_task
        send_bulk_campaign_task.delay(str(instance.id))
        return instance


class DeviceTokenSerializer(serializers.ModelSerializer):
    device_type = serializers.ChoiceField(choices=[(tag.value, tag.name) for tag in DeviceType])

    class Meta:
        model = DeviceToken
        fields = [
            'id', 'device_type', 'device_token', 'device_id',
            'app_version', 'os_version', 'language', 'timezone',
            'is_active', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_used', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['tenant_id'] = self.context['request'].tenant_id
        validated_data['user_id'] = self.context['request'].user_id
        return super().create(validated_data)

    def validate_device_token(self, value):
        """Validate FCM token format"""
        if not value or len(value) < 100:
            raise serializers.ValidationError("Invalid FCM token format")
        return value


class PushAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushAnalytics
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class SMSAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSAnalytics
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# Chat System Serializers
class ChatConversationSerializer(serializers.ModelSerializer):
    participant_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = [
            'id', 'title', 'conversation_type', 'created_by',
            'is_active', 'last_message_at', 'participant_count',
            'last_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_participant_count(self, obj):
        return obj.participants.filter(is_active=True).count()

    def get_last_message(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'sender_id': last_msg.sender_id,
                'message_type': last_msg.message_type,
                'created_at': last_msg.created_at
            }
        return None

    def create(self, validated_data):
        validated_data['tenant_id'] = self.context['request'].tenant_id
        validated_data['created_by'] = self.context['request'].user_id
        return super().create(validated_data)


class ChatParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatParticipant
        fields = [
            'id', 'conversation', 'user_id', 'role',
            'joined_at', 'last_seen_at', 'is_active'
        ]
        read_only_fields = ['id', 'joined_at']


class MessageReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ['id', 'message', 'user_id', 'emoji', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    reactions = MessageReactionSerializer(many=True, read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'conversation', 'sender_id', 'message_type',
            'content', 'file_url', 'file_name', 'file_size',
            'reply_to', 'reactions', 'reply_count',
            'edited_at', 'is_deleted', 'created_at'
        ]
        read_only_fields = ['id', 'sender_id', 'edited_at', 'created_at']

    def get_reply_count(self, obj):
        return obj.replies.filter(is_deleted=False).count()

    def create(self, validated_data):
        validated_data['tenant_id'] = self.context['request'].tenant_id
        validated_data['sender_id'] = self.context['request'].user_id
        return super().create(validated_data)


class TypingIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypingIndicator
        fields = ['id', 'conversation', 'user_id', 'started_at', 'expires_at']
        read_only_fields = ['id', 'started_at']


class UserPresenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPresence
        fields = ['id', 'user_id', 'status', 'last_seen', 'current_conversation']
        read_only_fields = ['id', 'last_seen']