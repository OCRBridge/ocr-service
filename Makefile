.PHONY: help install dev test test-unit test-integration test-contract test-coverage lint format typecheck pre-commit docker-up docker-down docker-logs clean run redis-cli redis-monitor redis-flush

# Default target
help:
	@echo "Available targets:"
	@echo "  make install          - Install dependencies"
	@echo "  make dev              - Run development server"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-contract    - Run contract tests only"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Check code with ruff"
	@echo "  make format           - Format code with ruff"
	@echo "  make typecheck        - Run pyright type checker"
	@echo "  make typecheck-watch  - Run pyright in watch mode"
	@echo "  make pre-commit       - Run pre-commit hooks on all files"
	@echo "  make pre-commit-install - Install pre-commit git hooks"
	@echo "  make docker-up        - Start Docker services (API + Redis)"
	@echo "  make docker-down      - Stop Docker services"
	@echo "  make docker-logs      - View Docker logs"
	@echo "  make redis-cli        - Open Redis CLI"
	@echo "  make redis-monitor    - Monitor Redis operations"
	@echo "  make redis-flush      - Flush Redis test data"
	@echo "  make clean            - Remove cache and temporary files"

# Development
install:
	uv sync --group dev

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run: dev

# Testing
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit/

test-integration:
	uv run pytest tests/integration/

test-contract:
	uv run pytest tests/contract/

test-coverage:
	uv run pytest --cov=src --cov-report=html --cov-report=term

# Code quality
lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format src/ tests/ --check

lint-fix:
	uv run ruff check src/ tests/ --fix

typecheck:
	uv run pyright

typecheck-watch:
	uv run pyright --watch

# Pre-commit
pre-commit:
	uv run pre-commit run --all-files

pre-commit-install:
	uv run pre-commit install

pre-commit-update:
	uv run pre-commit autoupdate

# Docker
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api

docker-build:
	docker compose build

docker-restart:
	docker compose restart

# Redis
redis-cli:
	redis-cli

redis-monitor:
	redis-cli monitor

redis-flush:
	redis-cli flushdb

redis-ping:
	redis-cli ping

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Quality check (run all checks)
check: lint format-check typecheck test

# CI simulation (what runs in CI)
ci: install check
