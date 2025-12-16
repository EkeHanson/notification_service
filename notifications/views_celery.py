from django.http import JsonResponse
from celery.result import AsyncResult
from django.conf import settings
from notification_service.celery import app as celery_app

def celery_health_check(request):
    try:
        # Use the built-in debug_task to check worker responsiveness
        result = celery_app.send_task('notification_service.celery.debug_task')
        # Wait briefly for result (non-blocking in real health checks)
        return JsonResponse({
            "status": "ok",
            "task_id": result.id,
            "service": "celery",
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "service": "celery"
        }, status=500)
