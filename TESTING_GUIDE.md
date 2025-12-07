# Notification Service Testing Guide

## Quick Start

### Prerequisites
Ensure you have the required Python environment configured:
```bash
cd notification_service
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Running All Tests
```bash
python -m pytest notifications/tests.py -v
```

---

## Test Files Structure

```
notification_service/
├── notifications/
│   ├── tests.py                    # All test cases (30 tests)
│   ├── models.py                   # Django models with soft delete support
│   ├── migrations/
│   │   └── 0001_initial.py        # Database migration
│   └── ...
├── notification_service/
│   ├── test_settings.py            # Test configuration
│   └── settings.py                 # Production settings
├── pytest.ini                       # Pytest configuration
├── .env                             # Environment variables
└── TEST_REPORT.md                  # This test report
```

---

## Test Organization

### 8 Test Classes with 30 Total Tests

#### 1. **NotificationModelTests** (8 tests)
Core model functionality:
- Record creation and defaults
- Template management
- Credential storage
- Soft delete mechanism
- Unique constraints

**Run:**
```bash
pytest notifications/tests.py::NotificationModelTests -v
```

#### 2. **NotificationViewTests** (3 tests)
API endpoint testing:
- Querying empty sets
- API record creation
- Status-based filtering

**Run:**
```bash
pytest notifications/tests.py::NotificationViewTests -v
```

#### 3. **TenantCredentialsTests** (2 tests)
Multi-tenant credential management:
- Credential storage
- Credential deactivation

**Run:**
```bash
pytest notifications/tests.py::TenantCredentialsTests -v
```

#### 4. **NotificationTemplateTests** (3 tests)
Template functionality:
- Version tracking
- Placeholder management
- Multi-channel templates

**Run:**
```bash
pytest notifications/tests.py::NotificationTemplateTests -v
```

#### 5. **NotificationLifecycleTests** (4 tests)
State management:
- State transitions (pending → success)
- Failure tracking
- Retry mechanism
- Max retry enforcement

**Run:**
```bash
pytest notifications/tests.py::NotificationLifecycleTests -v
```

#### 6. **NotificationContextTests** (2 tests)
Variable substitution:
- Context variable storage
- Empty context handling

**Run:**
```bash
pytest notifications/tests.py::NotificationContextTests -v
```

#### 7. **NotificationQueryTests** (4 tests)
Database queries:
- Tenant filtering
- Channel filtering
- Status filtering
- Combined filters

**Run:**
```bash
pytest notifications/tests.py::NotificationQueryTests -v
```

#### 8. **NotificationEdgeCaseTests** (4 tests)
Boundary conditions:
- Maximum length recipients
- Unicode/special characters
- Large responses
- Templates (optional)

**Run:**
```bash
pytest notifications/tests.py::NotificationEdgeCaseTests -v
```

---

## Advanced Test Commands

### Verbose Output
```bash
pytest notifications/tests.py -vv
```

### Show Print Statements
```bash
pytest notifications/tests.py -v -s
```

### Run with Markers
```bash
pytest notifications/tests.py -v -m "unit"
```

### Exit on First Failure
```bash
pytest notifications/tests.py -x
```

### Show Local Variables on Failure
```bash
pytest notifications/tests.py -l
```

### Generate HTML Report
```bash
pytest notifications/tests.py --html=report.html --self-contained-html
```

### Generate Coverage Report
```bash
pytest notifications/tests.py --cov=notifications --cov-report=html --cov-report=term
```

---

## Test Execution Results

### Expected Output
```
===== test session starts =====
platform win32 -- Python 3.11.9, pytest-9.0.1
django: version: 5.0.4, settings: notification_service.test_settings
collecting ... collected 30 items

notifications/tests.py::NotificationModelTests::... PASSED       [  3%]
... (all 30 tests)

============ 30 passed in 4.90s ============
```

### Success Criteria
- ✅ All 30 tests pass
- ✅ No warnings (except Django deprecation warnings)
- ✅ Execution completes in < 10 seconds

---

## Test Configuration Details

### Database Configuration
Tests use SQLite in-memory database for speed:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

### Django Settings
Tests use `notification_service/test_settings.py` which includes:
- In-memory SQLite database
- In-memory caching
- Eager Celery task execution
- In-memory channel layers
- Fast password hashing (MD5)
- Minimal logging

### Pytest Configuration
See `pytest.ini` for settings:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = notification_service.test_settings
python_files = tests.py test_*.py *_tests.py
testpaths = notifications
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'django'"
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "django.core.exceptions.ImproperlyConfigured"
**Solution:** Ensure `.env` file exists with required variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

### Issue: "No such table: notifications_notificationrecord"
**Solution:** Migrations should run automatically. If not:
```bash
python manage.py migrate --run-syncdb
```

### Issue: Tests hang or timeout
**Solution:** Check for blocking network calls. All tests should complete in < 10 seconds.

---

## Continuous Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    cd notification_service
    pip install -r requirements.txt
    pytest notifications/tests.py -v --tb=short
```

---

## Development Workflow

### Adding New Tests
1. Create test method in appropriate class in `notifications/tests.py`
2. Follow naming convention: `test_<feature>_<scenario>`
3. Include docstring explaining what is tested
4. Run: `pytest notifications/tests.py::YourTestClass::test_yourtest -v`

### Modifying Models
1. Update model in `notifications/models.py`
2. Create migration: `python manage.py makemigrations`
3. Run tests to verify: `pytest notifications/tests.py -v`

### Test Coverage Goals
- Aim for > 80% code coverage
- Test both happy path and error cases
- Include edge cases and boundary conditions

---

## Performance Notes

- **Test Execution Time**: ~4-5 seconds
- **Database**: In-memory SQLite (fastest)
- **No external services**: Mocked or disabled
- **Parallel execution**: Can run with `pytest-xdist`

---

## Support

For test issues or questions:
1. Check `TEST_REPORT.md` for detailed results
2. Review test docstrings for intent
3. Check `notification_service/test_settings.py` for configuration
4. Run with `-vv` flag for verbose debugging

---

**Last Updated**: December 6, 2025
**Test Status**: ✅ All 30 tests passing
