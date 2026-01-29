.PHONY: test test-unit test-cov

# Run all tests
test:
	python -m pytest

# Run unit tests only
test-unit:
	python -m pytest tests/unit -v

# Run tests with coverage
test-cov:
	python -m pytest --cov=app --cov-report=html --cov-report=term
