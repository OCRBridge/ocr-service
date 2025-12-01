"""Unit tests for dynamic engine-specific route generation."""

from src.api.routes.v2.dynamic_routes import register_engine_routes


def test_register_engine_routes_registers_paths(app, mock_engine_registry):
    """register_engine_routes should add /v2/ocr/<engine>/process for each engine."""
    # Act: register dynamic routes with mock engines
    register_engine_routes(app, mock_engine_registry)

    # Collect app route paths
    paths = {getattr(r, "path", None) for r in app.router.routes}

    # Assert expected per-engine process endpoints exist
    assert "/v2/ocr/tesseract/process" in paths
    assert "/v2/ocr/easyocr/process" in paths


def test_openapi_includes_engine_paths(app, mock_engine_registry):
    """OpenAPI should include per-engine /process paths after registration."""
    from fastapi.testclient import TestClient

    register_engine_routes(app, mock_engine_registry)

    with TestClient(app) as client:
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths", {})

        assert "/v2/ocr/tesseract/process" in paths
        assert "/v2/ocr/easyocr/process" in paths
