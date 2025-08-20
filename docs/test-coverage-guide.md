# Test Coverage and Reporting Guide

## Overview

This project uses pytest with coverage.py for comprehensive test reporting and code coverage analysis.

## Quick Start

### Running Tests with Coverage

```bash
# Basic test run with coverage
pytest --cov=app

# Using Makefile commands
make test-cov       # Run tests with coverage
make test-html      # Generate HTML reports
make test-all       # Run all tests and generate reports
```

## Coverage Reports

### 1. Terminal Report
Shows coverage directly in terminal with missing lines:
```bash
pytest --cov=app --cov-report=term-missing
```

### 2. HTML Report
Interactive HTML report with line-by-line coverage:
```bash
pytest --cov=app --cov-report=html
# View report at: htmlcov/index.html
```

### 3. XML Report (for CI/CD)
```bash
pytest --cov=app --cov-report=xml
# Output: coverage.xml
```

### 4. JSON Report
```bash
pytest --cov=app --cov-report=json
# Output: coverage.json
```

## Test Categories

Mark your tests with appropriate markers:

```python
import pytest

@pytest.mark.unit
def test_unit_example():
    pass

@pytest.mark.integration
def test_integration_example():
    pass

@pytest.mark.performance
def test_performance_example():
    pass

@pytest.mark.security
def test_security_example():
    pass
```

Run specific test categories:
```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
pytest -m "not slow"    # Skip slow tests
```

## Coverage Configuration

Coverage settings are defined in `.coveragerc`:

- **Source**: `app` directory
- **Branch Coverage**: Enabled
- **Minimum Coverage**: 80% (fails CI if below)
- **Excluded**: Test files, migrations, cache directories

## CI/CD Integration

GitHub Actions automatically:
1. Runs tests on push/PR to main/develop branches
2. Generates coverage reports
3. Uploads reports as artifacts
4. Comments PR with coverage delta
5. Updates coverage badge

### Viewing CI Reports

1. Go to Actions tab in GitHub
2. Select workflow run
3. Download artifacts:
   - `coverage-report`: HTML coverage report
   - `test-report`: Test results and JSON reports

## Local Development

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests with Watch Mode
```bash
pip install pytest-watch
pytest-watch -- --cov=app --cov-report=term-missing
```

### Docker Testing
```bash
make test-docker       # Run tests in Docker
make test-docker-cov   # Run with coverage in Docker
```

## Coverage Goals

- **Unit Tests**: ≥90% coverage
- **Integration Tests**: ≥80% coverage
- **Overall**: ≥80% coverage (CI requirement)

## Best Practices

1. **Write tests first** (TDD approach)
2. **Test edge cases** and error conditions
3. **Mock external dependencies** in unit tests
4. **Use fixtures** for test data setup
5. **Keep tests isolated** and independent
6. **Run tests locally** before pushing

## Troubleshooting

### Coverage Not Showing
- Ensure source path is correct in `.coveragerc`
- Check if `__init__.py` exists in packages
- Verify pytest is finding test files

### Tests Failing in CI
- Check environment variables
- Ensure database/Redis services are running
- Review Docker service configurations

### Low Coverage
- Run `coverage report -m` to see missing lines
- Focus on critical business logic first
- Add tests for error handling paths

## Commands Reference

```bash
# Basic commands
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest -k "test_name"          # Run specific test
pytest --lf                    # Run last failed tests

# Coverage commands
coverage run -m pytest         # Run tests with coverage
coverage report               # Show coverage report
coverage html                 # Generate HTML report
coverage xml                  # Generate XML report

# Makefile commands
make test                     # Run tests
make test-cov                # Tests with coverage
make test-html               # Generate HTML reports
make test-unit               # Run unit tests only
make test-integration        # Run integration tests
make clean-test              # Clean test artifacts
make test-all                # Full test suite with reports
```

## Integration with IDEs

### VS Code
Install Python extension and add to `settings.json`:
```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "--cov=app",
    "--cov-report=term-missing"
  ]
}
```

### PyCharm
1. Go to Run → Edit Configurations
2. Add pytest configuration
3. Add parameters: `--cov=app --cov-report=html`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [coverage.py documentation](https://coverage.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)