"""Unit tests for error handler middleware."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from src.api.middleware.error_handler import (
    add_exception_handlers,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


def create_mock_request(path: str = "/test") -> Request:
    """Create a mock Request object for testing.

    Uses Mock with spec=Request to ensure type compatibility.
    """
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = path
    return request


@pytest.mark.asyncio
async def test_validation_exception_handler_returns_400():
    """Test that validation exception handler returns 400 status code."""

    # Create a mock validation error
    class TestModel(BaseModel):
        field: int

    try:
        TestModel(field="not_an_int")  # type: ignore[arg-type]
    except ValidationError as e:
        # Convert to RequestValidationError-like structure
        exc = RequestValidationError(errors=e.errors())

    request = create_mock_request()
    response = await validation_exception_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_validation_exception_handler_includes_error_details():
    """Test that validation exception handler includes error details."""

    class TestModel(BaseModel):
        field: int

    try:
        TestModel(field="not_an_int")  # type: ignore[arg-type]
    except ValidationError as e:
        exc = RequestValidationError(errors=e.errors())

    request = create_mock_request()
    response = await validation_exception_handler(request, exc)

    # Parse response content
    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    assert "detail" in content
    assert "error_code" in content
    assert "errors" in content
    assert content["error_code"] == "validation_error"
    assert isinstance(content["errors"], list)
    assert len(content["errors"]) > 0


@pytest.mark.asyncio
async def test_validation_exception_handler_includes_error_list():
    """Test that validation errors are included as a list."""

    class TestModel(BaseModel):
        field1: int
        field2: str

    try:
        # Multiple validation errors
        TestModel(field1="not_an_int", field2=123)  # type: ignore[arg-type]
    except ValidationError as e:
        exc = RequestValidationError(errors=e.errors())

    request = create_mock_request()
    response = await validation_exception_handler(request, exc)

    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    # Should have errors for both fields
    assert len(content["errors"]) >= 2


@pytest.mark.asyncio
async def test_generic_exception_handler_returns_500():
    """Test that generic exception handler returns 500 status code."""
    exc = Exception("Test error")
    request = create_mock_request()

    response = await generic_exception_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_generic_exception_handler_hides_sensitive_info():
    """Test that generic handler hides sensitive error details."""
    exc = Exception("Database connection failed: password=secret123")
    request = create_mock_request()

    response = await generic_exception_handler(request, exc)

    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    # Should not expose the actual error message
    assert "password" not in str(content)
    assert "secret123" not in str(content)
    assert content["detail"] == "Internal server error"


@pytest.mark.asyncio
async def test_generic_exception_handler_includes_error_code():
    """Test that error responses include error code."""
    exc = Exception("Test error")
    request = create_mock_request()

    response = await generic_exception_handler(request, exc)

    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    assert "error_code" in content
    assert content["error_code"] == "internal_error"


def test_add_exception_handlers_registers_handlers():
    """Test that add_exception_handlers registers all handlers."""
    app = FastAPI()

    # Initially no custom exception handlers
    initial_handlers = len(app.exception_handlers)

    add_exception_handlers(app)

    # Should have added handlers
    assert len(app.exception_handlers) > initial_handlers
    assert RequestValidationError in app.exception_handlers
    assert Exception in app.exception_handlers


@pytest.mark.asyncio
async def test_validation_handler_with_empty_errors():
    """Test validation handler when exc doesn't have errors method."""
    # Create a generic exception that doesn't have errors()
    exc = Exception("Not a validation error")

    request = create_mock_request()
    response = await validation_exception_handler(request, exc)

    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    # Should handle gracefully with empty errors
    assert content["errors"] == []
    assert content["error_code"] == "validation_error"


@pytest.mark.asyncio
async def test_generic_handler_logs_request_path():
    """Test that generic handler logs the request path."""
    exc = ValueError("Test error")
    request = create_mock_request(path="/api/v2/ocr/tesseract/process")

    # Handler should log but not crash
    response = await generic_exception_handler(request, exc)

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_validation_handler_response_structure():
    """Test validation handler returns correct JSON structure."""

    class TestModel(BaseModel):
        value: int

    try:
        TestModel(value="invalid")  # type: ignore[arg-type]
    except ValidationError as e:
        exc = RequestValidationError(errors=e.errors())

    request = create_mock_request()
    response = await validation_exception_handler(request, exc)

    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    # Verify structure
    assert set(content.keys()) == {"detail", "error_code", "errors"}
    assert isinstance(content["detail"], str)
    assert isinstance(content["error_code"], str)
    assert isinstance(content["errors"], list)


@pytest.mark.asyncio
async def test_http_exception_handler():
    """Test that http exception handler returns correct status and content."""
    exc = HTTPException(status_code=418, detail="I'm a teapot")
    request = create_mock_request()

    response = await http_exception_handler(request, exc)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 418

    import json

    assert isinstance(response.body, bytes)
    content = json.loads(response.body.decode())

    assert content["detail"] == "I'm a teapot"
    assert content["error_code"] == "http_error"
