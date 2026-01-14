.PHONY: install dev test lint format type-check run clean help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"

test:  ## Run tests with coverage
	pytest --cov=app --cov-report=term-missing --cov-report=html

test-fast:  ## Run tests without coverage
	pytest -v

lint:  ## Check code style
	ruff check .

format:  ## Format code
	ruff format .

type-check:  ## Run type checker
	mypy app

check-all: lint type-check test  ## Run all checks

run:  ## Run development server
	uvicorn app.main:app --reload

run-prod:  ## Run production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

setup:  ## Initial setup (create .env from example)
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env file created"; else echo ".env already exists"; fi
