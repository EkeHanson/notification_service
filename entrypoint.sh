#!/bin/sh

# Enhanced entrypoint script that detects service type
SERVICE_TYPE=${SERVICE_TYPE:-unknown}

# Detect service type from environment variable or hostname/container name
if [ -n "$SERVICE_TYPE" ]; then
    echo "Using SERVICE_TYPE from environment: $SERVICE_TYPE"
else
    echo "DEBUG: HOSTNAME=$HOSTNAME"
    if echo "$HOSTNAME" | grep -q "kafka"; then
        SERVICE_TYPE="kafka-consumer"
    elif echo "$HOSTNAME" | grep -q "celery-worker"; then
        SERVICE_TYPE="celery-worker"
    elif echo "$HOSTNAME" | grep -q "celery-beat"; then
        SERVICE_TYPE="celery-beat"
    elif echo "$HOSTNAME" | grep -q "flower"; then
        SERVICE_TYPE="flower"
    else
        SERVICE_TYPE="web"
    fi
fi

echo "Starting service: $SERVICE_TYPE"

case "$SERVICE_TYPE" in
    kafka-consumer)
        echo "Starting Kafka consumer..."
        python -c "
import os
import sys
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
import django
django.setup()

try:
    from notifications.utils.kafka_consumer import start_kafka_consumer
    print('Kafka consumer started successfully')
    start_kafka_consumer()
except ImportError as e:
    print(f'Failed to import Kafka consumer: {e}')
    print('Please ensure kafka-python is properly installed')
    sys.exit(1)
except Exception as e:
    print(f'Failed to start Kafka consumer: {e}')
    print('Will retry in 30 seconds...')
    time.sleep(30)
    # Retry once
    try:
        start_kafka_consumer()
    except Exception as e2:
        print(f'Final failure: {e2}')
        sys.exit(1)
        "
        ;;
    celery-worker)
        echo "Starting Celery worker..."
        celery -A notification_service worker --loglevel=info
        ;;
    celery-beat)
        echo "Starting Celery beat..."
        celery -A notification_service beat --loglevel=info
        ;;
    flower)
        echo "Starting Flower..."
        celery --broker=redis://notifications_redis:6379/0 flower --port=5555
        ;;
    web)
        echo "Starting web service..."
        # Wait for DB if needed (uses WAIT_FOR environment variables if provided)
        if [ -n "$DB_HOST" ]; then
            echo "Waiting for DB host: $DB_HOST"
            /app/wait-for-it.sh "$DB_HOST":5432 -t 60 || echo "DB wait timed out or not reachable"
        fi

        # Run migrations automatically to keep container self-initializing
        echo "Applying database migrations..."
        python manage.py migrate --noinput || echo "Migrations failed (non-zero exit); continuing to start for debugging"

        # Optionally collect static files if Django staticfiles is used
        if [ "${DJANGO_COLLECT_STATIC:-false}" = "true" ]; then
            echo "Collecting static files..."
            python manage.py collectstatic --noinput || echo "collectstatic failed"
        fi

        # Finally execute the given command (e.g., gunicorn or daphne)
        exec "$@"
        ;;
    *)
        echo "Unknown service type, executing default command..."
        exec "$@"
        ;;
esac
