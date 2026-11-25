PYTHON ?= python

.PHONY: install test lint format data figures

install:  ## Install the package with development tools and the git hooks
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pre_commit install

test:  ## Run the test suite with coverage
	$(PYTHON) -m pytest -q --cov --cov-report=term-missing

lint:  ## Check style and common errors
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:  ## Apply ruff fixes and formatting
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

data:  ## Download the NMME files the figures need (NOAA CPC)
	$(PYTHON) scripts/download_data.py

figures:  ## Regenerate every figure in figures/ from data/ (run `make data` first)
	$(PYTHON) scripts/make_figures.py
