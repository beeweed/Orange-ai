"""Pydantic models for tool parameter validation.

Each tool's parameters are defined as a Pydantic model, providing:
- Strong type validation at the API boundary
- Clear, self-documenting parameter definitions
- Auto-generation of OpenAI-compatible function calling schemas
"""

from typing import Any, Dict, Type

from pydantic import BaseModel, Field


class FileWriteParams(BaseModel):
    file_path: str = Field(
        ..., description="Absolute path starting with /home/user/. Example: /home/user/project/src/App.tsx"
    )
    content: str = Field(
        ..., description="The full content to write to the file."
    )


class FileReadParams(BaseModel):
    file_path: str = Field(
        ..., description="Absolute path starting with /home/user/. Example: /home/user/project/src/main.py"
    )


class FileEditorParams(BaseModel):
    file_path: str = Field(
        ..., description="The absolute path to the file to modify"
    )
    old_string: str = Field(
        ..., description="The exact text to replace (must match the file content exactly, including whitespace and indentation)"
    )
    new_string: str = Field(
        ..., description="The text to replace it with (must be different from old_string)"
    )
    replace_all: bool = Field(
        default=False, description="Replace all occurrences of old_string (default false)"
    )


class WebSearchParams(BaseModel):
    query: str = Field(
        ..., description="The search query"
    )


class FetchWebUrlParams(BaseModel):
    url: str = Field(
        ..., description="The URL to fetch"
    )


def pydantic_to_openai_schema(
    name: str,
    description: str,
    params_model: Type[BaseModel],
) -> Dict[str, Any]:
    """Convert a Pydantic model to an OpenAI-compatible function calling schema."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": params_model.model_json_schema(),
        },
    }
