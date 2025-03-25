# Products Database Tests

This directory contains test cases for the products database functionality of the Supportly chatbot.

## Test Files

The test suite includes the following test files:

- `test_products_agent.py`: Tests for the `ProductsAgent` class and its methods for processing natural language queries.
- `test_products_tool.py`: Tests for the `ProductsTool` class used by the chatbot to interact with the product database.
- `test_products_repository.py`: Tests for the `ProductsRepository` class that handles database queries.
- `test_api_and_integration.py`: Tests for the API endpoints and integration with the main application.
- `test_main_application.py`: Tests for the integration with the main Supportly application and the OrchestratorAgent.

## Running Tests

### Running All Tests

To run all tests, use the `run_tests.py` script:

```bash
python -m database.tests.run_tests
```

### Running Individual Test Files

To run a specific test file, use the unittest module directly:

```bash
python -m unittest database.tests.test_products_agent
python -m unittest database.tests.test_products_tool
python -m unittest database.tests.test_products_repository
python -m unittest database.tests.test_api_and_integration
python -m unittest database.tests.test_main_application
```

## Test Coverage

The test suite covers the following aspects:

### ProductsAgent Tests

- Searching for products using natural language queries
- Retrieving detailed product information
- Checking product availability
- Browsing products by category
- Parameter extraction from user queries
- Response formatting for various scenarios

### ProductsTool Tests

- Integration with the agent's functionality
- Tool action execution (search, details, availability, category)
- Error handling for invalid parameters
- Tool description format

### ProductsRepository Tests

- Database query execution for various operations
- Error handling during database operations
- Data transformation and formatting
- Handling of edge cases (e.g., product not found)

### API and Integration Tests

- API endpoint functionality and response format
- Registration of the products tool with the main application
- Tool execution through the integration layer
- Error handling in API endpoints

### Main Application Integration Tests

- Intent routing from the OrchestratorAgent to the ProductsAgent
- Integration between the main ProductsAgent and the database ProductsAgent
- Application startup integration with the FastAPI framework
- Error handling during integration with the main application

## Mocking

These tests use mocking to isolate components and avoid actual database connections:

- Database methods are mocked using `unittest.mock.patch`
- API clients are created using FastAPI's `TestClient`
- External dependencies are mocked to ensure tests run in isolation
- The OrchestratorAgent and its dependencies are mocked to test interactions without complex dependencies

## Adding New Tests

When adding new functionality to the products database module, please add corresponding tests following these guidelines:

1. Place tests in the appropriate test file based on the component being tested
2. Use descriptive test method names that indicate what is being tested
3. Include assertions to verify expected behavior
4. Mock external dependencies to keep tests isolated
5. Handle both success and error cases in tests 