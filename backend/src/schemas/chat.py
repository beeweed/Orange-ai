"""Pydantic schemas for the chat / agent API surface.

All inbound payloads are validated through these models, providing a strong
type-safety and validation layer at the API boundary (defensive programming).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Provider(str, Enum):
    """Supported LLM providers. Extensible by adding new members + a client."""

    OPENROUTER = "openrouter"
    NVIDIA = "nvidia"


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallFunction(BaseModel):
    name: str
    arguments: str  # raw JSON string as returned by the provider


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ChatMessage(BaseModel):
    """A single message in the conversation history.

    Mirrors the OpenAI chat message shape so it can be forwarded to any
    OpenAI-compatible provider without transformation.
    """

    role: Role
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None

    def to_provider_dict(self) -> Dict[str, Any]:
        """Convert to the dict shape expected by provider APIs (omit None)."""
        data: Dict[str, Any] = {"role": self.role.value}
        if self.content is not None:
            data["content"] = self.content
        if self.name is not None:
            data["name"] = self.name
        if self.tool_calls:
            data["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        return data


class Credentials(BaseModel):
    """Per-request credentials supplied by the client (never persisted)."""

    provider: Provider
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    e2b_api_key: str = Field(min_length=1)
    sandbox_template: Optional[str] = None  # optional custom E2B template id

    @field_validator("api_key", "e2b_api_key", "model")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ChatRequest(BaseModel):
    """Inbound request to run one autonomous agent turn."""

    credentials: Credentials
    # Full prior conversation (the frontend owns history persistence).
    history: List[ChatMessage] = Field(default_factory=list)
    message: str = Field(min_length=1, description="The new user message")
    # Existing sandbox id to reuse; if None a new sandbox is created.
    sandbox_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def _strip_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        return v


class ModelInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    context_length: Optional[int] = None


class ModelsResponse(BaseModel):
    provider: Provider
    models: List[ModelInfo]


class ModelsRequest(BaseModel):
    provider: Provider
    api_key: str = Field(min_length=1)
