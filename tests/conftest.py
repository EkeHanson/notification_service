import pytest
import django
from django.conf import settings
from django.test.utils import get_runner

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'rest_framework',
            'channels',
            'notifications',
        ],
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
        REST_FRAMEWORK={
            'DEFAULT_AUTHENTICATION_CLASSES': [],
            'DEFAULT_PERMISSION_CLASSES': [],
        },
        CHANNEL_LAYERS={
            'default': {
                'BACKEND': 'channels.layers.InMemoryChannelLayer',
            },
        },
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        },
        CELERY_BROKER_URL='memory://',
        CELERY_RESULT_BACKEND='cache',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )

    django.setup()


@pytest.fixture
def tenant_id():
    """Default tenant ID for testing"""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def user_id():
    """Default user ID for testing"""
    return "660e8400-e29b-41d4-a716-446655440001"


@pytest.fixture
def api_client():
    """API client fixture"""
    from rest_framework.test import APIClient
    client = APIClient()
    # Mock tenant and user context
    client.tenant_id = "550e8400-e29b-41d4-a716-446655440000"
    client.user_id = "660e8400-e29b-41d4-a716-446655440001"
    return client


@pytest.fixture
def websocket_communicator():
    """WebSocket communicator fixture"""
    from channels.testing import WebsocketCommunicator
    from channels.routing import URLRouter
    from notifications.routing import websocket_urlpatterns

    def _communicator(path, tenant_id=None, user_id=None):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, path)

        if tenant_id:
            communicator.scope['tenant_id'] = tenant_id
        if user_id:
            communicator.scope['user_id'] = user_id

        return communicator

    return _communicator


@pytest.fixture
def chat_conversation(db, tenant_id, user_id):
    """Create a test chat conversation"""
    from notifications.models import ChatConversation, ChatParticipant

    conversation = ChatConversation.objects.create(
        tenant_id=tenant_id,
        title="Test Conversation",
        conversation_type="group",
        created_by=user_id
    )

    # Add creator as participant
    ChatParticipant.objects.create(
        tenant_id=tenant_id,
        conversation=conversation,
        user_id=user_id,
        role="admin"
    )

    return conversation


@pytest.fixture
def notification_record(db, tenant_id, user_id):
    """Create a test notification record"""
    from notifications.models import NotificationRecord, ChannelType

    return NotificationRecord.objects.create(
        tenant_id=tenant_id,
        channel=ChannelType.EMAIL,
        recipient="test@example.com",
        content={"subject": "Test", "body": "Test body"},
        context={"name": "Test User"}
    )


@pytest.fixture
def tenant_credentials(db, tenant_id):
    """Create test tenant credentials"""
    from notifications.models import TenantCredentials, ChannelType

    return TenantCredentials.objects.create(
        tenant_id=tenant_id,
        channel=ChannelType.EMAIL,
        credentials={
            "smtp_host": "smtp.gmail.com",
            "username": "test@example.com",
            "password": "test_password"
        }
    )


@pytest.fixture
def device_token(db, tenant_id, user_id):
    """Create a test device token"""
    from notifications.models import DeviceToken, DeviceType

    return DeviceToken.objects.create(
        tenant_id=tenant_id,
        user_id=user_id,
        device_type=DeviceType.ANDROID,
        device_token="fcm_test_token_123",
        device_id="device_123"
    )


@pytest.fixture
def mock_channel_layer():
    """Mock channel layer for testing"""
    from unittest.mock import MagicMock
    mock_layer = MagicMock()
    mock_layer.group_send = MagicMock()
    return mock_layer


@pytest.fixture
def mock_firebase_messaging():
    """Mock Firebase messaging for testing"""
    from unittest.mock import MagicMock, patch

    mock_messaging = MagicMock()
    mock_messaging.send.return_value = "msg_1234567890"

    with patch('notifications.channels.push_handler.messaging', mock_messaging):
        yield mock_messaging


@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client for testing"""
    from unittest.mock import MagicMock, patch

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.sid = "SM1234567890"
    mock_message.status = "queued"
    mock_message.to = "+1234567890"
    mock_message.from_ = "+0987654321"
    mock_client.messages.create.return_value = mock_message

    with patch('notifications.channels.sms_handler.Client', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_email_backend():
    """Mock email backend for testing"""
    from unittest.mock import patch, MagicMock

    mock_send = MagicMock(return_value=1)

    with patch('notifications.channels.email_handler.send_mail', mock_send):
        yield mock_send


# @pytest.fixture(autouse=True)
# def mock_celery_tasks():
#     """Mock Celery tasks to avoid actual task execution in tests"""
#     from unittest.mock import patch

#     with patch('notifications.tasks.tasks.send_notification_task.delay'):
#         yield


@pytest.fixture(autouse=True)
def mock_kafka_producer():
    """Mock Kafka producer for testing"""
    from unittest.mock import patch, MagicMock

    mock_producer = MagicMock()

    with patch('notifications.utils.kafka_producer.KafkaProducer', mock_producer):
        yield mock_producer


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis connections for testing"""
    from unittest.mock import patch

    with patch('redis.Redis'):
        yield


# Custom test markers
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "websocket: marks tests as WebSocket tests")
    config.addinivalue_line("markers", "event: marks tests as event system tests")


# Test utilities
def create_test_user(tenant_id, user_id, email="test@example.com"):
    """Helper to create test user data"""
    return {
        'id': user_id,
        'tenant_id': tenant_id,
        'email': email,
        'first_name': 'Test',
        'last_name': 'User'
    }


def create_test_event(event_type, tenant_id, payload):
    """Helper to create test event"""
    return {
        'event_type': event_type,
        'tenant_id': tenant_id,
        'timestamp': '2024-01-01T12:00:00Z',
        'payload': payload,
        'metadata': {
            'source': 'test',
            'version': '1.0'
        }
    }


def assert_notification_created(tenant_id, channel, recipient, check_count=True):
    """Assert that a notification was created"""
    from notifications.models import NotificationRecord

    notifications = NotificationRecord.objects.filter(
        tenant_id=tenant_id,
        channel=channel,
        recipient=recipient
    )

    if check_count:
        assert notifications.exists(), f"No notification found for {channel} to {recipient}"

    return notifications.first() if notifications.exists() else None


def assert_websocket_message_sent(communicator, message_type, timeout=5):
    """Assert that a WebSocket message was sent"""
    import asyncio
    from channels.testing import WebsocketCommunicator

    async def check_message():
        try:
            response = await communicator.receive_json_from()
            return response.get('type') == message_type
        except:
            return False

    # Run in event loop
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(asyncio.wait_for(check_message(), timeout=timeout))
        return result
    finally:
        loop.close()


# Performance testing utilities
def time_test_execution(func):
    """Decorator to time test execution"""
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\n{func.__name__} executed in {execution_time:.4f} seconds")
        return result

    return wrapper


# Database cleanup utilities
@pytest.fixture(autouse=True)
def clean_db(db):
    """Clean database between tests"""
    from django.core.management import call_command
    call_command('flush', '--noinput', verbosity=0)


# Test data factories
class TestDataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_conversation(tenant_id, user_id, title="Test Chat", conversation_type="direct"):
        """Create a test conversation"""
        from notifications.models import ChatConversation, ChatParticipant

        conversation = ChatConversation.objects.create(
            tenant_id=tenant_id,
            title=title,
            conversation_type=conversation_type,
            created_by=user_id
        )

        ChatParticipant.objects.create(
            tenant_id=tenant_id,
            conversation=conversation,
            user_id=user_id,
            role="admin"
        )

        return conversation

    @staticmethod
    def create_message(conversation, sender_id, content="Test message", message_type="text"):
        """Create a test message"""
        from notifications.models import ChatMessage, MessageType

        return ChatMessage.objects.create(
            tenant_id=conversation.tenant_id,
            conversation=conversation,
            sender_id=sender_id,
            message_type=MessageType(message_type),
            content=content
        )

    @staticmethod
    def create_notification(tenant_id, channel, recipient, content=None):
        """Create a test notification"""
        from notifications.models import NotificationRecord, ChannelType

        if content is None:
            content = {"subject": "Test", "body": "Test body"}

        return NotificationRecord.objects.create(
            tenant_id=tenant_id,
            channel=ChannelType(channel),
            recipient=recipient,
            content=content
        )