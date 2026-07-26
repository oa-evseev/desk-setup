.PHONY: help env install install-dev run test clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  env    Create a development environment"
	@echo "  test   Run tests"
	@echo "  clean  Remove temporary files"

env:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(MAKE) install-dev

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

run:
	$(PYTHON) -m src.main $(ARGS)

test:
	$(PYTHON) -m pytest

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} +
	find . -name '*.tmp' -delete
	rm -rf $(VENV)
