from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # Or custom
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from notifications.models import (
    NotificationRecord, TenantCredentials, NotificationTemplate, Campaign,
    DeviceToken, PushAnalytics, SMSAnalytics, ChatConversation, ChatParticipant,
    ChatMessage, MessageReaction, UserPresence, ChannelType, NotificationStatus,
    InAppMessage, InAppMessageStatus
)
from notifications.serializers import (
    NotificationRecordSerializer, TenantCredentialsSerializer, NotificationTemplateSerializer,
    CampaignSerializer, DeviceTokenSerializer, PushAnalyticsSerializer, SMSAnalyticsSerializer,
    ChatConversationSerializer, ChatParticipantSerializer, ChatMessageSerializer,
    MessageReactionSerializer, UserPresenceSerializer, InAppMessageSerializer
)
from notifications.orchestrator.validator import validate_tenant_and_channel
from notifications.utils.context import get_tenant_context
from rest_framework.pagination import PageNumberPagination
import logging

logger = logging.getLogger('notifications.api')

from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

class AnalyticsView(APIView):
    def get(self, request):
        tenant_id = request.tenant_id
        period_days = int(request.query_params.get('days', 30))
        cutoff = timezone.now() - timedelta(days=period_days)
        
        records = NotificationRecord.objects.filter(tenant_id=tenant_id, created_at__gte=cutoff)
        
        data = {
            'total_sent': records.filter(status=NotificationStatus.SUCCESS.value).count(),
            'total_failed': records.filter(status=NotificationStatus.FAILED.value).count(),
            'success_rate': round(
                (records.filter(status=NotificationStatus.SUCCESS.value).count() / records.count() * 100)
                if records.count() > 0 else 0, 2
            ),
            'channel_usage': dict(
                records.values('channel').annotate(count=Count('channel'))
            ),
            'failure_patterns': dict(
                records.filter(status=NotificationStatus.FAILED.value)
                       .values('failure_reason').annotate(count=Count('failure_reason'))
            ),
        }
        
        return Response(data)

        
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class NotificationListCreateView(generics.ListCreateAPIView):
    serializer_class = NotificationRecordSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'channel']
    search_fields = ['recipient', 'provider_response']

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return NotificationRecord.objects.filter(tenant_id=tenant_id)

    def perform_create(self, serializer):
        serializer.save()

class TenantCredentialsListCreateView(generics.ListCreateAPIView):
    serializer_class = TenantCredentialsSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return TenantCredentials.objects.filter(tenant_id=tenant_id)

    def create(self, request, *args, **kwargs):
        tenant_id = request.tenant_id
        channel = request.data.get('channel')
        existing = TenantCredentials.objects.all_with_deleted().filter(tenant_id=tenant_id, channel=channel).first()
        logger.info(f"Upsert check: tenant_id={tenant_id}, channel={channel}, existing={existing}")
        if existing:
            # Update existing (even if soft deleted)
            if existing.is_deleted:
                existing.is_deleted = False
                existing.save(update_fields=['is_deleted'])
            serializer = self.get_serializer(existing, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            # Mark as custom since tenant is updating it
            instance.is_custom = True
            instance.save(update_fields=['is_custom'])
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Create new - mark as custom
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(is_custom=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class TenantCredentialsDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TenantCredentialsSerializer

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return TenantCredentials.objects.filter(tenant_id=tenant_id)

class NotificationTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = NotificationTemplateSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return NotificationTemplate.objects.filter(tenant_id=tenant_id)

# Add Retrieve/Update/Destroy as needed, similar to your HR views

from notifications.models import Campaign  # Add
from .serializers import CampaignSerializer  # Add

class CampaignListCreateView(generics.ListCreateAPIView):
    serializer_class = CampaignSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return Campaign.objects.filter(tenant_id=tenant_id)


# Device Token Management Views
class DeviceTokenListCreateView(generics.ListCreateAPIView):
    serializer_class = DeviceTokenSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        user_id = self.request.user_id
        return DeviceToken.objects.filter(tenant_id=tenant_id, user_id=user_id)

    def perform_create(self, serializer):
        # Handle token updates (deactivate old tokens for same device)
        device_id = serializer.validated_data.get('device_id')
        if device_id:
            DeviceToken.objects.filter(
                tenant_id=self.request.tenant_id,
                user_id=self.request.user_id,
                device_id=device_id
            ).update(is_active=False)

        serializer.save()


class DeviceTokenDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeviceTokenSerializer

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        user_id = self.request.user_id
        return DeviceToken.objects.filter(tenant_id=tenant_id, user_id=user_id)


# Push Analytics Views
class PushAnalyticsListView(generics.ListAPIView):
    serializer_class = PushAnalyticsSerializer
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['status', 'platform']

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return PushAnalytics.objects.filter(tenant_id=tenant_id)


# Push Notification Testing View
class PushTestView(APIView):
    """Test endpoint for sending push notifications"""

    def post(self, request):
        tenant_id = request.tenant_id
        device_token = request.data.get('device_token')
        title = request.data.get('title', 'Test Notification')
        body = request.data.get('body', 'This is a test push notification')

        if not device_token:
            return Response({'error': 'device_token is required'}, status=400)

        # Get tenant credentials
        from notifications.models import TenantCredentials
        try:
            creds = TenantCredentials.objects.get(
                tenant_id=tenant_id,
                channel='push',
                is_active=True
            )
        except TenantCredentials.DoesNotExist:
            return Response({'error': 'Push credentials not configured'}, status=400)

        # Send test notification
        from notifications.channels.push_handler import PushHandler
        handler = PushHandler(tenant_id, creds.credentials)

        result = handler.send(device_token, {
            'title': title,
            'body': body,
            'data': {'test': True}
        }, {})

        return Response(result)


# SMS Analytics Views
class SMSAnalyticsListView(generics.ListAPIView):
    serializer_class = SMSAnalyticsSerializer
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['status', 'created_at']

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return SMSAnalytics.objects.filter(tenant_id=tenant_id)


# SMS Testing and Utility Views
class SMSTestView(APIView):
    """Test endpoint for sending SMS"""

    def post(self, request):
        tenant_id = request.tenant_id
        phone_number = request.data.get('phone_number')
        message = request.data.get('message', 'Test SMS from notification service')

        if not phone_number:
            return Response({'error': 'phone_number is required'}, status=400)

        # Get tenant credentials
        from notifications.models import TenantCredentials
        try:
            creds = TenantCredentials.objects.get(
                tenant_id=tenant_id,
                channel='sms',
                is_active=True
            )
        except TenantCredentials.DoesNotExist:
            return Response({'error': 'SMS credentials not configured'}, status=400)

        # Send test SMS
        from notifications.channels.sms_handler import SMSHandler
        handler = SMSHandler(tenant_id, creds.credentials)

        result = handler.send(phone_number, {
            'body': message
        }, {})

        return Response(result)


class SMSStatusView(APIView):
    """Check SMS delivery status"""

    def get(self, request, sid):
        tenant_id = request.tenant_id

        # Get tenant credentials for authentication
        from notifications.models import TenantCredentials
        try:
            creds = TenantCredentials.objects.get(
                tenant_id=tenant_id,
                channel='sms',
                is_active=True
            )
        except TenantCredentials.DoesNotExist:
            return Response({'error': 'SMS credentials not configured'}, status=400)

        # Check status
        from notifications.channels.sms_handler import SMSHandler
        handler = SMSHandler(tenant_id, creds.credentials)

        result = handler.check_status(sid)
        return Response(result)


class SMSCostEstimationView(APIView):
    """Estimate SMS costs"""

    def post(self, request):
        phone_numbers = request.data.get('phone_numbers', [])
        message = request.data.get('message', '')

        if not phone_numbers or not message:
            return Response({'error': 'phone_numbers and message are required'}, status=400)

        # Get tenant credentials
        tenant_id = request.tenant_id
        from notifications.models import TenantCredentials
        try:
            creds = TenantCredentials.objects.get(
                tenant_id=tenant_id,
                channel='sms',
                is_active=True
            )
        except TenantCredentials.DoesNotExist:
            return Response({'error': 'SMS credentials not configured'}, status=400)

        # Estimate cost
        from notifications.channels.sms_handler import SMSHandler
        handler = SMSHandler(tenant_id, creds.credentials)

        result = handler.estimate_cost(phone_numbers, len(message))
        return Response(result)


# Chat System Views
class ChatConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatConversationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        user_id = self.request.user_id
        # Return conversations where user is a participant
        return ChatConversation.objects.filter(
            tenant_id=tenant_id,
            participants__user_id=user_id,
            participants__is_active=True,
            is_active=True
        ).distinct()

    def perform_create(self, serializer):
        conversation = serializer.save()

        # Add creator as participant with admin role
        ChatParticipant.objects.create(
            tenant_id=self.request.tenant_id,
            conversation=conversation,
            user_id=self.request.user_id,
            role='admin'
        )


class ChatConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChatConversationSerializer

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        user_id = self.request.user_id
        return ChatConversation.objects.filter(
            tenant_id=tenant_id,
            participants__user_id=user_id,
            participants__is_active=True
        ).distinct()


class ChatParticipantListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatParticipantSerializer

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        conversation_id = self.kwargs['conversation_id']
        return ChatParticipant.objects.filter(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            is_active=True
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            conversation_id=self.kwargs['conversation_id']
        )


class ChatMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatMessageSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        conversation_id = self.kwargs['conversation_id']
        user_id = self.request.user_id

        # Ensure user is participant in conversation
        if not ChatParticipant.objects.filter(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_id=user_id,
            is_active=True
        ).exists():
            return ChatMessage.objects.none()

        return ChatMessage.objects.filter(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            is_deleted=False
        )

    def perform_create(self, serializer):
        message = serializer.save()

        # Update conversation's last_message_at
        message.conversation.last_message_at = message.created_at
        message.conversation.save(update_fields=['last_message_at'])

        # Update participant's last_seen_at
        ChatParticipant.objects.filter(
            conversation=message.conversation,
            user_id=self.request.user_id
        ).update(last_seen_at=message.created_at)


class ChatMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        conversation_id = self.kwargs['conversation_id']
        user_id = self.request.user_id

        # Ensure user is participant and message belongs to conversation
        return ChatMessage.objects.filter(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            conversation__participants__user_id=user_id,
            conversation__participants__is_active=True
        ).distinct()


class MessageReactionListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageReactionSerializer

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        message_id = self.kwargs['message_id']
        return MessageReaction.objects.filter(
            tenant_id=tenant_id,
            message_id=message_id
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            user_id=self.request.user_id
        )


class UserPresenceListView(generics.ListAPIView):
    serializer_class = UserPresenceSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        tenant_id = self.request.tenant_id
        return UserPresence.objects.filter(tenant_id=tenant_id)


class UserPresenceDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserPresenceSerializer

    def get_object(self):
        tenant_id = self.request.tenant_id
        user_id = self.request.user_id

        obj, created = UserPresence.objects.get_or_create(
            tenant_id=tenant_id,
            user_id=user_id,
            defaults={'status': 'online'}
        )
        return obj


class FileUploadView(APIView):
    """Handle file uploads for chat messages"""

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)

        uploaded_file = request.FILES['file']

        # Basic file validation
        max_size = 10 * 1024 * 1024  # 10MB
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif',
            'application/pdf', 'text/plain',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]

        if uploaded_file.size > max_size:
            return Response({'error': 'File too large (max 10MB)'}, status=400)

        if uploaded_file.content_type not in allowed_types:
            return Response({'error': 'File type not allowed'}, status=400)

        # In a real implementation, you'd upload to cloud storage (S3, etc.)
        # For now, return mock URL
        file_url = f"/media/chat-files/{request.tenant_id}/{uploaded_file.name}"

        return Response({
            'file_url': file_url,
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'content_type': uploaded_file.content_type
        })


# In-App Message Views
class InAppMessageListView(generics.ListAPIView):
    serializer_class = InAppMessageSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'priority']
    search_fields = ['title', 'body']

    def get_queryset(self):
        # For testing purposes, allow unauthenticated access
        tenant_id = getattr(self.request, 'tenant_id', '123e4567-e89b-12d3-a456-426614174000')
        user_id = getattr(self.request, 'user_id', 'test-user-123')

        # Get messages for this user, ordered by creation date (newest first)
        queryset = InAppMessage.objects.filter(
            tenant_id=tenant_id,
            recipient__in=[str(user_id), 'all'],  # Messages for this user or broadcast to all
            is_deleted=False
        ).order_by('-created_at')

        # Optionally filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            if is_read.lower() == 'true':
                queryset = queryset.filter(read_at__isnull=False)
            elif is_read.lower() == 'false':
                queryset = queryset.filter(read_at__isnull=True)

        return queryset


class InAppMessageDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InAppMessageSerializer

    def get_queryset(self):
        # For testing purposes, allow unauthenticated access
        tenant_id = getattr(self.request, 'tenant_id', '123e4567-e89b-12d3-a456-426614174000')
        user_id = getattr(self.request, 'user_id', 'test-user-123')

        return InAppMessage.objects.filter(
            tenant_id=tenant_id,
            recipient=str(user_id),
            is_deleted=False
        )

    def perform_update(self, serializer):
        # Allow marking as read
        if 'read_at' in self.request.data and self.request.data['read_at']:
            serializer.instance.mark_read()
        else:
            serializer.save()


# Add to urlpatterns in api/urls.py
