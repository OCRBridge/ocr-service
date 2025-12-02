.PHONY: help install dev test test-coverage test-slow test-macos test-all lint format typecheck pre-commit docker-up docker-down docker-logs docker-build-lite docker-build-full docker-build-all docker-compose-lite-up docker-compose-lite-down docker-compose-full-up docker-compose-full-down clean run setup-test-env check check-ci ci commit release release-dry-run changelog version

# Default target
help:
	@echo "Available targets:"
	@echo "  make install          - Install dependencies"
	@echo "  make dev              - Run development server"
	@echo "  make test             - Run tests excluding Ocrmac and EasyOCR tests (for Linux CI)"
	@echo "  make test-tesseract   - Run only Tesseract tests"
	@echo "  make test-easyocr     - Run only EasyOCR tests"
	@echo "  make test-macos       - Run only macOS-specific tests (OCRMac)"
	@echo "  make test-coverage    - Run tests with HTML/XML coverage report (excluding EasyOCR)"
	@echo "  make test-coverage-full - Run all tests with coverage (including EasyOCR)"
	@echo "  make test-all         - Run all tests including EasyOCR and macOS tests"
	@echo "  make lint             - Check code with ruff"
	@echo "  make format           - Format code with ruff"
	@echo "  make typecheck        - Run ty type checker"
	@echo "  make pre-commit       - Run pre-commit hooks on all files"
	@echo "  make pre-commit-install - Install pre-commit git hooks"
	@echo "  make docker-up        - Start Docker services"
	@echo "  make docker-down      - Stop Docker services"
	@echo "  make docker-logs      - View Docker logs"
	@echo "  make docker-build-lite - Build Tesseract-only Docker image (using --target lite)"
	@echo "  make docker-build-full - Build full Docker image with EasyOCR (using --target full)"
	@echo "  make docker-build-all  - Build both lite and full Docker images"
	@echo "  make docker-compose-lite-up   - Start lite flavor with docker-compose"
	@echo "  make docker-compose-lite-down - Stop lite flavor"
	@echo "  make docker-compose-full-up   - Start full flavor with docker-compose (default)"
	@echo "  make docker-compose-full-down - Stop full flavor"
	@echo "  make clean            - Remove cache and temporary files"
	@echo "  make commit           - Create a conventional commit using commitizen"
	@echo "  make release          - Create a new release (updates version, changelog, creates tag)"
	@echo "  make release-dry-run  - Preview what the next release would be"
	@echo "  make changelog        - Generate/update changelog"
	@echo "  make version          - Display current version"

# Development
install:
	uv sync --group dev --all-extras

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run: dev

# Testing
test:
	uv run pytest -m "not ocrmac and not easyocr" -v

test-tesseract:
	uv run pytest -m "tesseract" -v

test-easyocr:
	uv run pytest -m "easyocr" -v

test-coverage:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml -m "not easyocr"
	@echo "Coverage report generated:"
	@echo "  HTML: htmlcov/index.html"
	@echo "  XML: coverage.xml"

test-coverage-full:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "Full coverage report (including EasyOCR tests):"
	@echo "  HTML: htmlcov/index.html"

test-macos:
	uv run pytest -m "ocrmac" -v

test-all:
	uv run pytest -v

# Code quality
format:
	uv run ruff format

lint:
	uv run ruff check --fix

typecheck:
	uv run ty check

all: install typecheck format lint test-all

# Pre-commit
pre-commit:
	uv run pre-commit run --all-files

pre-commit-install:
	uv run pre-commit install

pre-commit-update:
	uv run pre-commit autoupdate

# Docker (uses full flavor by default)
docker-up:
	docker compose -f docker-compose.base.yml -f docker-compose.yml up -d

docker-down:
	docker compose -f docker-compose.base.yml -f docker-compose.yml down

docker-logs:
	docker compose -f docker-compose.base.yml -f docker-compose.yml logs -f api

docker-build:
	docker compose -f docker-compose.base.yml -f docker-compose.yml build

docker-restart:
	docker compose -f docker-compose.base.yml -f docker-compose.yml restart

# Docker multi-flavor builds (using multi-stage build targets)
docker-build-lite:
	@echo "Building lightweight Tesseract-only image..."
	docker build --target lite -t ocr-service:lite .

docker-build-full:
	@echo "Building full image with EasyOCR support..."
	docker build --target full -t ocr-service:full -t ocr-service:latest .

docker-build-all: docker-build-lite docker-build-full
	@echo "All Docker images built successfully!"
	@echo "  - ocr-service:lite  (Tesseract only, ~500MB)"
	@echo "  - ocr-service:full  (Tesseract + EasyOCR, ~2.5GB)"
	@echo "  - ocr-service:latest (alias to full)"

# Docker Compose commands for different flavors
docker-compose-lite-up:
	@echo "Starting lite flavor with docker-compose..."
	docker compose -f docker-compose.base.yml -f docker-compose.lite.yml up -d

docker-compose-lite-down:
	docker compose -f docker-compose.base.yml -f docker-compose.lite.yml down

docker-compose-full-up:
	@echo "Starting full flavor with docker-compose..."
	docker compose -f docker-compose.base.yml -f docker-compose.yml up -d

docker-compose-full-down:
	docker compose -f docker-compose.base.yml -f docker-compose.yml down


# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Quality check (run all checks)
check: lint format typecheck test

# Quality check for CI (skip macOS-only tests)
check-ci: lint format typecheck test

# CI simulation (what runs in CI)
ci: install check-ci

# Semantic Release and Conventional Commits
commit:
	uv run cz commit

release:
	uv run semantic-release version
	uv run semantic-release publish

release-dry-run:
	uv run semantic-release version --print

changelog:
	uv run semantic-release changelog

version:
	@uv run semantic-release version --print
