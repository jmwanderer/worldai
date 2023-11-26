.PHONY: test
test: unittest systest 

.PHONY: systest
systest:
	PYTHONPATH=. pytest

.PHONY: unittest
unittest:
	python3 -m tests.test_elements

.PHONY: build
build:
	python3 -m build  --wheel


.PHONY: coverage
coverage:
	PYTHONPATH=. coverage run -m pytest
	python3 -m tests.test_elements
	coverage report
	coverage html
