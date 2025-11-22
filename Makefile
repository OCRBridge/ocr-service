.PHONY: help install dev test test-unit test-integration test-contract test-coverage test-slow lint format typecheck pre-commit docker-up docker-down docker-logs docker-build-lite docker-build-full docker-build-all docker-compose-lite-up docker-compose-lite-down docker-compose-full-up docker-compose-full-down clean run setup-test-env commit release release-dry-run changelog version

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
	@echo "  make docker-build-lite - Build Tesseract-only Docker image (using --target lite)"
	@echo "  make docker-build-full - Build full Docker image with EasyOCR (using --target full)"
	@echo "  make docker-build-all  - Build both lite and full Docker images"
	@echo "  make docker-compose-lite-up   - Start lite flavor with docker-compose"
	@echo "  make docker-compose-lite-down - Stop lite flavor"
	@echo "  make docker-compose-full-up   - Start full flavor with docker-compose (default)"
	@echo "  make docker-compose-full-down - Stop full flavor"
	@echo "  make setup-test-env   - Set up test environment (create samples)"
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
setup-test-env:
	@echo "Setting up test environment..."
	@docker compose up -d redis
	@echo "Waiting for Redis to be ready..."
	@for i in 1 2 3 4 5; do \
		if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then \
			echo "Redis is ready"; \
			break; \
		fi; \
		echo "Waiting for Redis... ($$i/5)"; \
		sleep 1; \
	done
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

test: setup-test-env
	REDIS_URL=redis://localhost:7879/0 uv run pytest -m "not slow"

test-slow: setup-test-env
	REDIS_URL=redis://localhost:7879/0 uv run pytest --run-slow

test-unit:
	uv run pytest tests/unit/

test-integration: setup-test-env
	REDIS_URL=redis://localhost:7879/0 uv run pytest tests/integration/

test-contract: setup-test-env
	REDIS_URL=redis://localhost:7879/0 uv run pytest tests/contract/

test-coverage: setup-test-env
	REDIS_URL=redis://localhost:7879/0 uv run pytest --cov=src --cov-report=html --cov-report=term -m "not slow"

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
check: lint format-check typecheck test

# CI simulation (what runs in CI)
ci: install check

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
