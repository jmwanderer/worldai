.PHONY: test
test:
	PYTHONPATH=. pytest

.PHONY: build
build: build_ui
	python3 -m build  --wheel

.PHONY: build_ui
build_ui:
	cd worldai/ui && npm run build
	mkdir -p worldai/static/ui
	cp -r worldai/ui/dist/* worldai/static/ui


.PHONY: coverage
coverage:
	PYTHONPATH=. coverage run -m pytest
	python3 -m tests.test_elements
	coverage report
	coverage html
