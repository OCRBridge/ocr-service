.PHONY: help install dev test test-unit test-integration test-contract test-coverage test-slow lint format typecheck pre-commit docker-up docker-down docker-logs clean run redis-start redis-stop redis-cli redis-monitor redis-flush redis-check setup-test-env

# Default target
help:
	@echo "Available targets:"
	@echo "  make install          - Install dependencies"
	@echo "  make dev              - Run development server"
	@echo "  make test             - Run all tests (excluding slow tests)"
	@echo "  make test-slow        - Run all tests including slow tests"
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
	@echo "  make redis-start      - Start Redis server"
	@echo "  make redis-stop       - Stop Redis server"
	@echo "  make redis-check      - Check if Redis is running"
	@echo "  make redis-cli        - Open Redis CLI"
	@echo "  make redis-monitor    - Monitor Redis operations"
	@echo "  make redis-flush      - Flush Redis test data"
	@echo "  make setup-test-env   - Set up test environment (start Redis, create samples)"
	@echo "  make clean            - Remove cache and temporary files"

# Development
install:
	uv sync --group dev

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run: dev

# Testing
setup-test-env: redis-start
	@echo "Setting up test environment..."
	@uv run python3 -c "from PIL import Image, ImageDraw, ImageFont; import os; os.makedirs('samples', exist_ok=True); \
	img1 = Image.new('L', (800, 600), color=255) if not os.path.exists('samples/numbers_gs150.jpg') else None; \
	draw1 = ImageDraw.Draw(img1) if img1 else None; \
	draw1.text((100, 200), '0123456789', fill=0) if draw1 else None; \
	draw1.text((100, 300), 'Test Numbers', fill=0) if draw1 else None; \
	img1.save('samples/numbers_gs150.jpg', dpi=(150, 150)) if img1 else None; \
	print('Created samples/numbers_gs150.jpg') if img1 else print('samples/numbers_gs150.jpg exists'); \
	img2 = Image.new('L', (1024, 768), color=255) if not os.path.exists('samples/stock_gs200.jpg') else None; \
	draw2 = ImageDraw.Draw(img2) if img2 else None; \
	draw2.text((100, 200), 'Sample Text', fill=0) if draw2 else None; \
	draw2.text((100, 300), 'OCR Test Document', fill=0) if draw2 else None; \
	img2.save('samples/stock_gs200.jpg', dpi=(200, 200)) if img2 else None; \
	print('Created samples/stock_gs200.jpg') if img2 else print('samples/stock_gs200.jpg exists')" 2>/dev/null || echo "Warning: Could not create sample files"
	@echo "Test environment ready"

test: redis-check
	uv run pytest -m "not slow"

test-slow: redis-check
	uv run pytest --run-slow

test-unit:
	uv run pytest tests/unit/

test-integration: redis-check
	uv run pytest tests/integration/

test-contract: redis-check
	uv run pytest tests/contract/

test-coverage: redis-check
	uv run pytest --cov=src --cov-report=html --cov-report=term -m "not slow"

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
redis-start:
	@if ! redis-cli ping >/dev/null 2>&1; then \
		echo "Starting Redis server..."; \
		redis-server --daemonize yes; \
		sleep 1; \
		if redis-cli ping >/dev/null 2>&1; then \
			echo "Redis started successfully"; \
		else \
			echo "Failed to start Redis"; \
			exit 1; \
		fi; \
	else \
		echo "Redis is already running"; \
	fi

redis-stop:
	@if redis-cli ping >/dev/null 2>&1; then \
		echo "Stopping Redis server..."; \
		redis-cli shutdown; \
		echo "Redis stopped"; \
	else \
		echo "Redis is not running"; \
	fi

redis-check:
	@if ! redis-cli ping >/dev/null 2>&1; then \
		echo "Error: Redis is not running. Start it with 'make redis-start'"; \
		exit 1; \
	fi

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
ci: install redis-start check
