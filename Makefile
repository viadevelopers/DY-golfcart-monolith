.PHONY: test test-cov test-html test-watch test-unit test-integration test-performance clean-test

# Test commands
test:
	pytest

test-cov:
	pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

test-html:
	pytest --html=reports/pytest_report.html --self-contained-html
	@echo "Opening test report..."
	@python -m webbrowser htmlcov/index.html

test-watch:
	pytest-watch -- --cov=app --cov-report=term-missing

test-unit:
	pytest -m unit --cov=app --cov-report=term-missing

test-integration:
	pytest -m integration --cov=app --cov-report=term-missing

test-performance:
	pytest -m performance --benchmark-only

test-security:
	pytest -m security

# Coverage specific commands
coverage-report:
	coverage report -m

coverage-html:
	coverage html
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html

coverage-xml:
	coverage xml

coverage-json:
	coverage json

# Clean test artifacts
clean-test:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf reports
	rm -f .coverage
	rm -f coverage.xml
	rm -f coverage.json
	find . -type d -name __pycache__ -exec rm -rf {} +

# Combined commands
test-all: clean-test test-cov test-html
	@echo "All tests completed. Check htmlcov/ and reports/ for results."

# Docker test commands
test-docker:
	docker-compose -f docker-compose.dev.yml run --rm app pytest

test-docker-cov:
	docker-compose -f docker-compose.dev.yml run --rm app pytest --cov=app --cov-report=term-missing