import json
import logging
from kafka import KafkaConsumer
from notifications.events.registry import event_registry
from django.conf import settings
import threading

import json
import logging
from kafka import KafkaConsumer
from notifications.events.registry import event_registry
from django.conf import settings

logger = logging.getLogger('notifications.kafka.consumer')


class NotificationKafkaConsumer:
    """Kafka consumer for processing notification events using kafka-python"""

    def __init__(self):
        self.consumer = None
        self.running = False
        # default topics; can be overridden via settings or management command
        self.topics = getattr(settings, 'KAFKA_TOPICS', {}).values()

    def create_consumer(self):
        """Create kafka-python consumer instance"""
        bootstrap = settings.KAFKA_BOOTSTRAP_SERVERS
        # kafka-python accepts string or list
        consumer_config = {
            'bootstrap_servers': bootstrap,
            'group_id': getattr(settings, 'KAFKA_GROUP_ID', 'notification-service'),
            'auto_offset_reset': getattr(settings, 'KAFKA_AUTO_OFFSET_RESET', 'latest'),
            'enable_auto_commit': False,  # Disable auto commit, commit manually after successful processing
        }

        # SSL config if provided
        ssl_config = {}
        if hasattr(settings, 'KAFKA_SSL_CA') and settings.KAFKA_SSL_CA:
            ssl_config = {
                'security_protocol': 'SSL',
                'ssl_cafile': getattr(settings, 'KAFKA_SSL_CA', None),
                'ssl_certfile': getattr(settings, 'KAFKA_SSL_CERT', None),
                'ssl_keyfile': getattr(settings, 'KAFKA_SSL_KEY', None),
            }
            consumer_config.update(ssl_config)

        self.consumer = KafkaConsumer(**consumer_config)
        logger.info("Kafka consumer created (kafka-python)")

    def start_consuming(self):
        """Start consuming messages"""
        logger.info("Starting consumer...")
        self.running = True
        if not self.consumer:
            logger.info("Creating consumer...")
            self.create_consumer()
            logger.info("Consumer created successfully")

        topics = list(self.topics) if self.topics else []
        logger.info(f"Available topics from settings: {list(self.topics) if self.topics else 'None'}")
        logger.info(f"Topics list: {topics}")
        if topics:
            logger.info(f"Subscribing to topics: {topics}")
            self.consumer.subscribe(topics)
            logger.info(f"Successfully subscribed to topics: {topics}")
        else:
            logger.error("ERROR: No topics to subscribe to!")
            return

        try:
            logger.info("Starting consumer polling loop...")
            while self.running:
                try:
                    logger.debug("Polling for messages...")
                    # poll returns dict of partitions to list of records
                    records = self.consumer.poll(timeout_ms=1000)
                    if not records:
                        logger.debug("No records received in this poll")
                        continue

                    logger.info(f"Received {len(records)} partition(s) with records")
                    for tp, msgs in records.items():
                        logger.info(f"Processing {len(msgs)} messages from partition {tp}")
                        for msg in msgs:
                            try:
                                self.process_message(msg)
                            except Exception as e:
                                logger.error(f"Error processing message: {str(e)}")
                except StopIteration:
                    # Consumer timeout reached, continue polling
                    logger.debug("StopIteration caught, continuing polling")
                    continue

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}")
        finally:
            self.stop_consuming()

    def stop_consuming(self):
        """Stop consuming and cleanup"""
        self.running = False
        if self.consumer:
            try:
                self.consumer.close()
            except Exception:
                pass
            logger.info("Kafka consumer stopped")

    def process_message(self, msg):
        """Process a single Kafka message (kafka-python message)"""
        try:
            # msg.value may already be bytes
            raw = msg.value
            if isinstance(raw, bytes):
                message_value = raw.decode('utf-8')
            else:
                message_value = str(raw)

            event = json.loads(message_value)

            logger.info(f"🔥 KAFKA EVENT RECEIVED: {event.get('event_type')} from topic: {msg.topic}")
            logger.info(f"🔥 Event payload: {json.dumps(event, indent=2)}")

            # Validate event structure
            if not self._validate_event(event):
                logger.warning(f"❌ Invalid event structure: {event}")
                # Commit offset even for invalid events to avoid reprocessing
                self.consumer.commit()
                return

            # Process event using registry
            logger.info(f"🔄 Processing event {event['event_type']} with registry...")
            result = event_registry.process_event(event)

            if result:
                logger.info(f"✅ Successfully processed event {event['event_type']} for tenant {event['tenant_id']}")
                logger.info(f"✅ Notification created with ID: {result.id if hasattr(result, 'id') else 'Unknown'}")
                # Commit offset after successful processing
                self.consumer.commit()
            else:
                logger.warning(f"❌ Event {event['event_type']} was not processed (no result returned)")
                # Still commit offset to avoid reprocessing
                self.consumer.commit()

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in message: {str(e)}")
            # Commit offset for invalid JSON to avoid reprocessing
            self.consumer.commit()
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            logger.error(f"❌ Full event data: {raw if 'raw' in locals() else 'N/A'}")
            # Don't commit offset on processing errors to allow retry

    def _validate_event(self, event: dict) -> bool:
        """Validate event structure"""
        required_fields = ['event_type', 'tenant_id', 'payload', 'timestamp']

        for field in required_fields:
            if field not in event:
                logger.warning(f"Missing required field: {field}")
                return False

        # Validate tenant_id is UUID format
        import uuid
        try:
            uuid.UUID(event['tenant_id'])
        except (ValueError, TypeError):
            logger.warning(f"Invalid tenant_id format: {event['tenant_id']}")
            return False

        # Check if event type is supported
        if event['event_type'] not in event_registry.get_supported_events():
            logger.info(f"Unsupported event type: {event['event_type']}")
            return False

        return True


# Global consumer instance
kafka_consumer = NotificationKafkaConsumer()


def start_kafka_consumer():
    """Start the Kafka consumer (call this from management command)"""
    logger.info("Starting Kafka consumer...")
    kafka_consumer.start_consuming()


def stop_kafka_consumer():
    """Stop the Kafka consumer"""
    logger.info("Stopping Kafka consumer...")
    kafka_consumer.stop_consuming()