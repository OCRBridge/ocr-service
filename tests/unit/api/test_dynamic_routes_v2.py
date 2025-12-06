"""Unit tests for dynamic route handling with complex types (v2 schemas)."""

from typing import Annotated, get_args, get_origin

from fastapi import Form
from pydantic import BaseModel, Field

from src.api.routes.v2.dynamic_routes import create_form_params_from_model


class ComplexModel(BaseModel):
    """Test model with complex types similar to EasyOCRParams."""

    languages: list[str] = Field(description="List of langs")
    options: list[int] = Field(default=[1, 2])
    gpu: bool = Field(default=True)


def test_create_form_params_list_handling():
    """Test that list fields are correctly annotated for FastAPI Form."""
    params = create_form_params_from_model(ComplexModel)

    # Check languages (List[str])
    assert "languages" in params
    lang_param = params["languages"]

    # Should verify it has the correct annotation structure
    # Annotated[List[str], Form(...)]
    assert get_origin(lang_param.annotation) is Annotated

    # Unwrap annotation
    args = get_args(lang_param.annotation)
    type_arg = args[0]
    form_arg = args[1]

    # Verify type is List[str]
    assert get_origin(type_arg) is list
    assert get_args(type_arg)[0] is str

    # Verify Form info
    assert isinstance(form_arg, type(Form()))


def test_create_form_params_defaults():
    """Test default values are preserved."""
    params = create_form_params_from_model(ComplexModel)

    # The default value is set directly on the Parameter object
    assert params["options"].default == [1, 2]
    assert params["gpu"].default is True
