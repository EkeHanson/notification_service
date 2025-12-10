# backend/notify/notification_service/urls.py

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Health check endpoint
def health_check(request):
    return JsonResponse({"status": "healthy", "service": "notification_service"})

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Schema and Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # JWT Authentication endpoints (optional if used for your microservice)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Notifications app endpoints
    path('api/notifications/', include('notifications.urls')),
]
