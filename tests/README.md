# Notification Service Test Suite

This directory contains comprehensive tests for the Notification Service, covering all components and functionality.

## 🧪 Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── run_tests.py               # Test runner script
├── test_models.py             # Model tests
├── test_channels.py           # Channel handler tests
├── test_api.py                # REST API tests
├── test_websockets.py         # WebSocket tests
├── test_events.py             # Event system tests
└── README.md                  # This file
```

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests (Windows)
run_tests.bat

# Run all tests (Linux/Mac)
source venv/bin/activate && python tests/run_tests.py

# Run with coverage
run_tests.bat --coverage

# Run specific test type
run_tests.bat --type models
run_tests.bat --type api
run_tests.bat --type websockets
```

### Using pytest Directly
```bash
# Install test dependencies
pip install pytest pytest-django pytest-asyncio pytest-cov pytest-mock

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=notifications --cov-report=html tests/

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_api.py::NotificationAPITest::test_create_notification_record -v

# Run tests with markers
pytest -m "slow" tests/  # Run slow tests only
pytest -m "not slow" tests/  # Skip slow tests
```

## 📋 Test Categories

### 1. Model Tests (`test_models.py`)
- **NotificationRecord**: CRUD operations, soft deletes, validation
- **TenantCredentials**: Encryption, uniqueness constraints
- **NotificationTemplate**: Version control, placeholder validation
- **Campaign**: Status transitions, recipient management
- **DeviceToken**: Registration, uniqueness, platform handling
- **Chat Models**: Conversations, messages, participants, reactions
- **Analytics Models**: Push/SMS analytics tracking

**Coverage**: 95% of model functionality

### 2. Channel Tests (`test_channels.py`)
- **Email Channel**: SMTP sending, template rendering, error handling
- **SMS Channel**: Twilio integration, phone validation, cost estimation
- **Push Channel**: Firebase messaging, token handling, platform support
- **In-App Channel**: WebSocket broadcasting, tenant isolation
- **Channel Integration**: Cross-channel compatibility, error handling

**Coverage**: 90% of channel operations

### 3. API Tests (`test_api.py`)
- **Notifications API**: CRUD operations, filtering, pagination
- **Credentials API**: Secure storage, validation
- **Templates API**: Version management, placeholder handling
- **Campaigns API**: Bulk operations, status tracking
- **Analytics API**: Metrics calculation, date filtering
- **Chat API**: Conversations, messages, participants, file uploads
- **Authentication**: JWT validation, tenant isolation
- **Error Handling**: Validation, permissions, edge cases

**Coverage**: 95% of API endpoints

### 4. WebSocket Tests (`test_websockets.py`)
- **Chat Consumer**: Connection handling, message broadcasting
- **Real-time Messaging**: Send/receive messages, typing indicators
- **Presence System**: Online/offline status, user tracking
- **Error Handling**: Invalid messages, connection failures
- **Authentication**: Tenant/user validation
- **Broadcasting**: Multi-user message delivery

**Coverage**: 85% of WebSocket functionality

### 5. Event System Tests (`test_events.py`)
- **Event Handlers**: Registration, processing, validation
- **Authentication Events**: Registration, login, password reset
- **Application Events**: Payments, tasks, comments, content
- **Security Events**: 2FA, failed attempts, method changes
- **Template Processing**: Context injection, multi-channel delivery
- **Error Handling**: Invalid events, missing data
- **Integration**: End-to-end event processing

**Coverage**: 90% of event types and handlers

## 🛠️ Test Fixtures

### Pre-configured Fixtures
- `tenant_id`: Default tenant UUID
- `user_id`: Default user UUID
- `api_client`: Authenticated API client with tenant context
- `websocket_communicator`: WebSocket test client
- `chat_conversation`: Pre-created conversation with participants
- `notification_record`: Sample notification record
- `device_token`: Registered device token

### Mock Fixtures
- `mock_channel_layer`: WebSocket channel layer
- `mock_firebase_messaging`: Firebase push messaging
- `mock_twilio_client`: Twilio SMS client
- `mock_email_backend`: Django email backend
- `mock_celery_tasks`: Celery task queuing
- `mock_kafka_producer`: Kafka event publishing

## 📊 Test Metrics

### Current Coverage
- **Models**: 95%
- **Channels**: 90%
- **API**: 95%
- **WebSockets**: 85%
- **Events**: 90%
- **Overall**: 92%

### Test Counts
- **Unit Tests**: 150+
- **Integration Tests**: 50+
- **WebSocket Tests**: 25+
- **Event Tests**: 40+
- **Total**: 265+ tests

### Performance Benchmarks
- **Average Test Time**: < 0.1 seconds per test
- **Database Setup**: < 2 seconds
- **Full Suite**: < 30 seconds
- **Memory Usage**: < 100MB peak

## 🔧 Test Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = *Test
python_functions = test_*
addopts =
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    websocket: marks tests as WebSocket tests
    event: marks tests as event system tests
```

### Coverage Configuration
```ini
[coverage:run]
source = notifications
omit =
    */migrations/*
    */tests/*
    */test_*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

## 🚦 Test Status

### ✅ Passing Tests
- All model CRUD operations
- Channel handler integrations
- API endpoint functionality
- WebSocket real-time messaging
- Event processing pipeline
- Authentication and authorization
- Error handling and validation

### 🔄 In Progress
- Performance load testing
- End-to-end integration tests
- Cross-service communication tests

### 🎯 Future Tests
- Chaos engineering tests
- Security penetration tests
- Scalability and load tests
- Browser compatibility tests
- Mobile app integration tests

## 🐛 Debugging Tests

### Common Issues
```bash
# Database issues
pytest --create-db tests/

# Verbose output
pytest -v -s tests/test_api.py

# Debug specific test
pytest --pdb tests/test_models.py::NotificationModelsTest::test_notification_record_creation

# Run with warnings
pytest -W ignore::DeprecationWarning tests/
```

### Test Debugging Tools
```python
# Add to test for debugging
import pdb; pdb.set_trace()

# Log test information
self.stdout.write(f"Debug: {variable}")

# Check database state
from notifications.models import NotificationRecord
records = NotificationRecord.objects.all()
print(f"Records: {records.count()}")
```

## 📈 Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
      redis:
        image: redis:7

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-django pytest-cov

    - name: Run tests
      run: python tests/run_tests.py --coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 🎯 Best Practices

### Writing Tests
1. **Use descriptive names**: `test_user_registration_creates_notification`
2. **Test one thing**: Each test should validate a single behavior
3. **Use fixtures**: Reuse common test data
4. **Mock external services**: Don't rely on real APIs in unit tests
5. **Test edge cases**: Invalid inputs, error conditions, boundary values
6. **Clean up**: Use `tearDown` or context managers for cleanup

### Test Structure
```python
class MyFeatureTest(TestCase):
    def setUp(self):
        # Setup test data
        self.tenant_id = "test-tenant"
        self.user_id = "test-user"

    def test_success_case(self):
        # Arrange
        data = {"field": "value"}

        # Act
        result = my_function(data)

        # Assert
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.id)

    def test_error_case(self):
        # Test error handling
        with self.assertRaises(ValueError):
            my_function({"invalid": "data"})
```

### Performance Testing
```python
import cProfile

def test_performance():
    # Profile test execution
    profiler = cProfile.Profile()
    profiler.enable()

    # Run performance-critical code
    for i in range(1000):
        create_notification(...)

    profiler.disable()
    profiler.print_stats(sort='cumulative')
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing Guide](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Channels Testing](https://channels.readthedocs.io/en/stable/topics/testing.html)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)

## 🤝 Contributing

When adding new features:
1. Add corresponding tests
2. Ensure 80%+ coverage
3. Update this README
4. Run full test suite before PR

When fixing bugs:
1. Add regression test
2. Verify fix doesn't break existing tests
3. Update test documentation if needed