from fastapi.testclient import TestClient

from src.main import app


def test_engines_list_includes_schemas() -> None:
    with TestClient(app) as client:
        resp = client.get("/v2/ocr/engines")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) >= 1
    # Ensure each engine has expected keys
    for eng in data:
        assert "name" in eng and "class" in eng and "supported_formats" in eng
        assert "has_param_model" in eng
        if eng.get("has_param_model"):
            assert "params_schema" in eng
            schema = eng["params_schema"]
            assert isinstance(schema, dict)
            assert schema.get("type") == "object"


def test_tesseract_info_schema_has_fields() -> None:
    # This may be skipped on environments without tesseract installed, but info should still resolve
    with TestClient(app) as client:
        resp = client.get("/v2/ocr/tesseract/info")
    assert resp.status_code == 200
    info = resp.json()
    assert info.get("name") == "tesseract"
    assert info.get("has_param_model") is True
    schema = info.get("params_schema")
    assert isinstance(schema, dict)
    # Expect known fields in schema
    props = schema.get("properties", {})
    for key in ("lang", "psm", "oem", "dpi"):
        assert key in props


def test_get_engine_details_success() -> None:
    with TestClient(app) as client:
        # Assuming 'tesseract' is always available in test environment
        resp = client.get("/v2/ocr/engines/tesseract")
    assert resp.status_code == 200
    info = resp.json()
    assert info.get("name") == "tesseract"
    assert "class" in info
    assert "supported_formats" in info
    assert "has_param_model" in info
    if info.get("has_param_model"):
        assert "params_schema" in info


def test_get_engine_details_not_found() -> None:
    with TestClient(app) as client:
        resp = client.get("/v2/ocr/engines/nonexistent_engine")
    assert resp.status_code == 404
    assert "Engine 'nonexistent_engine' not found" in resp.json()["detail"]
