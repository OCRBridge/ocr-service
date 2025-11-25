from typing import Any

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


def test_tesseract_process_works_with_form_fields() -> None:
    # Use a sample image; skip if not available
    try:
        with open("samples/numbers_gs150.jpg", "rb") as f:
            files = {"file": ("numbers_gs150.jpg", f, "image/jpeg")}
            data: dict[str, Any] = {"lang": "eng", "psm": 3, "oem": 1, "dpi": 300}
            with TestClient(app) as client:
                resp = client.post("/v2/ocr/tesseract/process", files=files, data=data)
    except FileNotFoundError:
        # If sample isn't present, skip this test gracefully
        return

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "hocr" in payload
    assert payload.get("engine") == "tesseract"
