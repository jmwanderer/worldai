.PHONY: test
test:
	PYTHONPATH=. pytest

.PHONY: build
build:
	python3 -m build  --wheel


.PHONY: coverage
coverage:
	PYTHONPATH=. coverage run -m pytest
	python3 -m tests.test_elements
	coverage report
	coverage html
