.PHONY: help env install run fmt lint test clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  fmt    Format source code"
	@echo "  lint   Run linters"
	@echo "  test   Run tests"
	@echo "  clean  Remove temporary files"

env:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(MAKE) install

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m src.main $(ARGS)

fmt:

lint:

test:

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} +
	find . -name '*.tmp' -delete
	rm -rf $(VENV)
