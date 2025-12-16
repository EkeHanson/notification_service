import json
import logging
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from notifications.consumers.event_consumer import event_consumer

# Optional Kafka import
try:
    from confluent_kafka import Consumer, KafkaError, KafkaException
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Confluent Kafka not available. Event processing disabled.")

logger = logging.getLogger('notifications.management')

class Command(BaseCommand):
    help = 'Process notification events from Kafka'

    def add_arguments(self, parser):
        parser.add_argument(
            '--topics',
            nargs='+',
            default=['auth-events', 'app-events', 'security-events'],
            help='Kafka topics to consume from'
        )
        parser.add_argument(
            '--group-id',
            default='notification-service',
            help='Consumer group ID'
        )
        parser.add_argument(
            '--bootstrap-servers',
            default=getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            help='Kafka bootstrap servers'
        )
        parser.add_argument(
            '--max-events',
            type=int,
            default=None,
            help='Maximum number of events to process (for testing)'
        )

    def handle(self, *args, **options):
        if not KAFKA_AVAILABLE:
            self.stderr.write(
                self.style.ERROR('Confluent Kafka library not installed. '
                               'Install with: pip install confluent-kafka')
            )
            return

        topics = options['topics']
        group_id = options['group_id']
        bootstrap_servers = options['bootstrap_servers']
        max_events = options['max_events']

        self.stdout.write(
            self.style.SUCCESS(f'Starting event consumer for topics: {topics}')
        )

        # Configure consumer
        consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'session.timeout.ms': 6000,
            'heartbeat.interval.ms': 2000,
        }

        consumer = Consumer(consumer_config)

        try:
            consumer.subscribe(topics)

            self.stdout.write(
                self.style.SUCCESS(f'Connected to Kafka. Waiting for events...')
            )

            processed_count = 0
            error_count = 0

            while True:
                # Check if we've reached max events (for testing)
                if max_events and processed_count >= max_events:
                    self.stdout.write(
                        self.style.SUCCESS(f'Reached max events limit ({max_events})')
                    )
                    break

                try:
                    # Poll for messages
                    msg = consumer.poll(timeout=1.0)

                    if msg is None:
                        continue

                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue
                        else:
                            logger.error(f'Kafka error: {msg.error()}')
                            error_count += 1
                            continue

                    # Process the message
                    try:
                        event_data = json.loads(msg.value().decode('utf-8'))

                        self.stdout.write(
                            f'Processing event: {event_data.get("event_type")} '
                            f'(tenant: {event_data.get("tenant_id")})'
                        )

                        # Process the event
                        success = event_consumer.process_event(event_data)

                        if success:
                            processed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Event processed successfully')
                            )
                        else:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(f'✗ Failed to process event')
                            )

                    except json.JSONDecodeError as e:
                        logger.error(f'Invalid JSON in message: {e}')
                        error_count += 1
                    except Exception as e:
                        logger.error(f'Error processing message: {e}')
                        error_count += 1

                except KeyboardInterrupt:
                    self.stdout.write(
                        self.style.WARNING('Received interrupt signal. Shutting down...')
                    )
                    break
                except Exception as e:
                    logger.error(f'Consumer error: {e}')
                    error_count += 1
                    time.sleep(1)  # Brief pause before retrying

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Consumer failed: {str(e)}')
            )
        finally:
            consumer.close()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Consumer stopped. Processed: {processed_count}, Errors: {error_count}'
                )
            )