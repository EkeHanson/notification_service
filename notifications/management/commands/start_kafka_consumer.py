from django.core.management.base import BaseCommand
from notifications.utils.kafka_consumer import start_kafka_consumer, stop_kafka_consumer
import signal
import sys
import logging

logger = logging.getLogger('notifications.management')

class Command(BaseCommand):
    help = 'Start the Kafka consumer for processing notification events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--topics',
            nargs='+',
            help='Specific topics to consume (default: all configured topics)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Kafka consumer for notification events...')
        )

        # Handle graceful shutdown
        def signal_handler(signum, frame):
            self.stdout.write(self.style.WARNING('\nReceived signal to stop consumer...'))
            stop_kafka_consumer()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            start_kafka_consumer()
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error starting Kafka consumer: {str(e)}')
            )
            sys.exit(1)