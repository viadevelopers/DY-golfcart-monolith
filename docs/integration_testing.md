# Integration Testing

This document provides an overview of the integration testing setup for the application and how to run the tests.

## Purpose of Integration Tests

Integration tests are designed to verify that different parts of the application work together correctly. Unlike unit tests, which test individual components in isolation, integration tests focus on the interactions between components, such as the application's business logic, data access layer, and the database.

The current suite of integration tests covers:

- **SQLAlchemy Cart Repository:** Ensures that the repository can correctly save, retrieve, update, and delete cart data from the database.
- **Unit of Work (UoW):** Verifies that database transactions are properly managed, with changes being committed on success and rolled back on failure.
- **CQRS Handlers:** Tests that command and query handlers interact correctly with the repository and the database to execute business logic.

## Running the Tests

To run the integration tests, you first need to install the required dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

Once the dependencies are installed, you can run the tests using `pytest`:

```bash
pytest tests/integration/
```

This command will discover and run all the tests located in the `tests/integration/` directory.

## Test Environment Setup

The integration tests are configured to run against an in-memory SQLite database. This provides a fast, isolated, and reproducible environment for each test run, without the need for an external database server.

The test environment setup is defined in `tests/integration/conftest.py`. Key features of the setup include:

- **In-Memory SQLite Database:** A new, clean in-memory SQLite database is created for each test function. The database schema is created at the beginning of each test and torn down at the end.
- **Unit of Work Fixture:** A `UnitOfWork` instance is provided as a pytest fixture, configured to use the in-memory test database. This allows tests to easily access the repository and manage transactions within a test-specific database session.
- **Custom UUID Type:** A custom SQLAlchemy `UUID` type is used to ensure compatibility between the application's native PostgreSQL `UUID` type and the string-based UUID storage required by SQLite.
