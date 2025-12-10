from django.urls import path
from django.http import JsonResponse
from .views import (
    AnalyticsView, CampaignListCreateView, NotificationListCreateView,
    TenantCredentialsListCreateView, TenantCredentialsDetailView, NotificationTemplateListCreateView,
    DeviceTokenListCreateView, DeviceTokenDetailView, PushAnalyticsListView, PushTestView,
    SMSAnalyticsListView, SMSTestView, SMSStatusView, SMSCostEstimationView,
    ChatConversationListCreateView, ChatConversationDetailView, ChatParticipantListCreateView,
    ChatMessageListCreateView, ChatMessageDetailView, MessageReactionListCreateView,
    UserPresenceListView, UserPresenceDetailView, FileUploadView,
    InAppMessageListView, InAppMessageDetailView
)

# Health check endpoint
def health_check(request):
    return JsonResponse({"status": "healthy", "service": "notification_service"})

app_name = 'notifications'

urlpatterns = [
    # Health check endpoint
    path('health/', health_check, name='health'),

    # Core notification endpoints
    path('records/', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('credentials/', TenantCredentialsListCreateView.as_view(), name='credentials-list-create'),
    path('credentials/<uuid:pk>/', TenantCredentialsDetailView.as_view(), name='credentials-detail'),
    path('templates/', NotificationTemplateListCreateView.as_view(), name='template-list-create'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('campaigns/', CampaignListCreateView.as_view(), name='campaign-list-create'),

    # In-App Message endpoints
    path('messages/', InAppMessageListView.as_view(), name='inapp-message-list'),
    path('messages/<uuid:pk>/', InAppMessageDetailView.as_view(), name='inapp-message-detail'),

    # Device token management for push notifications
    path('devices/', DeviceTokenListCreateView.as_view(), name='device-token-list-create'),
    path('devices/<uuid:pk>/', DeviceTokenDetailView.as_view(), name='device-token-detail'),

    # Push analytics and testing
    path('push-analytics/', PushAnalyticsListView.as_view(), name='push-analytics'),
    path('push-test/', PushTestView.as_view(), name='push-test'),

    # SMS analytics and testing
    path('sms-analytics/', SMSAnalyticsListView.as_view(), name='sms-analytics'),
    path('sms-test/', SMSTestView.as_view(), name='sms-test'),
    path('sms-status/<str:sid>/', SMSStatusView.as_view(), name='sms-status'),
    path('sms-cost-estimate/', SMSCostEstimationView.as_view(), name='sms-cost-estimate'),

    # Chat system endpoints
    path('chat/conversations/', ChatConversationListCreateView.as_view(), name='chat-conversations'),
    path('chat/conversations/<uuid:pk>/', ChatConversationDetailView.as_view(), name='chat-conversation-detail'),
    path('chat/conversations/<uuid:conversation_id>/participants/', ChatParticipantListCreateView.as_view(), name='chat-participants'),
    path('chat/conversations/<uuid:conversation_id>/messages/', ChatMessageListCreateView.as_view(), name='chat-messages'),
    path('chat/conversations/<uuid:conversation_id>/messages/<uuid:pk>/', ChatMessageDetailView.as_view(), name='chat-message-detail'),
    path('chat/messages/<uuid:message_id>/reactions/', MessageReactionListCreateView.as_view(), name='message-reactions'),
    path('chat/presence/', UserPresenceListView.as_view(), name='user-presence-list'),
    path('chat/presence/me/', UserPresenceDetailView.as_view(), name='user-presence-detail'),
    path('chat/upload/', FileUploadView.as_view(), name='file-upload'),
]
