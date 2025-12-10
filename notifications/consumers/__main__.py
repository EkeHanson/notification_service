#!/usr/bin/env python
"""
Main entry point for the Kafka consumer service.
This script initializes Django and starts the Kafka consumer.
"""
import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
django.setup()

# Now we can import Django-dependent modules
from notifications.consumers.event_consumer import event_consumer
from notifications.utils.kafka_consumer import start_kafka_consumer

if __name__ == '__main__':
    print("Starting Kafka consumer for notification events...")
    try:
        start_kafka_consumer()
    except KeyboardInterrupt:
        print("Kafka consumer stopped by user")
    except Exception as e:
        print(f"Error starting Kafka consumer: {e}")
        sys.exit(1)