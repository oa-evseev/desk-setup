.PHONY: help fmt lint test clean

help:
	@echo "Available targets:"
	@echo "  fmt    Format source code"
	@echo "  lint   Run linters"
	@echo "  test   Run tests"
	@echo "  clean  Remove temporary files"

fmt:

lint:

test:

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} +
	find . -name '*.tmp' -delete
