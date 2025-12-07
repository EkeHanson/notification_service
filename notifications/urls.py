from django.urls import path
from .views import (
    AnalyticsView, CampaignListCreateView, NotificationListCreateView,
    TenantCredentialsListCreateView, NotificationTemplateListCreateView,
    DeviceTokenListCreateView, DeviceTokenDetailView, PushAnalyticsListView, PushTestView,
    SMSAnalyticsListView, SMSTestView, SMSStatusView, SMSCostEstimationView,
    ChatConversationListCreateView, ChatConversationDetailView, ChatParticipantListCreateView,
    ChatMessageListCreateView, ChatMessageDetailView, MessageReactionListCreateView,
    UserPresenceListView, UserPresenceDetailView, FileUploadView
)

app_name = 'notifications'

urlpatterns = [
    # Core notification endpoints
    path('records/', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('credentials/', TenantCredentialsListCreateView.as_view(), name='credentials-list-create'),
    path('templates/', NotificationTemplateListCreateView.as_view(), name='template-list-create'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('campaigns/', CampaignListCreateView.as_view(), name='campaign-list-create'),

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
