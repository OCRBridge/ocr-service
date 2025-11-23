"""OCR Bridge - Namespace package for OCR engines."""

# This is a namespace package to allow multiple packages to extend ocrbridge.*
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
