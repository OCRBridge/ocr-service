# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Completed project metadata for publication readiness

## [1.1.0] - 2024-11-22

### Added
- Makefile for simplified development workflow
- Pre-commit hooks with automated code quality checks
- Pyright for static type checking
- Ruff workflow for CI/CD linting
- Enhanced sample PDFs for testing (German and English contracts)
- Synchronous OCR endpoints for immediate processing
- LiveText framework support for ocrmac OCR engine (macOS Sonoma 14.0+)
- EasyOCR integration with structured HOCR output
- Comprehensive unit tests for validation

### Changed
- Replaced pylint workflow with Ruff for faster linting
- Updated Python version matrix to support 3.11 and 3.12
- Modernized type hints across codebase
- Fixed OpenCV dependency issue (pinned to avoid broken 4.11.0.86 release)

### Removed
- Generic upload endpoint (consolidated into specific endpoints)
- GPU parameter from configuration (auto-detection implemented)
- Samples directory copy from Dockerfile (optimization)
- Pylint workflow in favor of Ruff

### Fixed
- Docker build for PyTorch compatibility with Debian-based images
- Platform limitations documented for macOS-native frameworks

## [1.0.0] - 2024-10-18

### Added
- Initial release of RESTful OCR API
- Multi-format support (JPEG, PNG, PDF, TIFF)
- HOCR (HTML-based OCR) output format
- Async job-based processing with status polling
- Redis-backed job state management
- Rate limiting (100 requests/minute per IP)
- Auto-expiration of results after 48 hours
- Tesseract OCR engine integration
- FastAPI-based REST API
- Docker and Docker Compose support
- Prometheus metrics endpoint
- Health check endpoint
- Comprehensive test suite (unit, integration, contract, performance)
- Contributing guidelines (CONTRIBUTING.md)
- Development guidelines (AGENTS.md)

### Security
- File upload validation and sanitization
- Rate limiting to prevent abuse
- Automatic cleanup of expired jobs

## [0.1.0] - 2024-09-01

### Added
- Initial prototype development
- Basic Tesseract integration
- Simple file upload endpoint
- Proof of concept for HOCR output

[unreleased]: https://github.com/OCRBridge/ocr-service/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/OCRBridge/ocr-service/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/OCRBridge/ocr-service/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/OCRBridge/ocr-service/releases/tag/v0.1.0
