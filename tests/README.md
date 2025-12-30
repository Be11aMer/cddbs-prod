# CDDBS Test Suite

This directory contains comprehensive tests for the CDDBS application.

## Test Structure

- `conftest.py` - Shared pytest fixtures and configuration
- `test_api.py` - FastAPI endpoint tests
- `test_api_helpers.py` - API helper function tests
- `test_database.py` - Database operation tests
- `test_fetch.py` - Article fetching tests
- `test_models.py` - SQLAlchemy model tests
- `test_orchestrator.py` - Pipeline orchestration tests
- `test_pipeline.py` - Individual pipeline module tests

## Running Tests

### Run with Docker (Recommended)
This is the easiest way to run tests as it automatically handles the database and environment orchestration.
```bash
docker-compose run web pytest
```

### Run Locally (Pytest)
Ensure you have the required Python packages installed and the `PYTHONPATH` set to the project root.

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   export PYTHONPATH=.
   export DATABASE_URL="postgresql+psycopg2://admin:admin@localhost:5432/cddbs"
   ```

3. **Run Tests**:
   ```bash
   pytest
   ```

### Run with coverage
*Note: Requires `pytest-cov` plugin.*
```bash
pytest --cov=src.cddbs --cov-report=html
```

## Test Coverage

### API Endpoints (`test_api.py`)
- ✅ Root endpoint (`/`)
- ✅ Health check (`/health`)
- ✅ Create analysis run (`POST /analysis-runs`)
- ✅ List analysis runs (`GET /analysis-runs`)
- ✅ Get analysis run detail (`GET /analysis-runs/{id}`)
- ✅ Input validation
- ✅ Error handling (404, 422)
- ✅ Status determination (queued/running/completed/failed)

### Database Models (`test_models.py`)
- ✅ Outlet creation and uniqueness constraints
- ✅ Article creation and relationships
- ✅ Report creation with optional fields
- ✅ Foreign key relationships
- ✅ Required field validation

### Pipeline Modules (`test_pipeline.py`)
- ✅ `fetch_articles` - Mock fallback and API integration
- ✅ `analyze_article` - Analysis with fallback handling
- ✅ `digest_content` - Content digestion with error handling
- ✅ `translate_text` - Translation with fallback
- ✅ `summarize_digest` - Summary generation

### Orchestrator (`test_orchestrator.py`)
- ✅ Full pipeline execution
- ✅ Database integration (outlet creation)
- ✅ Handling existing outlets
- ✅ Structured output validation

### Database Operations (`test_database.py`)
- ✅ Database initialization
- ✅ Connection handling
- ✅ Session management
- ✅ Transaction support

### API Helpers (`test_api_helpers.py`)
- ✅ `_get_or_create_outlet` - Outlet management
- ✅ URL updates
- ✅ None handling

## Test Fixtures

### Database Fixtures
- `db_session` - Provides a database session for tests
- `cleanup_db` - Cleans up test data after each test
- `create_test_db` - Creates tables before all tests (session scope)

### Mocking
Tests use `monkeypatch` and `unittest.mock` to:
- Mock external API calls (SerpAPI, Gemini)
- Avoid actual API charges during testing
- Ensure predictable test results

## Test Environment

### Database Isolation
Tests automatically use a dedicated database named `cddbs_test`. 
- The suite will attempt to create this database if it doesn't exist.
- This prevents tests from affecting your primary database (e.g., `cddbs`).
- Environment: Configured via `DATABASE_URL` in `.env` (the suite overrides the database name).

## Notes

- Tests are designed to be isolated and can run in any order
- Database cleanup happens automatically via fixtures
- External API calls are mocked to avoid costs and ensure reliability
- Tests validate both success paths and error handling
